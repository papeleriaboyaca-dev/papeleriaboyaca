import json
import logging
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from src.config import settings
from src.interfaces.http import router as proxy_router, limiter

_REQUIRED = ["SUPABASE_JWT_SECRET", "IDENTITY_SERVICE_URL", "CATALOG_SERVICE_URL",
             "ORDER_SERVICE_URL", "PAYMENT_SERVICE_URL"]
_missing = [v for v in _REQUIRED if not os.getenv(v)]
if _missing:
    raise RuntimeError(f"Missing required env vars: {_missing}")

# Fail fast: en producción el shared secret entre gateway y servicios internos
# DEBE estar seteado. Si está vacío y JWT_SECRET cae al default "dev-secret",
# cualquiera puede forjar tokens.
if os.getenv("ENVIRONMENT", "development") == "production" and not os.getenv("INTERNAL_API_SECRET"):
    raise RuntimeError("INTERNAL_API_SECRET es obligatorio en producción")


class _JSONFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        data = {
            "ts": self.formatTime(record, "%Y-%m-%dT%H:%M:%S"),
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
        }
        if record.exc_info:
            data["exc"] = self.formatException(record.exc_info)
        return json.dumps(data, ensure_ascii=False)


def _configure_logging() -> None:
    handler = logging.StreamHandler()
    if settings.ENVIRONMENT == "production":
        handler.setFormatter(_JSONFormatter())
    else:
        handler.setFormatter(
            logging.Formatter("%(asctime)s %(name)s %(levelname)s %(message)s")
        )
    logging.root.handlers = [handler]
    logging.root.setLevel(settings.LOG_LEVEL)


_configure_logging()
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting %s", settings.SERVICE_NAME)
    yield
    logger.info("Shutting down %s", settings.SERVICE_NAME)


app = FastAPI(
    title=settings.API_TITLE,
    description=settings.API_DESCRIPTION,
    version=settings.API_VERSION,
    docs_url=settings.DOCS_URL,
    redoc_url=settings.REDOC_URL,
    openapi_url=settings.OPENAPI_URL,
    lifespan=lifespan,
    debug=settings.DEBUG,
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=settings.CORS_ALLOW_CREDENTIALS,
    allow_methods=settings.CORS_ALLOW_METHODS,
    allow_headers=settings.CORS_ALLOW_HEADERS,
)


@app.exception_handler(Exception)
async def exception_handler(request: Request, exc: Exception):
    # En producción no se loguea el stack trace completo para evitar leaks
    # de tokens o secretos que puedan estar en variables locales.
    if settings.ENVIRONMENT == "production":
        logger.error("Unhandled error at %s: %s", request.url.path, type(exc).__name__)
    else:
        logger.error("Unhandled error: %s", exc, exc_info=True)
    return JSONResponse(status_code=500, content={"detail": "Server error"})


@app.get("/health")
async def health():
    return {"status": "healthy", "service": settings.SERVICE_NAME}


@app.get("/")
async def root():
    return {
        "service": settings.SERVICE_NAME,
        "version": settings.API_VERSION,
        "docs": f"http://localhost:{settings.SERVICE_PORT}{settings.DOCS_URL}",
        "status": "running",
    }


app.include_router(proxy_router)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "src.main:app",
        host=settings.SERVICE_HOST,
        port=settings.SERVICE_PORT,
        reload=settings.DEBUG,
        log_level=settings.LOG_LEVEL.lower(),
    )
