"""
Tests para los fixes de auditoría de producción.
Cubren:
  - Race condition en create_transaction (UNIQUE PARTIAL INDEX + IntegrityError)
  - Webhook idempotency por event_id
  - Webhook amount/currency validation
"""
import pytest
import hashlib
import hmac
import json
import asyncio
from uuid import uuid4
from unittest.mock import patch
from sqlalchemy import JSON
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import StaticPool

from src.infrastructure.database import Base
from src.infrastructure.repositories import (
    TransactionRepository, PaymentMethodRepository, WebhookLogRepository,
)
from src.application.services import PaymentService


def _patch_for_sqlite():
    """SQLite no soporta JSONB; convertir a JSON. Tampoco schema namespaces."""
    for table in Base.metadata.sorted_tables:
        setattr(table, "schema", None)
        for col in table.columns:
            if isinstance(col.type, JSONB):
                col.type = JSON()


@pytest.fixture
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


@pytest.fixture
async def session_factory(db_engine):
    return async_sessionmaker(db_engine, class_=AsyncSession, expire_on_commit=False)


@pytest.fixture
async def payment_service(session_factory):
    async with session_factory() as session:
        yield PaymentService(
            TransactionRepository(session),
            PaymentMethodRepository(session),
            WebhookLogRepository(session),
        )


# ── Helpers ──────────────────────────────────────────────────────────────────

async def _fake_order_total(*args, **kwargs):
    """Mock que retorna un total fijo para el order-service."""
    return 50000.0


# ── 1. Race condition / doble cobro ─────────────────────────────────────────

@pytest.mark.asyncio
async def test_create_transaction_idempotent_returns_existing(payment_service):
    """Si ya hay una transacción pending para el order, retornarla en vez de crear otra."""
    order_id = uuid4()
    user_id = uuid4()
    with patch("src.application.services._order_get_total", _fake_order_total):
        tx1 = await payment_service.create_transaction(order_id, user_id, 50000.0, "card")
        tx2 = await payment_service.create_transaction(order_id, user_id, 50000.0, "card")
    assert tx1.id == tx2.id, "Segunda llamada debe retornar la primera transacción"


@pytest.mark.asyncio
async def test_create_transaction_blocked_if_already_completed(payment_service):
    """Si ya hay una transacción completada, no permitir crear otra."""
    order_id = uuid4()
    with patch("src.application.services._order_get_total", _fake_order_total):
        tx = await payment_service.create_transaction(order_id, uuid4(), 50000.0, "card")
        # Marcar como completed
        await payment_service.transaction_repo.update_status(tx.id, "completed")
        await payment_service.transaction_repo.save()
        with pytest.raises(ValueError, match="Order already paid"):
            await payment_service.create_transaction(order_id, uuid4(), 50000.0, "card")


@pytest.mark.asyncio
async def test_unique_partial_index_blocks_second_active_transaction(session_factory):
    """
    Defensa de DB: el UNIQUE PARTIAL INDEX rechaza una segunda transacción
    activa para el mismo order incluso si bypasea el find-check del service.
    Sin este index, dos requests concurrentes podrían crear duplicados → doble cobro.
    """
    from src.infrastructure.models import Transaction
    from sqlalchemy.exc import IntegrityError

    order_id = uuid4()

    # Primera transacción: status pending
    async with session_factory() as session:
        t1 = Transaction(
            order_id=order_id,
            user_id=uuid4(),
            amount=50000,
            payment_method="card",
            status="pending",
        )
        session.add(t1)
        await session.commit()

    # Segunda transacción para el MISMO order (también activa) — debe fallar
    async with session_factory() as session:
        t2 = Transaction(
            order_id=order_id,
            user_id=uuid4(),
            amount=50000,
            payment_method="card",
            status="pending",
        )
        session.add(t2)
        with pytest.raises(IntegrityError):
            await session.commit()


@pytest.mark.asyncio
async def test_failed_transaction_allows_retry(session_factory):
    """
    Cuando la primera transacción está en estado 'failed' (no activo),
    se permite crear una nueva transacción para el mismo order (retry).
    """
    from src.infrastructure.models import Transaction
    order_id = uuid4()

    async with session_factory() as session:
        t1 = Transaction(
            order_id=order_id, user_id=uuid4(), amount=50000,
            payment_method="card", status="failed",
        )
        session.add(t1)
        await session.commit()

    # Retry debe funcionar — failed no está en el partial index
    async with session_factory() as session:
        t2 = Transaction(
            order_id=order_id, user_id=uuid4(), amount=50000,
            payment_method="card", status="pending",
        )
        session.add(t2)
        await session.commit()  # No debe lanzar


# ── 2. Webhook idempotency por event_id ──────────────────────────────────────

def _sign_event(payload: dict, secret: str) -> dict:
    """Construye un payload con firma HMAC válida (formato Wompi v1)."""
    timestamp = "1234567890"
    properties = ["data.transaction.id", "data.transaction.status"]
    # Concatena valores siguiendo el orden de las properties
    data = payload.get("data", {})
    parts = []
    for p in properties:
        keys = p.split(".")
        val = data
        for k in keys:
            val = val.get(k, "") if isinstance(val, dict) else ""
        parts.append(str(val))
    raw = "".join(parts) + timestamp + secret
    checksum = hashlib.sha256(raw.encode()).hexdigest()
    payload["timestamp"] = timestamp
    payload["signature"] = {"properties": properties, "checksum": checksum}
    return payload


@pytest.mark.asyncio
async def test_webhook_duplicate_event_id_is_idempotent(payment_service, monkeypatch):
    """Un mismo event_id enviado dos veces solo debe procesar UNA VEZ."""
    secret = "test-events-secret"
    payment_service.wompi.events_secret = secret

    order_id = uuid4()
    with patch("src.application.services._order_get_total", _fake_order_total), \
         patch("src.application.services._order_update_status"):
        tx = await payment_service.create_transaction(order_id, uuid4(), 50000.0, "card")
        await payment_service.transaction_repo.update_status(
            tx.id, "processing", wompi_reference="WMP-001"
        )
        await payment_service.transaction_repo.save()

        payload = {
            "id": "evt_unique_123",
            "event": "transaction.updated",
            "data": {
                "transaction": {
                    "id": "WMP-001",
                    "status": "APPROVED",
                    "amount_in_cents": 5000000,
                    "currency": "COP",
                }
            },
        }
        _sign_event(payload, secret)

        first = await payment_service.handle_wompi_webhook(payload, "")
        second = await payment_service.handle_wompi_webhook(payload, "")

    assert first["status"] == "received"
    assert second["status"] == "duplicate"


# ── 3. Webhook amount mismatch ───────────────────────────────────────────────

@pytest.mark.asyncio
async def test_webhook_amount_mismatch_is_rejected(payment_service):
    """Si Wompi reporta un amount distinto al guardado en DB, rechazar."""
    secret = "test-events-secret"
    payment_service.wompi.events_secret = secret

    order_id = uuid4()
    with patch("src.application.services._order_get_total", _fake_order_total), \
         patch("src.application.services._order_update_status"):
        tx = await payment_service.create_transaction(order_id, uuid4(), 50000.0, "card")
        await payment_service.transaction_repo.update_status(
            tx.id, "processing", wompi_reference="WMP-MISMATCH"
        )
        await payment_service.transaction_repo.save()

        payload = {
            "id": "evt_mismatch_1",
            "event": "transaction.updated",
            "data": {
                "transaction": {
                    "id": "WMP-MISMATCH",
                    "status": "APPROVED",
                    "amount_in_cents": 100,  # DB tiene 5_000_000
                    "currency": "COP",
                }
            },
        }
        _sign_event(payload, secret)

        result = await payment_service.handle_wompi_webhook(payload, "")

    assert result["status"] == "rejected"
    assert result["reason"] == "amount_mismatch"

    # Verificar que la transacción NO se marcó completed
    updated = await payment_service.transaction_repo.find_by_id(tx.id)
    assert updated.status == "processing"


# ── 4. Webhook currency mismatch ─────────────────────────────────────────────

@pytest.mark.asyncio
async def test_webhook_currency_mismatch_is_rejected(payment_service):
    """Wompi reportando una moneda distinta a COP debe ser rechazado."""
    secret = "test-events-secret"
    payment_service.wompi.events_secret = secret

    order_id = uuid4()
    with patch("src.application.services._order_get_total", _fake_order_total), \
         patch("src.application.services._order_update_status"):
        tx = await payment_service.create_transaction(order_id, uuid4(), 50000.0, "card")
        await payment_service.transaction_repo.update_status(
            tx.id, "processing", wompi_reference="WMP-CURR"
        )
        await payment_service.transaction_repo.save()

        payload = {
            "id": "evt_curr_1",
            "event": "transaction.updated",
            "data": {
                "transaction": {
                    "id": "WMP-CURR",
                    "status": "APPROVED",
                    "amount_in_cents": 5000000,
                    "currency": "USD",  # ← no COP
                }
            },
        }
        _sign_event(payload, secret)

        result = await payment_service.handle_wompi_webhook(payload, "")

    assert result["status"] == "rejected"
    assert result["reason"] == "currency_mismatch"


# ── 5. Webhook APPROVED → completed cuando todo es válido ──────────────────

@pytest.mark.asyncio
async def test_webhook_approved_success_marks_completed(payment_service):
    """Caso correcto: amount y currency válidos → transacción pasa a 'completed'."""
    secret = "test-events-secret"
    payment_service.wompi.events_secret = secret

    order_id = uuid4()
    with patch("src.application.services._order_get_total", _fake_order_total), \
         patch("src.application.services._order_update_status"):
        tx = await payment_service.create_transaction(order_id, uuid4(), 50000.0, "card")
        await payment_service.transaction_repo.update_status(
            tx.id, "processing", wompi_reference="WMP-OK"
        )
        await payment_service.transaction_repo.save()

        payload = {
            "id": "evt_ok_1",
            "event": "transaction.updated",
            "data": {
                "transaction": {
                    "id": "WMP-OK",
                    "status": "APPROVED",
                    "amount_in_cents": 5000000,
                    "currency": "COP",
                }
            },
        }
        _sign_event(payload, secret)

        result = await payment_service.handle_wompi_webhook(payload, "")

    assert result["status"] == "received"
    updated = await payment_service.transaction_repo.find_by_id(tx.id)
    assert updated.status == "completed"


# ── P0-6: webhook sin event_id rechazado ────────────────────────────────────

@pytest.mark.asyncio
async def test_webhook_missing_event_id_is_rejected(payment_service):
    """Webhook sin `id` ni `event_id` debe rechazarse — no podemos deduplicar."""
    secret = "test-events-secret"
    payment_service.wompi.events_secret = secret

    payload = {
        # SIN "id" ni "event_id"
        "event": "transaction.updated",
        "data": {"transaction": {"id": "WMP-ABC", "status": "APPROVED",
                                 "amount_in_cents": 5000000, "currency": "COP"}},
    }
    _sign_event(payload, secret)

    result = await payment_service.handle_wompi_webhook(payload, "")
    assert result["status"] == "rejected"
    assert result["reason"] == "missing_event_id"


# ── 6. Webhook DECLINED no debe bajar de completed ─────────────────────────

@pytest.mark.asyncio
async def test_webhook_declined_ignored_if_already_completed(payment_service):
    """Out-of-order webhook: DECLINED después de APPROVED no debe revertir."""
    secret = "test-events-secret"
    payment_service.wompi.events_secret = secret

    order_id = uuid4()
    with patch("src.application.services._order_get_total", _fake_order_total), \
         patch("src.application.services._order_update_status"):
        tx = await payment_service.create_transaction(order_id, uuid4(), 50000.0, "card")
        await payment_service.transaction_repo.update_status(
            tx.id, "completed", wompi_reference="WMP-FINAL"
        )
        await payment_service.transaction_repo.save()

        payload = {
            "id": "evt_declined_late",
            "event": "transaction.updated",
            "data": {
                "transaction": {
                    "id": "WMP-FINAL",
                    "status": "DECLINED",
                    "amount_in_cents": 5000000,
                    "currency": "COP",
                    "status_message": "Late decline",
                }
            },
        }
        _sign_event(payload, secret)

        await payment_service.handle_wompi_webhook(payload, "")

    updated = await payment_service.transaction_repo.find_by_id(tx.id)
    assert updated.status == "completed", "Transacción completa no debe revertirse"
