"""
Tests HTTP del payment-service — endpoints /payments/*
Ejecutar: cd payment-service && pytest tests/test_http_payments.py -v
"""
import pytest
import hashlib
import json
from uuid import uuid4
from unittest.mock import AsyncMock, patch


# ═══════════════════════════════════════════════════════════════════════════════
# POST /payments/transactions
# ═══════════════════════════════════════════════════════════════════════════════

class TestCreateTransaction:

    @pytest.mark.unit
    async def test_create_transaction_success(self, async_client, user_id, transaction_payload):
        with patch("src.application.services._order_get_total", return_value=50000.0):
            resp = await async_client.post(
                "/payments/transactions",
                json=transaction_payload,
                params={"user_id": str(user_id)},
            )
        assert resp.status_code == 201
        body = resp.json()
        assert body["amount"] == 50000.0
        assert body["status"] == "pending"
        assert "id" in body

    @pytest.mark.unit
    async def test_create_transaction_zero_amount_rejected(self, async_client, user_id):
        """422 — amount = 0 no permitido."""
        resp = await async_client.post(
            "/payments/transactions",
            json={"order_id": str(uuid4()), "amount": 0, "payment_method": "card"},
            params={"user_id": str(user_id)},
        )
        assert resp.status_code == 422

    @pytest.mark.unit
    async def test_create_transaction_negative_amount_rejected(self, async_client, user_id):
        """422 — amount negativo no permitido."""
        resp = await async_client.post(
            "/payments/transactions",
            json={"order_id": str(uuid4()), "amount": -100.0, "payment_method": "card"},
            params={"user_id": str(user_id)},
        )
        assert resp.status_code == 422

    @pytest.mark.unit
    async def test_create_transaction_missing_order_id(self, async_client, user_id):
        """422 — falta order_id."""
        resp = await async_client.post(
            "/payments/transactions",
            json={"amount": 10000.0, "payment_method": "card"},
            params={"user_id": str(user_id)},
        )
        assert resp.status_code == 422

    @pytest.mark.unit
    async def test_create_transaction_missing_user_id(self, async_client, transaction_payload):
        """422 — falta user_id."""
        resp = await async_client.post("/payments/transactions", json=transaction_payload)
        assert resp.status_code == 422

    @pytest.mark.unit
    async def test_create_transaction_invalid_order_uuid(self, async_client, user_id):
        """422 — order_id no es UUID."""
        resp = await async_client.post(
            "/payments/transactions",
            json={"order_id": "not-a-uuid", "amount": 5000.0, "payment_method": "card"},
            params={"user_id": str(user_id)},
        )
        assert resp.status_code == 422


# ═══════════════════════════════════════════════════════════════════════════════
# GET /payments/transactions/{id}
# ═══════════════════════════════════════════════════════════════════════════════

class TestGetTransaction:

    @pytest.mark.unit
    async def test_get_transaction_success(self, async_client, created_transaction):
        resp = await async_client.get(f"/payments/transactions/{created_transaction['id']}")
        assert resp.status_code == 200
        assert resp.json()["id"] == created_transaction["id"]
        assert resp.json()["amount"] == created_transaction["amount"]

    @pytest.mark.unit
    async def test_get_transaction_not_found(self, async_client):
        resp = await async_client.get(f"/payments/transactions/{uuid4()}")
        assert resp.status_code == 404

    @pytest.mark.unit
    async def test_get_transaction_invalid_uuid(self, async_client):
        resp = await async_client.get("/payments/transactions/not-a-uuid")
        assert resp.status_code == 422


# ═══════════════════════════════════════════════════════════════════════════════
# POST /payments/wompi/checkout
# ═══════════════════════════════════════════════════════════════════════════════

class TestWompiCheckout:

    @pytest.mark.unit
    async def test_checkout_transaction_not_found(self, async_client, user_id):
        """400 — transacción no existe."""
        resp = await async_client.post(
            "/payments/wompi/checkout",
            json={"transaction_id": str(uuid4()), "customer_email": "test@test.com"},
            params={"user_id": str(user_id)},
        )
        assert resp.status_code == 400
        assert "not found" in resp.json()["detail"].lower()

    @pytest.mark.unit
    async def test_checkout_returns_url(self, async_client, user_id, created_transaction):
        """200 — devuelve checkout_url apuntando a Wompi con los parámetros requeridos."""
        resp = await async_client.post(
            "/payments/wompi/checkout",
            json={"transaction_id": created_transaction["id"], "customer_email": "cliente@papeleria.com"},
            params={"user_id": str(user_id)},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert "checkout_url" in body
        url = body["checkout_url"]
        assert "checkout.wompi.co/p/" in url
        assert "public-key=" in url
        assert "reference=" in url
        assert "amount-in-cents=" in url

    @pytest.mark.unit
    async def test_checkout_reference_encodes_transaction_id(self, async_client, user_id, created_transaction):
        """El reference contiene el transaction_id para que el webhook pueda encontrar la transacción."""
        from urllib.parse import urlparse, parse_qs

        resp = await async_client.post(
            "/payments/wompi/checkout",
            json={"transaction_id": created_transaction["id"], "customer_email": "test@test.com"},
            params={"user_id": str(user_id)},
        )
        assert resp.status_code == 200
        parsed = urlparse(resp.json()["checkout_url"])
        params = parse_qs(parsed.query)
        reference = params.get("reference", [None])[0]
        assert reference is not None
        assert reference.startswith("PB-")
        assert reference[3:] == created_transaction["id"].replace("-", "")

    @pytest.mark.unit
    async def test_checkout_already_processing_rejected(self, async_client, db_session, user_id):
        """400 — transacción que ya no está pending no puede generar checkout."""
        from src.infrastructure.repositories import TransactionRepository

        tx_repo = TransactionRepository(db_session)
        tx = await tx_repo.create(
            order_id=uuid4(),
            user_id=user_id,
            amount=30000.0,
            payment_method="wompi",
            status="completed",
        )
        await tx_repo.save()

        resp = await async_client.post(
            "/payments/wompi/checkout",
            json={"transaction_id": str(tx.id), "customer_email": "test@test.com"},
            params={"user_id": str(user_id)},
        )
        assert resp.status_code == 400
        assert "completed" in resp.json()["detail"].lower()


# ═══════════════════════════════════════════════════════════════════════════════
# POST /payments/webhooks/wompi
# ═══════════════════════════════════════════════════════════════════════════════

_EVENTS_SECRET = "test-events-secret"


def _sign_event(payload: dict, secret: str = _EVENTS_SECRET) -> dict:
    """Build a properly-signed Wompi webhook payload (same algorithm as WompiClient.verify_webhook)."""
    timestamp = "1234567890"
    data = payload.get("data", {})
    transaction = data.get("transaction", {})
    properties = ["data.transaction.id", "data.transaction.status"]
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


class TestWompiWebhook:

    @pytest.mark.unit
    async def test_webhook_missing_signature(self, async_client):
        """401 — sin header X-Event-Checksum."""
        resp = await async_client.post(
            "/payments/webhooks/wompi",
            json={"event": "transaction.updated"},
        )
        assert resp.status_code == 401

    @pytest.mark.unit
    async def test_webhook_invalid_signature(self, async_client):
        """401 — checksum incorrecto en payload."""
        payload = {
            "event": "transaction.updated",
            "data": {"transaction": {"id": "ref_001", "status": "APPROVED"}},
            "timestamp": "123",
            "signature": {"properties": ["data.transaction.id"], "checksum": "badhash"},
        }
        resp = await async_client.post(
            "/payments/webhooks/wompi",
            json=payload,
            headers={"x-event-checksum": "any-value"},
        )
        assert resp.status_code == 401

    @pytest.mark.unit
    async def test_webhook_approved_updates_transaction(self, async_client, db_session, user_id):
        """200 — evento APPROVED actualiza transacción a 'completed'."""
        from src.infrastructure.repositories import TransactionRepository

        tx_repo = TransactionRepository(db_session)
        tx = await tx_repo.create(
            order_id=uuid4(),
            user_id=user_id,
            amount=50000.0,
            payment_method="card",
            status="processing",
            wompi_reference="WOMPI_REF_ABC",
        )
        await tx_repo.save()

        payload = {
            "id": "evt_approved_abc",
            "event": "transaction.updated",
            "data": {
                "transaction": {
                    "id": "WOMPI_REF_ABC",
                    "status": "APPROVED",
                    "amount_in_cents": 5000000,
                    "currency": "COP",
                }
            },
        }
        _sign_event(payload)

        with patch("src.application.services._order_update_status"):
            resp = await async_client.post(
                "/payments/webhooks/wompi",
                content=json.dumps(payload),
                headers={"Content-Type": "application/json", "x-event-checksum": "any"},
            )
        assert resp.status_code == 200
        assert resp.json() == {"status": "received"}

        updated = await tx_repo.find_by_id(tx.id)
        assert updated.status == "completed"

    @pytest.mark.unit
    async def test_webhook_declined_updates_transaction(self, async_client, db_session, user_id):
        """200 — evento DECLINED actualiza transacción a 'failed'."""
        from src.infrastructure.repositories import TransactionRepository

        tx_repo = TransactionRepository(db_session)
        tx = await tx_repo.create(
            order_id=uuid4(),
            user_id=user_id,
            amount=20000.0,
            payment_method="card",
            status="processing",
            wompi_reference="WOMPI_REF_DEF",
        )
        await tx_repo.save()

        payload = {
            "id": "evt_declined_def",
            "event": "transaction.updated",
            "data": {
                "transaction": {
                    "id": "WOMPI_REF_DEF",
                    "status": "DECLINED",
                    "status_message": "Fondos insuficientes",
                }
            },
        }
        _sign_event(payload)

        resp = await async_client.post(
            "/payments/webhooks/wompi",
            content=json.dumps(payload),
            headers={"Content-Type": "application/json", "x-event-checksum": "any"},
        )
        assert resp.status_code == 200

        updated = await tx_repo.find_by_id(tx.id)
        assert updated.status == "failed"

    @pytest.mark.unit
    async def test_webhook_unknown_event_accepted(self, async_client):
        """200 — evento desconocido se registra pero no falla."""
        payload = {"id": "evt_unknown_001", "event": "some.other.event", "data": {}}
        _sign_event(payload)

        resp = await async_client.post(
            "/payments/webhooks/wompi",
            content=json.dumps(payload),
            headers={"Content-Type": "application/json", "x-event-checksum": "any"},
        )
        assert resp.status_code == 200

    @pytest.mark.unit
    async def test_webhook_approved_via_reference_fallback(self, async_client, db_session, user_id):
        """Hosted checkout: wompi_reference es NULL hasta que llega el webhook.
        El handler debe encontrar la transacción por reference (PB-{txn_id_hex})
        y después setear wompi_reference para que reintentos usen el camino rápido."""
        from src.infrastructure.repositories import TransactionRepository

        tx_repo = TransactionRepository(db_session)
        tx = await tx_repo.create(
            order_id=uuid4(),
            user_id=user_id,
            amount=75000.0,
            payment_method="wompi",
            status="pending",
            # wompi_reference intencionalmente NULL — simula hosted checkout
        )
        await tx_repo.save()

        our_reference = f"PB-{tx.id.hex}"
        payload = {
            "id": "evt_fallback_hosted_001",
            "event": "transaction.updated",
            "data": {
                "transaction": {
                    "id": "WOMPI_HOSTED_REF_001",
                    "reference": our_reference,
                    "status": "APPROVED",
                    "amount_in_cents": 7500000,
                    "currency": "COP",
                }
            },
        }
        _sign_event(payload)

        with patch("src.application.services._order_update_status"):
            resp = await async_client.post(
                "/payments/webhooks/wompi",
                content=json.dumps(payload),
                headers={"Content-Type": "application/json", "x-event-checksum": "any"},
            )
        assert resp.status_code == 200
        assert resp.json() == {"status": "received"}

        updated = await tx_repo.find_by_id(tx.id)
        assert updated.status == "completed"
        # wompi_reference queda seteado para que reintentos usen find_by_wompi_reference
        assert updated.wompi_reference == "WOMPI_HOSTED_REF_001"

    @pytest.mark.unit
    async def test_webhook_retry_after_fallback_uses_wompi_reference(self, async_client, db_session, user_id):
        """Verifica el flujo completo de dos pasos del hosted checkout:

        Paso 1 — primer webhook: wompi_reference es NULL, el fallback encuentra la
        transacción por PB-{uuid}, la marca completed y guarda wompi_reference.

        Paso 2 — retry de Wompi (event_id distinto): find_by_wompi_reference la
        encuentra directamente sin usar el fallback. El handler la ignora porque
        ya está completed, sin errors ni side effects.
        """
        from src.infrastructure.repositories import TransactionRepository

        tx_repo = TransactionRepository(db_session)
        tx = await tx_repo.create(
            order_id=uuid4(),
            user_id=user_id,
            amount=50000.0,
            payment_method="wompi",
            status="pending",
            # wompi_reference intencionalmente NULL — estado real antes del primer webhook
        )
        await tx_repo.save()

        internal_reference = f"PB-{tx.id.hex}"

        # ── Paso 1: primer webhook llega, wompi_reference es NULL ──────────────
        payload_1 = {
            "id": "evt_two_step_001",
            "event": "transaction.updated",
            "data": {
                "transaction": {
                    "id": "WOMPI_TWO_STEP_REF",
                    "reference": internal_reference,
                    "status": "APPROVED",
                    "amount_in_cents": 5000000,
                    "currency": "COP",
                }
            },
        }
        _sign_event(payload_1)

        with patch("src.application.services._order_update_status"):
            resp_1 = await async_client.post(
                "/payments/webhooks/wompi",
                content=json.dumps(payload_1),
                headers={"Content-Type": "application/json", "x-event-checksum": "any"},
            )
        assert resp_1.status_code == 200
        assert resp_1.json() == {"status": "received"}

        # El fallback encontró la txn, la marcó completed y guardó wompi_reference
        after_first = await tx_repo.find_by_id(tx.id)
        assert after_first.status == "completed"
        assert after_first.wompi_reference == "WOMPI_TWO_STEP_REF"

        # ── Paso 2: retry de Wompi con event_id distinto ────────────────────────
        # find_by_wompi_reference la encuentra directo; el handler la ignora
        # porque ya está completed (sin romper, sin doble cobro).
        payload_2 = {
            "id": "evt_two_step_002",          # event_id distinto = retry real
            "event": "transaction.updated",
            "data": {
                "transaction": {
                    "id": "WOMPI_TWO_STEP_REF",  # mismo wompi id
                    "reference": internal_reference,
                    "status": "APPROVED",
                    "amount_in_cents": 5000000,
                    "currency": "COP",
                }
            },
        }
        _sign_event(payload_2)

        with patch("src.application.services._order_update_status") as mock_order:
            resp_2 = await async_client.post(
                "/payments/webhooks/wompi",
                content=json.dumps(payload_2),
                headers={"Content-Type": "application/json", "x-event-checksum": "any"},
            )
        assert resp_2.status_code == 200
        assert resp_2.json() == {"status": "received"}

        # Estado no cambió y _order_update_status NO se llamó segunda vez
        after_second = await tx_repo.find_by_id(tx.id)
        assert after_second.status == "completed"
        assert after_second.wompi_reference == "WOMPI_TWO_STEP_REF"
        mock_order.assert_not_called()
