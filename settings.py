from pydantic_settings import BaseSettings
from os import getenv


class Settings(BaseSettings):
    app_name: str = "My FastAPI App"
    debug: bool = True
    DB_USER: str = "user"
    DB_PASSWORD: str = "password"
    DB_NAME: str = "restaurant_db"
    DB_HOST: str = "localhost"
    DB_PORT: int = 5434

    @property
    def database_url(self) -> str:
        return f"postgresql+asyncpg://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"

    redis_url: str = getenv("REDIS_URL", "redis://localhost:6379/0")

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "extra": "ignore",
    }


settings = Settings()
