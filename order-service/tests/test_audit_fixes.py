"""
Tests para los fixes de auditoría — order-service.
Cubren:
  - Cleanup de órdenes huérfanas (pending_payment > N min → expired)
  - Stock restaurado al expirar una orden
  - Estados pending_payment / paid / expired aceptados
"""
import pytest
from datetime import datetime, timezone, timedelta
from uuid import uuid4
from unittest.mock import patch
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import StaticPool

from src.infrastructure.database import Base
from src.infrastructure.repositories import (
    OrderRepository, OrderItemRepository, ShippingAddressRepository, OrderHistoryRepository,
)
from src.infrastructure.models import Order, OrderItem
from src.application.services import OrderService


@pytest.fixture
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


@pytest.fixture
async def session_factory(db_engine):
    return async_sessionmaker(db_engine, class_=AsyncSession, expire_on_commit=False)


@pytest.fixture
async def order_service(session_factory):
    async with session_factory() as session:
        yield OrderService(
            OrderRepository(session),
            OrderItemRepository(session),
            ShippingAddressRepository(session),
            OrderHistoryRepository(session),
        )


# ── Helpers ──────────────────────────────────────────────────────────────────

async def _insert_old_order(session, user_id, status="pending_payment", minutes_ago=45):
    """Inserta una orden antigua directamente en DB (sin stock reservation)."""
    created_at = datetime.now(timezone.utc) - timedelta(minutes=minutes_ago)
    order = Order(
        order_number=f"OLD-{uuid4().hex[:8].upper()}",
        user_id=user_id,
        status=status,
        subtotal=10000,
        total=10000,
        created_at=created_at,
    )
    session.add(order)
    await session.flush()
    item = OrderItem(
        order_id=order.id,
        product_id=uuid4(),
        quantity=2,
        unit_price=5000,
        subtotal=10000,
    )
    session.add(item)
    await session.flush()
    return order, item


# ── Cleanup expira órdenes ────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_cleanup_marks_old_pending_payment_as_expired(session_factory):
    """Orden pending_payment > 30 min se marca expired y se restaura stock."""
    user_id = uuid4()
    restored = []

    async def _mock_restore(product_id, qty):
        restored.append((product_id, qty))

    async with session_factory() as session:
        old_order, item = await _insert_old_order(session, user_id, minutes_ago=45)
        await session.commit()
        old_order_id = old_order.id
        item_product_id = item.product_id
        item_qty = item.quantity

    async with session_factory() as session:
        svc = OrderService(
            OrderRepository(session),
            OrderItemRepository(session),
            ShippingAddressRepository(session),
            OrderHistoryRepository(session),
        )
        with patch("src.application.services._catalog_restore_stock", _mock_restore):
            n = await svc.cleanup_expired_orders(timeout_minutes=30)

    assert n == 1
    assert (item_product_id, item_qty) in restored

    # Verificar que la orden quedó como "expired"
    async with session_factory() as session:
        from sqlalchemy import select
        result = await session.execute(select(Order).where(Order.id == old_order_id))
        order = result.scalars().first()
        assert order.status == "expired"


@pytest.mark.asyncio
async def test_cleanup_ignores_recent_orders(session_factory):
    """Órdenes recientes (< 30 min) NO se expiran."""
    user_id = uuid4()

    async with session_factory() as session:
        await _insert_old_order(session, user_id, minutes_ago=10)
        await session.commit()

    async with session_factory() as session:
        svc = OrderService(
            OrderRepository(session),
            OrderItemRepository(session),
            ShippingAddressRepository(session),
            OrderHistoryRepository(session),
        )
        with patch("src.application.services._catalog_restore_stock"):
            n = await svc.cleanup_expired_orders(timeout_minutes=30)

    assert n == 0


@pytest.mark.asyncio
async def test_cleanup_ignores_paid_orders(session_factory):
    """Órdenes 'paid' antiguas NO se expiran (ya pagadas)."""
    user_id = uuid4()

    async with session_factory() as session:
        await _insert_old_order(session, user_id, status="paid", minutes_ago=120)
        await session.commit()

    async with session_factory() as session:
        svc = OrderService(
            OrderRepository(session),
            OrderItemRepository(session),
            ShippingAddressRepository(session),
            OrderHistoryRepository(session),
        )
        with patch("src.application.services._catalog_restore_stock"):
            n = await svc.cleanup_expired_orders(timeout_minutes=30)

    assert n == 0


@pytest.mark.asyncio
async def test_cleanup_handles_legacy_pending(session_factory):
    """Órdenes en estado legacy 'pending' también deben expirar."""
    user_id = uuid4()

    async with session_factory() as session:
        await _insert_old_order(session, user_id, status="pending", minutes_ago=60)
        await session.commit()

    async with session_factory() as session:
        svc = OrderService(
            OrderRepository(session),
            OrderItemRepository(session),
            ShippingAddressRepository(session),
            OrderHistoryRepository(session),
        )
        with patch("src.application.services._catalog_restore_stock"):
            n = await svc.cleanup_expired_orders(timeout_minutes=30)

    assert n == 1


# ── Validación de estados ────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_update_order_status_accepts_paid(order_service):
    """El nuevo estado 'paid' debe aceptarse."""
    user_id = uuid4()
    # Crear orden vía repo directo para evitar dependencia del catalog
    order = await order_service.order_repo.create(
        order_number="TEST-001",
        user_id=user_id,
        total=10000,
        subtotal=10000,
        status="pending_payment",
    )
    await order_service.order_repo.save()

    result = await order_service.update_order_status(order.id, "paid")
    assert result.status == "paid"


@pytest.mark.asyncio
async def test_update_order_status_accepts_expired(order_service):
    """El nuevo estado 'expired' debe aceptarse."""
    order = await order_service.order_repo.create(
        order_number="TEST-002",
        user_id=uuid4(),
        total=10000,
        subtotal=10000,
        status="pending_payment",
    )
    await order_service.order_repo.save()

    result = await order_service.update_order_status(order.id, "expired")
    assert result.status == "expired"


@pytest.mark.asyncio
async def test_update_order_status_rejects_invalid(order_service):
    """Estados inventados deben rechazarse."""
    order = await order_service.order_repo.create(
        order_number="TEST-003",
        user_id=uuid4(),
        total=10000,
        subtotal=10000,
    )
    await order_service.order_repo.save()

    with pytest.raises(ValueError, match="Invalid status"):
        await order_service.update_order_status(order.id, "magic_state")


# ── P0-3: bloquear transición expired → paid (webhook tardío) ────────────────

@pytest.mark.asyncio
async def test_update_order_status_blocks_expired_to_paid(order_service):
    """Webhook tardío llega APPROVED sobre orden ya expirada → debe bloquearse."""
    order = await order_service.order_repo.create(
        order_number="TEST-EXPIRED",
        user_id=uuid4(),
        total=10000,
        subtotal=10000,
        status="expired",
    )
    await order_service.order_repo.save()

    with pytest.raises(ValueError, match="cannot mark paid"):
        await order_service.update_order_status(order.id, "paid")

    # La orden NO cambió de estado
    refreshed = await order_service.order_repo.find_by_id(order.id)
    assert refreshed.status == "expired"


@pytest.mark.asyncio
async def test_update_order_status_blocks_cancelled_to_paid(order_service):
    """Webhook tardío sobre orden cancelada también debe bloquearse."""
    order = await order_service.order_repo.create(
        order_number="TEST-CANCELLED",
        user_id=uuid4(),
        total=10000,
        subtotal=10000,
        status="cancelled",
    )
    await order_service.order_repo.save()

    with pytest.raises(ValueError, match="cannot mark paid"):
        await order_service.update_order_status(order.id, "paid")


@pytest.mark.asyncio
async def test_update_order_status_allows_normal_paid_transition(order_service):
    """pending_payment → paid sigue funcionando (flujo normal)."""
    order = await order_service.order_repo.create(
        order_number="TEST-NORMAL",
        user_id=uuid4(),
        total=10000,
        subtotal=10000,
        status="pending_payment",
    )
    await order_service.order_repo.save()

    result = await order_service.update_order_status(order.id, "paid")
    assert result.status == "paid"


# ── P0-2: shipping_address_id debe pertenecer al user ────────────────────────

@pytest.mark.asyncio
async def test_create_order_rejects_address_of_another_user(order_service):
    """IDOR: user A no puede usar address de user B en una orden."""
    from src.application.dtos import OrderCreate, ShippingAddressCreate, OrderItemCreate

    user_a = uuid4()
    user_b = uuid4()

    addr_b = await order_service.create_shipping_address(
        user_b,
        ShippingAddressCreate(
            address_line1="Calle B 1-2",
            city="Tunja",
            postal_code="150001",
        ),
    )

    # User A intenta usar el address_id de B
    order_data = OrderCreate(
        items=[OrderItemCreate(product_id=uuid4(), quantity=1)],
        shipping_address_id=addr_b.id,
    )
    with pytest.raises(ValueError, match="Invalid shipping address"):
        await order_service.create_order(user_a, order_data)


# ── P0-4: admin cancel de orden paid debe ser rechazado ──────────────────────

@pytest.mark.asyncio
async def test_cancel_order_admin_cannot_cancel_paid(order_service):
    """Admin NO puede cancelar orden paid via este endpoint — debe refundar en Wompi."""
    admin_id = uuid4()
    user_id = uuid4()
    order = await order_service.order_repo.create(
        order_number="TEST-PAID",
        user_id=user_id,
        total=10000,
        subtotal=10000,
        status="paid",
    )
    await order_service.order_repo.save()

    with pytest.raises(ValueError, match="refund en Wompi"):
        await order_service.cancel_order(order.id, admin_id, is_admin=True)


@pytest.mark.asyncio
async def test_cancel_order_admin_cancels_pending_payment(order_service):
    """Admin sí puede cancelar pending_payment normalmente."""
    admin_id = uuid4()
    user_id = uuid4()
    order = await order_service.order_repo.create(
        order_number="TEST-PEND",
        user_id=user_id,
        total=10000,
        subtotal=10000,
        status="pending_payment",
    )
    await order_service.order_repo.save()

    with patch("src.application.services._catalog_restore_stock"):
        result = await order_service.cancel_order(order.id, admin_id, is_admin=True)
    assert result.status == "cancelled"


# ── P0-5: quantity max debe ser 20 ──────────────────────────────────────────

def test_order_item_quantity_max_is_20():
    """OrderItemCreate rechaza quantity > 20 (previene DoS de inventario)."""
    from src.application.dtos import OrderItemCreate
    from pydantic import ValidationError

    OrderItemCreate(product_id=uuid4(), quantity=20)  # OK
    with pytest.raises(ValidationError):
        OrderItemCreate(product_id=uuid4(), quantity=21)
    with pytest.raises(ValidationError):
        OrderItemCreate(product_id=uuid4(), quantity=9999)
