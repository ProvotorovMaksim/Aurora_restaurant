# Aurora Restaurant API

A production-ready REST API for restaurant management built with **FastAPI**, **PostgreSQL**, and **Redis**.  
Designed to demonstrate modern Python backend development: async database access, application-level caching, Docker orchestration, and database migrations.

## 🚀 Tech Stack

| Layer | Technology | Purpose |
|-------|-----------|---------|
| **Framework** | FastAPI 0.162 | High-performance async web framework with automatic OpenAPI docs |
| **Database** | PostgreSQL 15 + asyncpg | Relational storage for restaurants, halls, and tables |
| **ORM** | SQLAlchemy 2.1 (async) | Core-style async SQL execution with `AsyncSession` |
| **Cache** | Redis 6 | JSON response caching to reduce DB load |
| **Migrations** | Alembic 1.20 | Schema versioning and zero-downtime deployments |
| **Config** | Pydantic Settings | Type-safe environment variables via `.env` |
| **Server** | Uvicorn | ASGI production server |
| **DevOps** | Docker + Docker Compose | Reproducible local and production environments |

## 📂 Project Structure

```
Aurora_restaurant/
├── main.py              # FastAPI app & all API endpoints
├── db_provider.py       # Async SQLAlchemy engine & session factory
├── redis_provider.py    # Redis client provider (singleton pattern)
├── settings.py          # Pydantic Settings (env config)
├── dockerfile           # Multi-stage Docker image (python:3.11-slim)
├── compose.yml          # Docker Compose: API + Postgres + Redis
├── entry.sh             # Entrypoint: DB wait → Alembic upgrade → Uvicorn
├── alembic.ini          # Alembic configuration
├── migrations/          # Alembic migration versions
├── models/              # SQLAlchemy models (declarative base)
├── shcemas/             # Pydantic schemas
├── requirements.txt     # Python dependencies
├── .env                 # Local environment variables
└── README.md
```
## 🛠 Key Solutions & Engineering Decisions

### 1. Async-First Data Access
The entire stack is asynchronous. SQLAlchemy 2.0 async engine (`create_async_engine`) with `asyncpg` driver and `AsyncSession` ensures non-blocking I/O under concurrent load. `pool_pre_ping=True` protects against stale connections after database restarts.

### 2. Smart Redis Caching with Invalidation
Every read endpoint checks Redis first. Data is serialized with `json.dumps` / `json.loads`, and corrupted cache entries are gracefully handled (`JSONDecodeError` → cache eviction → DB fallback).

**Cache invalidation strategy:**
- `create` / `update` / `delete` on restaurants → invalidate `"restaurants"` and `"restaurants_with_halls"`
- Hall mutations → `invalidate_hall_cache()` uses `scan_iter` to find and delete all related keys (`halls`, `halls_with_tables`, nested table caches, and the combined `restaurants_with_halls` view)

### 3. Composite Nested Endpoints
- `GET /restaurants/with-halls` — single query with `LEFT JOIN`, Python-side grouping into nested `{restaurant: [halls]}` structure
- `GET /restaurants/{id}/halls/with_tables` — halls eagerly loaded with their tables, TTL-based cache (`ex=60`)

### 4. Safe Dynamic SQL
All write/update operations use SQLAlchemy `text()` with **named bind parameters** (`:name`, `:restaurant_id`), preventing SQL injection. Dynamic `SET` clauses are built from validated keys only.

### 5. Robust Container Startup (`entry.sh`)
The container does not crash if PostgreSQL is not yet ready:
1. Polls Postgres via `asyncpg` (up to 30 seconds)
2. Runs `alembic upgrade head` to apply migrations
3. Starts Uvicorn on port `8001`
## 📡 API Endpoints

### Restaurants
| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/` | Health root |
| `GET` | `/health` | Health status |
| `GET` | `/restaurants` | List all restaurants (cached) |
| `GET` | `/restaurants/with-halls` | Restaurants with nested halls (cached) |
| `POST` | `/restaurants` | Create a restaurant |
| `PUT` | `/restaurants/{id}` | Partially update a restaurant |
| `DELETE` | `/restaurants/{id}` | Delete a restaurant |

### Halls
| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/restaurants/{id}/halls` | Halls for a restaurant (cached) |
| `GET` | `/restaurants/{id}/halls/with_tables` | Halls with nested tables (cached, 60s TTL) |
| `POST` | `/restaurants/{id}/halls` | Create a hall |
| `PUT` | `/restaurants/{id}/halls/{hall_id}` | Partially update a hall |
| `DELETE` | `/restaurants/{id}/halls/{hall_id}` | Delete a hall |

### Tables
| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/restaurants/{id}/halls/{hall_id}/tables` | Tables in a hall (cached) |
| `POST` | `/restaurants/{id}/halls/{hall_id}/tables` | Create a table |
| `DELETE` | `/restaurants/{id}/halls/{hall_id}/tables/{table_id}` | Delete a table |

OpenAPI docs are available at `http://localhost:8001/docs` once the app is running.


## 🐳 Quick Start with Docker

```bash
# Clone the repo
git clone https://github.com/ProvotorovMaksim/Aurora_restaurant.git
cd Aurora_restaurant

# Copy environment variables
cp .env.example .env   # or adjust .env directly

# Build and start all services
docker compose up --build

# API: http://localhost:8001
# Postgres: localhost:5434
# Redis: localhost:6379
```

## 💻 Local Development (without Docker)

```bash
# Create virtual environment
python -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
# Edit .env with your local DB/Redis credentials

# Run migrations
alembic upgrade head

# Start the server
uvicorn main:app --reload --port 8001
```

## 🧠 Skills Demonstrated

- **Python 3.11+**: async/await, type hints (`Optional`, `int`, `str`), f-strings, context managers
- **FastAPI**: dependency injection (`Depends`), path/query parameters, automatic OpenAPI documentation
- **SQLAlchemy 2.0 async**: engine, sessionmaker, `text()` with bound parameters, `mappings().all()`, `RETURNING` clause
- **Redis**: caching patterns, `scan_iter` for pattern-based key deletion, TTL expiration, JSON serialization
- **Docker / Docker Compose**: multi-service orchestration, custom entrypoint, health-wait logic
- **Alembic**: database migration lifecycle
- **Pydantic Settings**: 12-factor app configuration via environment variables
- **PostgreSQL**: relational modeling, joins, `RETURNING`, connection pooling

## 🌟 Project Strengths

1. **Cache-Aside pattern implemented correctly** — reads check cache first, writes invalidate dependent keys, preventing stale data.
2. **Defensive programming** — corrupted cache entries are detected and purged; missing related records return `404` instead of silent failures; empty update payloads return `400`.
3. **Production-ready containerization** — waits for DB readiness before running migrations, avoiding crash-loops during orchestrated deployments.
4. **Clean separation of concerns** — database provider, Redis provider, settings, and route logic are in separate modules.
5. **No ORM models bloat** — uses SQLAlchemy Core-style `text()` queries where appropriate, keeping the codebase lightweight and explicit.
6. **Internationalization-ready codebase** — comments and strings are in English; error responses are structured JSON.

## 📄 License

MIT. Feel free to use this as a template or learning reference.

---

*Built with ❤️ to showcase backend engineering skills: FastAPI, PostgreSQL, Redis, Docker, and Alembic.*
