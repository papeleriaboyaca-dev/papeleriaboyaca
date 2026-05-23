import pytest
from uuid import uuid4
from unittest.mock import AsyncMock, patch
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import StaticPool

from src.infrastructure.database import Base
from src.infrastructure.models import Order, OrderItem
from src.infrastructure.repositories import (
    OrderRepository, OrderItemRepository, ShippingAddressRepository, OrderHistoryRepository
)
from src.application.services import OrderService
from src.application.dtos import OrderCreate, OrderItemCreate


@pytest.fixture
async def db_session():
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    async with engine.begin() as conn:
        await conn.run_sync(lambda c: [setattr(t, "schema", None) for t in Base.metadata.sorted_tables])
        await conn.run_sync(Base.metadata.create_all)

    async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        yield session

    await engine.dispose()


@pytest.fixture
async def order_service(db_session):
    return OrderService(
        OrderRepository(db_session),
        OrderItemRepository(db_session),
        ShippingAddressRepository(db_session),
        OrderHistoryRepository(db_session),
    )


def _order_create(*items):
    return OrderCreate(
        items=[OrderItemCreate(product_id=uuid4(), quantity=q, unit_price=p) for q, p in items]
    )


# ── Crear orden ───────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_create_order(order_service):
    user_id = uuid4()
    with patch("src.application.services._catalog_get_product",
               AsyncMock(return_value={"price": 1000.0, "name": "test"})), \
         patch("src.application.services._catalog_reduce_stock", AsyncMock(return_value=True)):
        order = await order_service.create_order(user_id, _order_create((2, 1000.0)))
    assert order.user_id == user_id
    assert order.status == "pending_payment"
    assert order.total == 2000.0
    assert order.order_number.startswith("ORD-")


@pytest.mark.asyncio
async def test_create_order_multiple_items(order_service):
    user_id = uuid4()
    with patch("src.application.services._catalog_get_product",
               AsyncMock(side_effect=[
                   {"price": 500.0, "name": "item1"},
                   {"price": 2000.0, "name": "item2"},
               ])), \
         patch("src.application.services._catalog_reduce_stock", AsyncMock(return_value=True)):
        order = await order_service.create_order(user_id, _order_create((3, 500.0), (1, 2000.0)))
    assert order.total == 3500.0


@pytest.mark.asyncio
async def test_create_order_empty_items_rejected(order_service):
    with pytest.raises(Exception):
        await order_service.create_order(uuid4(), OrderCreate(items=[]))


# ── Obtener orden ─────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_get_order(order_service):
    user_id = uuid4()
    with patch("src.application.services._catalog_get_product",
               AsyncMock(return_value={"price": 500.0, "name": "test"})), \
         patch("src.application.services._catalog_reduce_stock", AsyncMock(return_value=True)):
        created = await order_service.create_order(user_id, _order_create((1, 500.0)))
    retrieved = await order_service.get_order(created.id)
    assert retrieved.id == created.id
    assert retrieved.user_id == user_id


@pytest.mark.asyncio
async def test_get_order_not_found(order_service):
    with pytest.raises(ValueError, match="Order not found"):
        await order_service.get_order(uuid4())


# ── Listar órdenes ────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_list_user_orders(order_service):
    user_id = uuid4()
    with patch("src.application.services._catalog_get_product",
               AsyncMock(return_value={"price": 100.0, "name": "test"})), \
         patch("src.application.services._catalog_reduce_stock", AsyncMock(return_value=True)):
        await order_service.create_order(user_id, _order_create((1, 100.0)))
        await order_service.create_order(user_id, _order_create((2, 200.0)))
    orders = await order_service.list_user_orders(user_id)
    assert len(orders) == 2


@pytest.mark.asyncio
async def test_list_user_orders_empty(order_service):
    orders = await order_service.list_user_orders(uuid4())
    assert orders == []


# ── Actualizar estado ─────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_update_order_status(order_service):
    with patch("src.application.services._catalog_get_product",
               AsyncMock(return_value={"price": 500.0, "name": "test"})), \
         patch("src.application.services._catalog_reduce_stock", AsyncMock(return_value=True)):
        order = await order_service.create_order(uuid4(), _order_create((1, 500.0)))
    updated = await order_service.update_order_status(order.id, "confirmed")
    assert updated.status == "confirmed"


@pytest.mark.asyncio
async def test_update_order_status_invalid(order_service):
    with patch("src.application.services._catalog_get_product",
               AsyncMock(return_value={"price": 500.0, "name": "test"})), \
         patch("src.application.services._catalog_reduce_stock", AsyncMock(return_value=True)):
        order = await order_service.create_order(uuid4(), _order_create((1, 500.0)))
    with pytest.raises(ValueError, match="Invalid status"):
        await order_service.update_order_status(order.id, "invalid_status")


@pytest.mark.asyncio
async def test_update_order_status_not_found(order_service):
    with pytest.raises(ValueError, match="Order not found"):
        await order_service.update_order_status(uuid4(), "confirmed")


# ── Items ─────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_get_order_items(order_service):
    with patch("src.application.services._catalog_get_product",
               AsyncMock(return_value={"price": 1000.0, "name": "test"})), \
         patch("src.application.services._catalog_reduce_stock", AsyncMock(return_value=True)):
        order = await order_service.create_order(uuid4(), _order_create((3, 1000.0)))
    items = await order_service.get_order_items(order.id)
    assert len(items) == 1
    assert items[0]["quantity"] == 3
    assert items[0]["unit_price"] == 1000.0
    assert items[0]["subtotal"] == 3000.0


@pytest.mark.asyncio
async def test_add_item_to_existing_order(order_service):
    with patch("src.application.services._catalog_get_product",
               AsyncMock(return_value={"price": 500.0, "name": "test"})), \
         patch("src.application.services._catalog_reduce_stock", AsyncMock(return_value=True)):
        order = await order_service.create_order(uuid4(), _order_create((1, 500.0)))
    result = await order_service.add_item_to_order(order.id, uuid4(), 5, 1000.0)
    assert result["subtotal"] == 5000.0


@pytest.mark.asyncio
async def test_add_item_order_not_found(order_service):
    with pytest.raises(ValueError, match="Order not found"):
        await order_service.add_item_to_order(uuid4(), uuid4(), 1, 100.0)
