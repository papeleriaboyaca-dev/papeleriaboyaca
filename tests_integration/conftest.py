"""
Tests de integración — conectan al PostgreSQL real del contenedor.
Requieren la variable de entorno TEST_DATABASE_URL.

Ejecutar:
  make test-db-up
  export TEST_DATABASE_URL="postgresql+asyncpg://postgres:testpass@localhost:5433/papeleria_test"
  pytest tests_integration/ -v -m integration
  make test-db-down
"""
import pytest
import os
import sys
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import NullPool

TEST_DB_URL = os.environ.get(
    "TEST_DATABASE_URL",
    "postgresql+asyncpg://postgres:testpass@localhost:5433/papeleria_test",
)


@pytest.fixture(scope="session")
async def integration_engine():
    """Motor conectado al PostgreSQL de test (contenedor separado)."""
    engine = create_async_engine(TEST_DB_URL, poolclass=NullPool, echo=False)

    # Crea las tablas si el contenedor no montó el schema.sql
    # (útil cuando se corre sin docker-compose, e.g. CI con servicio postgres nativo)
    _ensure_schemas(engine)

    yield engine
    await engine.dispose()


def _ensure_schemas(engine):
    """Garantiza que los schemas y tablas existen en el DB de test."""
    import asyncio

    async def _run():
        # Importa todos los modelos para que Base.metadata los conozca
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../identity-service"))
        import src.infrastructure.models as _  # noqa: F401

        from src.infrastructure.database import Base

        async with engine.begin() as conn:
            # Crea schemas (DDL raw) antes de create_all
            await conn.execute(__import__("sqlalchemy").text(
                "CREATE SCHEMA IF NOT EXISTS identity_service"
            ))
            await conn.execute(__import__("sqlalchemy").text(
                "CREATE SCHEMA IF NOT EXISTS catalog_service"
            ))
            await conn.execute(__import__("sqlalchemy").text(
                "CREATE SCHEMA IF NOT EXISTS order_service"
            ))
            await conn.execute(__import__("sqlalchemy").text(
                "CREATE SCHEMA IF NOT EXISTS payment_service"
            ))
            await conn.run_sync(Base.metadata.create_all)

    asyncio.get_event_loop().run_until_complete(_run())


@pytest.fixture(scope="function")
async def integration_session(integration_engine):
    """Sesión con ROLLBACK automático al terminar cada test."""
    factory = async_sessionmaker(
        integration_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,
    )
    async with factory() as session:
        async with session.begin():
            try:
                yield session
            finally:
                await session.rollback()  # limpieza automática — no queda basura


@pytest.fixture(scope="function")
async def identity_client_integration(integration_session):
    """Cliente HTTP del identity-service contra PostgreSQL real."""
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../identity-service"))
    from httpx import AsyncClient, ASGITransport
    from src.main import app
    from src.infrastructure.database import get_db

    async def _override():
        yield integration_session

    app.dependency_overrides[get_db] = _override
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c
    app.dependency_overrides.clear()
