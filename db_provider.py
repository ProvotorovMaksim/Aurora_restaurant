from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from settings import settings

class Database:
    def __init__(self):
        self.engine = create_async_engine(settings.database_url, pool_pre_ping=True)
        self.SessionLocal = async_sessionmaker(
            bind=self.engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )

    def get_session(self):
        return self.SessionLocal()


database = Database()