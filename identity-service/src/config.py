from pydantic_settings import BaseSettings
from typing import Optional
import os


class Settings(BaseSettings):
    SERVICE_NAME: str = "identity-service"
    SERVICE_PORT: int = int(os.getenv("SERVICE_PORT", 8004))
    SERVICE_HOST: str = os.getenv("SERVICE_HOST", "0.0.0.0")
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")
    DEBUG: bool = os.getenv("DEBUG", "false").lower() == "true"
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        "postgresql+asyncpg://postgres:postgres@localhost:5432/papeleria"
    )
    DB_ECHO: bool = os.getenv("DB_ECHO", "false").lower() == "true"
    DB_POOL_SIZE: int = int(os.getenv("DB_POOL_SIZE", 20))
    DB_MAX_OVERFLOW: int = int(os.getenv("DB_MAX_OVERFLOW", 10))
    
    JWT_SECRET_KEY: str = os.getenv("JWT_SECRET_KEY", "your-secret-key-change-in-production")
    JWT_ALGORITHM: str = os.getenv("JWT_ALGORITHM", "HS256")
    JWT_EXPIRATION_HOURS: int = int(os.getenv("JWT_EXPIRATION_HOURS", 24))
    JWT_REFRESH_EXPIRATION_DAYS: int = int(os.getenv("JWT_REFRESH_EXPIRATION_DAYS", 7))
    
    SUPABASE_URL: str = os.getenv("SUPABASE_URL", "https://tnoyilwwfvigxoetxasj.supabase.co")
    SUPABASE_KEY: str = os.getenv("SUPABASE_KEY", "")   # service_role key
    SUPABASE_JWT_SECRET: str = os.getenv("SUPABASE_JWT_SECRET", "")
    
    CORS_ORIGINS: list = [
        "http://localhost:3000",
        "http://localhost:8083",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:8083"
    ]
    ALLOWED_HOSTS: list = ["localhost", "127.0.0.1"]

    INTERNAL_API_SECRET: str = os.getenv("INTERNAL_API_SECRET", "")

    API_TITLE: str = SERVICE_NAME
    API_VERSION: str = "2.0.0"
    DOCS_URL: str = "/docs"
    REDOC_URL: str = "/redoc"
    
    class Config:
        case_sensitive = True
        env_file = ".env"


settings = Settings()
