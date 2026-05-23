"""
Fixtures compartidas del payment-service.
"""
import pytest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# Must be set before importing src modules so Settings() captures them at instantiation
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
os.environ.setdefault("WOMPI_EVENTS_SECRET", "test-events-secret")
os.environ.setdefault("WOMPI_PRIVATE_KEY", "prv_test_dummy")
os.environ.setdefault("WOMPI_PUBLIC_KEY", "pub_test_dummy")
os.environ.setdefault("WOMPI_MERCHANT_ID", "merchant_test")

from uuid import uuid4
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import StaticPool
from httpx import AsyncClient, ASGITransport

from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy import JSON
from src.infrastructure.database import Base, get_db
from src.infrastructure.repositories import TransactionRepository, PaymentMethodRepository, WebhookLogRepository  # noqa: F401 — registers models in Base.metadata


def _patch_for_sqlite():
    for table in Base.metadata.sorted_tables:
        setattr(table, "schema", None)
        for col in table.columns:
            if isinstance(col.type, JSONB):
                col.type = JSON()


@pytest.fixture(scope="function")
async def db_engine():
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with engine.begin() as conn:
        await conn.run_sync(lambda c: _patch_for_sqlite())
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest.fixture(scope="function")
async def db_session(db_engine):
    factory = async_sessionmaker(
        db_engine, class_=AsyncSession, expire_on_commit=False, autoflush=False
    )
    async with factory() as session:
        yield session


@pytest.fixture(scope="function")
async def async_client(db_session):
    from src.main import app

    async def _override():
        yield db_session

    app.dependency_overrides[get_db] = _override
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c
    app.dependency_overrides.clear()


# ── Datos reutilizables ────────────────────────────────────────────────────────

@pytest.fixture
def user_id():
    return uuid4()


@pytest.fixture
def transaction_payload():
    return {
        "order_id": str(uuid4()),
        "amount": 50000.0,
        "payment_method": "card",
    }


@pytest.fixture
async def created_transaction(async_client, user_id, transaction_payload):
    from unittest.mock import patch
    with patch("src.application.services._order_get_total", return_value=transaction_payload["amount"]):
        resp = await async_client.post(
            "/payments/transactions",
            json=transaction_payload,
            params={"user_id": str(user_id)},
        )
    assert resp.status_code == 201
    return resp.json()
