"""
Fixtures compartidas del order-service.
"""
import pytest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# Must be set before any src import so Settings() captures the value
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")

from uuid import uuid4
from unittest.mock import patch
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import StaticPool
from httpx import AsyncClient, ASGITransport

from src.infrastructure.database import Base, get_db
from src.infrastructure.repositories import OrderRepository, OrderItemRepository, ShippingAddressRepository


@pytest.fixture(scope="function")
async def db_engine():
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with engine.begin() as conn:
        await conn.run_sync(
            lambda c: [setattr(t, "schema", None) for t in Base.metadata.sorted_tables]
        )
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
def order_payload():
    """Payload válido para crear una orden con un item."""
    return {
        "items": [
            {"product_id": str(uuid4()), "quantity": 2, "unit_price": 1500.0}
        ],
        "notes": "Entregar en oficina",
    }


# ── Catalog service mock (auto-applied to all HTTP tests) ─────────────────────

async def _fake_get_product(product_id):
    return {
        "id": str(product_id),
        "name": "Test Product",
        "price": 1500.0,
        "stock": 100,
        "is_active": True,
        "sku": f"SKU-{str(product_id)[:8].upper()}",
        "category_id": str(uuid4()),
    }


async def _fake_reduce_stock(product_id, quantity):
    return True


async def _fake_restore_stock(product_id, quantity):
    return


@pytest.fixture(autouse=True)
def mock_catalog_calls():
    """Patch catalog HTTP calls for all order-service tests."""
    with patch("src.application.services._catalog_get_product", side_effect=_fake_get_product), \
         patch("src.application.services._catalog_reduce_stock", side_effect=_fake_reduce_stock), \
         patch("src.application.services._catalog_restore_stock", side_effect=_fake_restore_stock):
        yield


@pytest.fixture
async def created_order(async_client, user_id, order_payload):
    """Orden ya creada disponible para tests de GET/PUT."""
    resp = await async_client.post(
        "/orders",
        json=order_payload,
        params={"user_id": str(user_id)},
    )
    assert resp.status_code == 201
    return resp.json()
