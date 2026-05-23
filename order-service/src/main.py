import asyncio
import json
import logging
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text

from .config import settings
from .infrastructure.database import close_db, init_db, engine, AsyncSessionLocal
from .infrastructure.repositories import (
    OrderRepository, OrderItemRepository, ShippingAddressRepository, OrderHistoryRepository
)
from .application.services import OrderService
from .interfaces.http import router

_REQUIRED = ["DATABASE_URL"]
_missing = [v for v in _REQUIRED if not os.getenv(v)]
if _missing:
    raise RuntimeError(f"Missing required env vars: {_missing}")

# Fail fast: en producción el shared secret entre gateway y servicios internos
# DEBE estar seteado. Sin él, el middleware verify_internal_auth queda abierto.
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


async def _cleanup_loop() -> None:
    """Background task: expira órdenes huérfanas cada X segundos."""
    interval = settings.ORDER_CLEANUP_INTERVAL_SECONDS
    timeout_min = settings.ORDER_CLEANUP_TIMEOUT_MINUTES
    logger.info(
        "Order cleanup task started (timeout=%dmin, interval=%ds)",
        timeout_min, interval,
    )
    while True:
        try:
            await asyncio.sleep(interval)
            async with AsyncSessionLocal() as session:
                svc = OrderService(
                    OrderRepository(session),
                    OrderItemRepository(session),
                    ShippingAddressRepository(session),
                    OrderHistoryRepository(session),
                )
                n = await svc.cleanup_expired_orders(timeout_minutes=timeout_min)
                if n:
                    logger.info("Cleanup: %d orders expired", n)
        except asyncio.CancelledError:
            logger.info("Order cleanup task cancelled")
            break
        except Exception as e:
            logger.error("cleanup_loop iteration failed: %s", e)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting %s", settings.SERVICE_NAME)
    await init_db()
    cleanup_task = None
    if settings.ORDER_CLEANUP_ENABLED:
        cleanup_task = asyncio.create_task(_cleanup_loop())
    yield
    if cleanup_task:
        cleanup_task.cancel()
        try:
            await cleanup_task
        except asyncio.CancelledError:
            pass
    logger.info("Shutting down %s", settings.SERVICE_NAME)
    await close_db()


app = FastAPI(
    title=settings.API_TITLE,
    version=settings.API_VERSION,
    docs_url=settings.DOCS_URL,
    redoc_url=settings.REDOC_URL,
    lifespan=lifespan,
    debug=settings.DEBUG,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
    allow_headers=["*"],
)


_PUBLIC_PATHS = {"/health", "/", "/docs", "/redoc", "/openapi.json"}


@app.middleware("http")
async def verify_internal_auth(request, call_next):
    """Bloquea llamadas internas sin X-Internal-Auth. Permite /health para Docker."""
    if request.url.path in _PUBLIC_PATHS or request.url.path.startswith("/docs"):
        return await call_next(request)
    if settings.INTERNAL_API_SECRET:
        if request.headers.get("X-Internal-Auth") != settings.INTERNAL_API_SECRET:
            return JSONResponse(status_code=401, content={"detail": "Unauthorized"})
    return await call_next(request)


@app.exception_handler(Exception)
async def exception_handler(request, exc):
    if settings.ENVIRONMENT == "production":
        logger.error("Unhandled error at %s: %s", request.url.path, type(exc).__name__)
    else:
        logger.error("Unhandled error: %s", exc, exc_info=True)
    return JSONResponse(status_code=500, content={"detail": "Server error"})


@app.get("/health")
async def health():
    db_ok = False
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        db_ok = True
    except Exception:
        pass
    return {
        "status": "ok" if db_ok else "degraded",
        "service": settings.SERVICE_NAME,
        "db": db_ok,
    }


@app.get("/")
async def root():
    return {
        "service": settings.SERVICE_NAME,
        "version": settings.API_VERSION,
        "docs": f"http://localhost:{settings.SERVICE_PORT}{settings.DOCS_URL}",
    }


app.include_router(router)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "src.main:app",
        host=settings.SERVICE_HOST,
        port=settings.SERVICE_PORT,
        reload=settings.DEBUG,
        log_level=settings.LOG_LEVEL.lower(),
    )
