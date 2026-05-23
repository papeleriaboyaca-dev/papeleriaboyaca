from pydantic_settings import BaseSettings
import os


class Settings(BaseSettings):
    SERVICE_NAME: str = "payment-service"
    SERVICE_PORT: int = int(os.getenv("SERVICE_PORT", 8005))
    SERVICE_HOST: str = os.getenv("SERVICE_HOST", "0.0.0.0")
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")
    DEBUG: bool = os.getenv("DEBUG", "false").lower() == "true"
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    FRONTEND_URL: str = os.getenv("FRONTEND_URL", "http://localhost:5173")
    
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        "postgresql+asyncpg://postgres:postgres@localhost:5432/papeleria"
    )
    DB_ECHO: bool = os.getenv("DB_ECHO", "false").lower() == "true"
    DB_POOL_SIZE: int = int(os.getenv("DB_POOL_SIZE", 20))
    DB_MAX_OVERFLOW: int = int(os.getenv("DB_MAX_OVERFLOW", 10))
    
    WOMPI_API_URL: str = os.getenv("WOMPI_API_URL", "https://sandbox.wompi.co/v1")
    WOMPI_PRIVATE_KEY: str = os.getenv("WOMPI_PRIVATE_KEY", "")
    WOMPI_PUBLIC_KEY: str = os.getenv("WOMPI_PUBLIC_KEY", "")
    WOMPI_EVENTS_SECRET: str = os.getenv("WOMPI_EVENTS_SECRET", "")
    WOMPI_INTEGRITY_SECRET: str = os.getenv("WOMPI_INTEGRITY_SECRET", "")
    
    CORS_ORIGINS: list = [
        "http://localhost:3000",
        "http://localhost:8083",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:8083"
    ]
    ALLOWED_HOSTS: list = ["localhost", "127.0.0.1"]

    INTERNAL_API_SECRET: str = os.getenv("INTERNAL_API_SECRET", "")

    ORDER_SERVICE_URL: str = os.getenv("ORDER_SERVICE_URL", "http://order-service:8003")

    API_TITLE: str = SERVICE_NAME
    API_VERSION: str = "2.0.0"
    DOCS_URL: str = "/docs"
    REDOC_URL: str = "/redoc"
    
    class Config:
        case_sensitive = True
        env_file = ".env"


settings = Settings()
