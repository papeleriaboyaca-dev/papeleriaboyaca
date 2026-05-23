from pydantic_settings import BaseSettings
from typing import Optional
import os


class Settings(BaseSettings):
    SERVICE_NAME: str = os.getenv("SERVICE_NAME", "api-gateway")
    SERVICE_PORT: int = int(os.getenv("GATEWAY_PORT", os.getenv("SERVICE_PORT", 8083)))
    SERVICE_HOST: str = os.getenv("SERVICE_HOST", "0.0.0.0")
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")
    DEBUG: bool = os.getenv("DEBUG", "false").lower() == "true"
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        "postgresql://postgres:postgres@localhost:5432/papeleria"
    )
    DB_ECHO: bool = os.getenv("DB_ECHO", "false").lower() == "true"
    DB_POOL_SIZE: int = int(os.getenv("DB_POOL_SIZE", 20))
    DB_MAX_OVERFLOW: int = int(os.getenv("DB_MAX_OVERFLOW", 10))
    
    JWT_SECRET: str = os.getenv("JWT_SECRET", "dev-secret")           # legacy fallback
    JWT_ALGORITHM: str = os.getenv("JWT_ALGORITHM", "HS256")
    SUPABASE_JWT_SECRET: str = os.getenv("SUPABASE_JWT_SECRET", "")  # firma real de Supabase
    INTERNAL_API_SECRET: str = os.getenv("INTERNAL_API_SECRET", "")  # shared secret gateway ↔ servicios

    IDENTITY_SERVICE_URL: str = os.getenv("IDENTITY_SERVICE_URL", "http://identity-service:8004")
    CATALOG_SERVICE_URL: str = os.getenv("CATALOG_SERVICE_URL", "http://catalog-service:8002")
    ORDER_SERVICE_URL: str = os.getenv("ORDER_SERVICE_URL", "http://order-service:8003")
    PAYMENT_SERVICE_URL: str = os.getenv("PAYMENT_SERVICE_URL", "http://payment-service:8005")
    
    SUPABASE_URL: Optional[str] = os.getenv("SUPABASE_URL")
    SUPABASE_KEY: Optional[str] = os.getenv("SUPABASE_KEY")
    
    CORS_ALLOW_CREDENTIALS: bool = True
    CORS_ALLOW_METHODS: list = ["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"]
    CORS_ALLOW_HEADERS: list = ["Authorization", "Content-Type", "Accept"]

    @property
    def CORS_ORIGINS(self) -> list[str]:
        raw = os.getenv("CORS_ORIGINS", "")
        defaults = [
            "http://localhost:3000",
            "http://localhost:8083",
            "http://127.0.0.1:3000",
        ]
        if not raw:
            return defaults
        # Acepta JSON array o lista separada por comas
        import json
        try:
            parsed = json.loads(raw)
            return parsed if isinstance(parsed, list) else defaults
        except (json.JSONDecodeError, ValueError):
            return [o.strip() for o in raw.split(",") if o.strip()]
    
    API_TITLE: str = SERVICE_NAME
    API_VERSION: str = "2.0.0"
    API_DESCRIPTION: str = f"API for {SERVICE_NAME}"

    @property
    def OPENAPI_URL(self) -> Optional[str]:
        return None if self.ENVIRONMENT == "production" else "/openapi.json"

    @property
    def DOCS_URL(self) -> Optional[str]:
        return None if self.ENVIRONMENT == "production" else "/docs"

    @property
    def REDOC_URL(self) -> Optional[str]:
        return None if self.ENVIRONMENT == "production" else "/redoc"
    
    class Config:
        case_sensitive = True
        env_file = ".env"


settings = Settings()
