import pytest
import hashlib
import json
from uuid import uuid4
from unittest.mock import AsyncMock, patch

from src.infrastructure.repositories import (
    TransactionRepository, PaymentMethodRepository, WebhookLogRepository
)
from src.application.services import PaymentService
from src.application.dtos import TransactionCreate


@pytest.fixture
async def payment_service(db_session):
    return PaymentService(
        TransactionRepository(db_session),
        PaymentMethodRepository(db_session),
        WebhookLogRepository(db_session),
    )


# ── TransactionCreate validaciones ───────────────────────────────────────────

def test_transaction_create_amount_zero_rejected():
    with pytest.raises(Exception):
        TransactionCreate(order_id=uuid4(), amount=0, payment_method="card")


def test_transaction_create_amount_negative_rejected():
    with pytest.raises(Exception):
        TransactionCreate(order_id=uuid4(), amount=-100.0, payment_method="card")


# ── Crear transacción ─────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_create_transaction(payment_service):
    order_id = uuid4()
    user_id = uuid4()
    with patch("src.application.services._order_get_total", AsyncMock(return_value=50000.0)):
        tx = await payment_service.create_transaction(order_id, user_id, 50000.0, "card")
    assert tx.amount == 50000.0
    assert tx.status == "pending"


@pytest.mark.asyncio
async def test_create_transaction_stores_order_id(payment_service):
    order_id = uuid4()
    with patch("src.application.services._order_get_total", AsyncMock(return_value=10000.0)):
        tx = await payment_service.create_transaction(order_id, uuid4(), 10000.0, "card")
    assert tx.order_id == order_id


# ── Obtener transacción ───────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_get_transaction(payment_service):
    with patch("src.application.services._order_get_total", AsyncMock(return_value=50000.0)):
        created = await payment_service.create_transaction(uuid4(), uuid4(), 50000.0, "card")
    retrieved = await payment_service.get_transaction(created.id)
    assert retrieved.id == created.id


@pytest.mark.asyncio
async def test_get_transaction_not_found(payment_service):
    with pytest.raises(ValueError, match="Transaction not found"):
        await payment_service.get_transaction(uuid4())


# ── Métodos de pago ───────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_save_payment_method(payment_service):
    result = await payment_service.save_payment_method(
        user_id=uuid4(),
        method_type="CREDIT_CARD",
        reference="tok_test_123",
        last_four_digits="1234",
        card_brand="VISA",
    )
    assert result["method_type"] == "CREDIT_CARD"
    assert result["is_default"] is False


# ── Webhook handler ───────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_handle_webhook_invalid_signature(payment_service):
    payload = {"event": "transaction.updated", "data": {"transaction": {}}}
    with pytest.raises(ValueError, match="Invalid webhook signature"):
        await payment_service.handle_wompi_webhook(payload, "bad_signature")


@pytest.mark.asyncio
async def test_handle_webhook_approved_updates_transaction(payment_service):
    """Transacción aprobada vía webhook pasa a estado 'completed'."""
    with patch("src.application.services._order_get_total", AsyncMock(return_value=80000.0)):
        tx = await payment_service.create_transaction(uuid4(), uuid4(), 80000.0, "card")

    tx_repo = payment_service.transaction_repo
    await tx_repo.update_status(tx.id, "processing", wompi_reference="wompi_ref_001")
    await tx_repo.save()

    amount_in_cents = int(float(tx.amount) * 100)
    secret = "test-events-secret"
    payment_service.wompi.events_secret = secret
    timestamp = "1234567890"
    properties = ["data.transaction.id", "data.transaction.status"]
    data_block = {"transaction": {"id": "wompi_ref_001", "status": "APPROVED"}}
    parts = []
    for prop in properties:
        keys = prop.split(".")
        val = data_block
        for k in keys:
            val = val.get(k, "") if isinstance(val, dict) else ""
        parts.append(str(val))
    raw = "".join(parts) + timestamp + secret
    checksum = hashlib.sha256(raw.encode()).hexdigest()

    payload = {
        "id": "evt_approved_test_001",
        "event": "transaction.updated",
        "timestamp": timestamp,
        "signature": {"properties": properties, "checksum": checksum},
        "data": {
            "transaction": {
                "id": "wompi_ref_001",
                "status": "APPROVED",
                "amount_in_cents": amount_in_cents,
                "currency": "COP",
            }
        },
    }

    with patch("src.application.services._order_update_status"):
        result = await payment_service.handle_wompi_webhook(payload, "")

    assert result == {"status": "received"}
    updated = await tx_repo.find_by_id(tx.id)
    assert updated.status == "completed"
