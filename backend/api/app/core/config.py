from pydantic_settings import BaseSettings
from functools import lru_cache
import os
from  dotenv import load_dotenv




class Settings(BaseSettings):
    load_dotenv()
    # App
    APP_NAME: str = "DocTrack API"
    APP_VERSION: str = "1.0.0"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True

    # Database
    DATABASE_URL: str = "postgresql://docker-lucas--:DockErSQL--v1@localhost:5435/doctrack_db"

    # Security
    SECRET_KEY: str = ""
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # Redis
    REDIS_URL: str = "redis://redis:6379"

    # Google Cloud Storage
    GCS_BUCKET_NAME: str = "doctrack-documents"
    GOOGLE_APPLICATION_CREDENTIALS: str = ""

    # CORS
    ALLOWED_ORIGINS: list[str] = [
        "http://localhost:3000",
        "http://localhost:5173",
    ]

    class Config:
        env_file = ".env"
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()