import json

from fastapi import FastAPI, Depends, HTTPException
from settings import settings

from typing import Optional
from sqlalchemy import text

from db_provider import database
from redis_provider import redis

app = FastAPI(title=settings.app_name, debug=settings.debug)


def invalidate_hall_cache(cache, restaurant_id: int) -> None:
    keys = list(cache.scan_iter(match=f"restaurant_{restaurant_id}_hall_*_tables"))
    cache.delete(
        f"restaurant_{restaurant_id}_halls",
        f"restaurant_{restaurant_id}_halls_with_tables",
        "restaurants_with_halls",
        *keys,
    )


@app.get("/")
async def root():
    return {"message": "Hello World"}

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

@app.get("/restaurants")
async def get_restaurants(redis=Depends(redis.get_client),db=Depends(database.get_session)):
    if redis.exists("restaurants"):
        try:
            return {"restaurants": json.loads(redis.get("restaurants"))}
        except (json.JSONDecodeError, TypeError):
            redis.delete("restaurants")
    
    async with db as session:
        result = await session.execute(text("SELECT * FROM restaurants"))
        restaurants = [dict(row) for row in result.mappings().all()]
        redis.set("restaurants", json.dumps(restaurants))
        return {"restaurants": restaurants}

@app.get("/restaurants/with-halls")
async def get_restaurants_with_halls(redis=Depends(redis.get_client), db=Depends(database.get_session)):
    cache_key = "restaurants_with_halls"
    if redis.exists(cache_key):
        try:
            return {"restaurants": json.loads(redis.get(cache_key))}
        except (json.JSONDecodeError, TypeError):
            redis.delete(cache_key)

    async with db as session:
        result = await session.execute(
            text(
                "SELECT r.id AS restaurant_id, r.name AS restaurant_name, "
                "r.description AS restaurant_description, h.id AS hall_id, "
                "h.name AS hall_name, h.description AS hall_description "
                "FROM restaurants AS r "
                "LEFT JOIN halls AS h ON h.restaurant_id = r.id "
                "ORDER BY r.id, h.id"
            )
        )
        restaurants_by_id = {}
        for row in result.mappings():
            restaurant = restaurants_by_id.setdefault(
                row["restaurant_id"],
                {
                    "id": row["restaurant_id"],
                    "name": row["restaurant_name"],
                    "description": row["restaurant_description"],
                    "halls": [],
                },
            )
            if row["hall_id"] is not None:
                restaurant["halls"].append(
                    {
                        "id": row["hall_id"],
                        "restaurant_id": row["restaurant_id"],
                        "name": row["hall_name"],
                        "description": row["hall_description"],
                    }
                )

        restaurants = list(restaurants_by_id.values())
        redis.set(cache_key, json.dumps(restaurants))
        return {"restaurants": restaurants}

@app.post("/restaurants")
async def create_restaurant(name: str, description: Optional[str] = None, redis=Depends(redis.get_client), db=Depends(database.get_session)):
    async with db as session:
        await session.execute(
            text("INSERT INTO restaurants (name, description) VALUES (:name, :description)"),
            {"name": name, "description": description},
        )

        redis.delete("restaurants")
        redis.delete("restaurants_with_halls")
        await session.commit()
        return {"message": "Restaurant created successfully"}

@app.delete("/restaurants/{restaurant_id}")
async def delete_restaurant(restaurant_id: int, redis=Depends(redis.get_client), db=Depends(database.get_session)):
    async with db as session:
        await session.execute(
            text("DELETE FROM restaurants WHERE id = :restaurant_id"),
            {"restaurant_id": restaurant_id},
        )
        redis.delete("restaurants")
        redis.delete("restaurants_with_halls")
        await session.commit()
        return {"message": "Restaurant deleted successfully"}

@app.put("/restaurants/{restaurant_id}")
async def update_restaurant(restaurant_id: int, name: Optional[str] = None, description: Optional[str] = None, redis=Depends(redis.get_client), db=Depends(database.get_session)):
    async with db as session:
        update_data = {}
        if name is not None:
            update_data["name"] = name
        if description is not None:
            update_data["description"] = description

        if not update_data:
            raise HTTPException(status_code=400, detail="No data provided for update")

        await session.execute(
            text(
                "UPDATE restaurants SET "
                + ", ".join(f"{key} = :{key}" for key in update_data.keys())
                + " WHERE id = :restaurant_id"
            ),
            {**update_data, "restaurant_id": restaurant_id},
        )
        redis.delete("restaurants")
        redis.delete("restaurants_with_halls")
        await session.commit()
        return {"message": "Restaurant updated successfully"}

@app.get("/restaurants/{restaurant_id}/halls")
async def get_halls(restaurant_id: int, redis=Depends(redis.get_client), db=Depends(database.get_session)):
    cache_key = f"restaurant_{restaurant_id}_halls"
    if redis.exists(cache_key):
        try:
            return {"halls": json.loads(redis.get(cache_key))}
        except (json.JSONDecodeError, TypeError):
            redis.delete(cache_key)

    async with db as session:
        result = await session.execute(
            text("SELECT * FROM halls WHERE restaurant_id = :restaurant_id"),
            {"restaurant_id": restaurant_id},
        )
        halls = [dict(row) for row in result.mappings().all()]
        redis.set(cache_key, json.dumps(halls))
        return {"halls": halls}

@app.get("/restaurants/{restaurant_id}/halls/with_tables")
async def get_halls_with_tables(restaurant_id: int, redis=Depends(redis.get_client), db=Depends(database.get_session)):
    cache_key = f"restaurant_{restaurant_id}_halls_with_tables"
    if redis.exists(cache_key):
        try:
            return {"halls": json.loads(redis.get(cache_key))}
        except (json.JSONDecodeError, TypeError):
            redis.delete(cache_key)

    async with db as session:
        result = await session.execute(
            text(
                "SELECT h.id AS hall_id, h.restaurant_id, h.name AS hall_name, "
                "h.description AS hall_description, t.id AS table_id, "
                "t.capacity AS table_capacity, t.active AS table_active "
                "FROM halls AS h LEFT JOIN tables AS t ON h.id = t.hall_id "
                "WHERE h.restaurant_id = :restaurant_id ORDER BY h.id, t.id"
            ),
            {"restaurant_id": restaurant_id},
        )
        halls_by_id = {}
        for row in result.mappings():
            hall = halls_by_id.setdefault(
                row["hall_id"],
                {
                    "id": row["hall_id"],
                    "restaurant_id": row["restaurant_id"],
                    "name": row["hall_name"],
                    "description": row["hall_description"],
                    "tables": [],
                },
            )
            if row["table_id"] is not None:
                hall["tables"].append(
                    {
                        "id": row["table_id"],
                        "hall_id": row["hall_id"],
                        "capacity": row["table_capacity"],
                        "active": row["table_active"],
                    }
                )

        halls = list(halls_by_id.values())
        redis.set(cache_key, json.dumps(halls), ex=60)
        return {"halls": halls}

@app.post("/restaurants/{restaurant_id}/halls")
async def create_restaurant_hall(hall_name: str, restaurant_id: int, hall_description: Optional[str] = None, redis=Depends(redis.get_client), db=Depends(database.get_session)):
    async with db as session:
        restaurant = await session.execute(
            text("SELECT id FROM restaurants WHERE id = :restaurant_id"),
            {"restaurant_id": restaurant_id},
        )
        if restaurant.scalar_one_or_none() is None:
            raise HTTPException(status_code=404, detail="Restaurant not found")

        result = await session.execute(
            text("INSERT INTO halls (name, description, restaurant_id) VALUES (:name, :description, :restaurant_id) RETURNING id, name, description, restaurant_id"),
            {"name": hall_name, "description": hall_description, "restaurant_id": restaurant_id},
        )
        hall = dict(result.mappings().one())
        await session.commit()
        invalidate_hall_cache(redis, restaurant_id)
        return {"hall": hall}

@app.delete("/restaurants/{restaurant_id}/halls/{hall_id}")
async def delete_restaurant_hall(restaurant_id: int, hall_id: int, redis=Depends(redis.get_client), db=Depends(database.get_session)):
    async with db as session:
        result = await session.execute(
            text("DELETE FROM halls WHERE id = :hall_id AND restaurant_id = :restaurant_id"),
            {"hall_id": hall_id, "restaurant_id": restaurant_id},
        )
        if result.rowcount == 0:
            raise HTTPException(status_code=404, detail="Hall not found")
        await session.commit()
        invalidate_hall_cache(redis, restaurant_id)
        return {"message": "Hall deleted successfully"}

@app.put("/restaurants/{restaurant_id}/halls/{hall_id}")
async def update_restaurant_hall(restaurant_id: int, hall_id: int, name: Optional[str] = None, description: Optional[str] = None, redis=Depends(redis.get_client), db=Depends(database.get_session)):
    async with db as session:
        update_data = {}
        if name is not None:
            update_data["name"] = name
        if description is not None:
            update_data["description"] = description

        if not update_data:
            raise HTTPException(status_code=400, detail="No data provided for update")

        await session.execute(
            text(
                "UPDATE halls SET "
                + ", ".join(f"{key} = :{key}" for key in update_data.keys())
                + " WHERE id = :hall_id AND restaurant_id = :restaurant_id"
            ),
            {**update_data, "hall_id": hall_id, "restaurant_id": restaurant_id},
        )
        invalidate_hall_cache(redis, restaurant_id)
        await session.commit()
        return {"message": "Hall updated successfully"}

@app.get("/restaurants/{restaurant_id}/halls/{hall_id}/tables")
async def get_hall_tables(restaurant_id: int, hall_id: int, redis=Depends(redis.get_client), db=Depends(database.get_session)):
    cache_key = f"restaurant_{restaurant_id}_hall_{hall_id}_tables"
    if redis.exists(cache_key):
        try:
            return {"tables": json.loads(redis.get(cache_key))}
        except (json.JSONDecodeError, TypeError):
            redis.delete(cache_key)

    async with db as session:
        hall = await session.execute(
            text("SELECT id FROM halls WHERE id = :hall_id AND restaurant_id = :restaurant_id"),
            {"hall_id": hall_id, "restaurant_id": restaurant_id},
        )
        if hall.scalar_one_or_none() is None:
            raise HTTPException(status_code=404, detail="Hall not found")

        result = await session.execute(
            text("SELECT * FROM tables WHERE hall_id = :hall_id"),
            {"hall_id": hall_id},
        )
        tables = [dict(row) for row in result.mappings().all()]
        redis.set(cache_key, json.dumps(tables))
        return {"tables": tables}

@app.post("/restaurants/{restaurant_id}/halls/{hall_id}/tables")
async def create_hall_table(restaurant_id: int, hall_id: int, capacity: int, redis=Depends(redis.get_client), db=Depends(database.get_session)):
    async with db as session:
        hall = await session.execute(
            text("SELECT id FROM halls WHERE id = :hall_id AND restaurant_id = :restaurant_id"),
            {"hall_id": hall_id, "restaurant_id": restaurant_id},
        )
        if hall.scalar_one_or_none() is None:
            raise HTTPException(status_code=404, detail="Hall not found")

        result = await session.execute(
            text(
                "INSERT INTO tables (hall_id, capacity, active) "
                "VALUES (:hall_id, :capacity, TRUE) "
                "RETURNING id, hall_id, capacity, active"
            ),
            {"hall_id": hall_id, "capacity": capacity},
        )
        table = dict(result.mappings().one())
        await session.commit()
        invalidate_hall_cache(redis, restaurant_id)
        return {"table": table}

@app.delete("/restaurants/{restaurant_id}/halls/{hall_id}/tables/{table_id}")
async def delete_hall_table(restaurant_id: int, hall_id: int, table_id: int, redis=Depends(redis.get_client), db=Depends(database.get_session)):
    async with db as session:
        hall = await session.execute(
            text("SELECT id FROM halls WHERE id = :hall_id AND restaurant_id = :restaurant_id"),
            {"hall_id": hall_id, "restaurant_id": restaurant_id},
        )
        if hall.scalar_one_or_none() is None:
            raise HTTPException(status_code=404, detail="Hall not found")

        result = await session.execute(
            text("DELETE FROM tables WHERE id = :table_id AND hall_id = :hall_id"),
            {"table_id": table_id, "hall_id": hall_id},
        )
        if result.rowcount == 0:
            raise HTTPException(status_code=404, detail="Table not found")
        await session.commit()
        invalidate_hall_cache(redis, restaurant_id)
        return {"message": "Table deleted successfully"}