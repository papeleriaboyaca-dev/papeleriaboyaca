import httpx
import hmac
import hashlib
import logging
from uuid import UUID
from datetime import datetime
from typing import Optional
from urllib.parse import urlencode
from sqlalchemy.exc import IntegrityError
from ..config import settings

logger = logging.getLogger(__name__)
from ..infrastructure.repositories import (
    TransactionRepository, PaymentMethodRepository, WebhookLogRepository
)
from ..application.dtos import TransactionResponse


def _internal_headers() -> dict:
    return {"X-Internal-Auth": settings.INTERNAL_API_SECRET} if settings.INTERNAL_API_SECRET else {}


async def _order_get_total(order_id: UUID, user_id: UUID | None = None) -> float | None:
    try:
        params = {"user_id": str(user_id)} if user_id else {}
        async with httpx.AsyncClient(timeout=10, headers=_internal_headers()) as client:
            r = await client.get(f"{settings.ORDER_SERVICE_URL}/orders/{order_id}", params=params)
            if r.status_code == 200:
                return float(r.json()["total"])
    except Exception as e:
        logger.error("Order total fetch failed for %s: %s", order_id, e)
    return None


async def _order_update_status(order_id: UUID, new_status: str) -> None:
    async with httpx.AsyncClient(timeout=10, headers=_internal_headers()) as client:
        r = await client.put(
            f"{settings.ORDER_SERVICE_URL}/orders/{order_id}/status",
            json={"status": new_status},
        )
        r.raise_for_status()


class WompiClient:
    def __init__(self):
        self.base_url = settings.WOMPI_API_URL
        self.private_key = settings.WOMPI_PRIVATE_KEY
        self.public_key = settings.WOMPI_PUBLIC_KEY
        self.events_secret = settings.WOMPI_EVENTS_SECRET
        self.integrity_secret = settings.WOMPI_INTEGRITY_SECRET

    async def get_acceptance_tokens(self) -> dict:
        """GET /merchants/{public_key} → presigned acceptance tokens."""
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.get(
                f"{self.base_url}/merchants/{self.public_key}",
                headers={"Authorization": f"Bearer {self.public_key}"},
            )
            r.raise_for_status()
            data = r.json()["data"]
            return {
                "acceptance_token": data["presigned_acceptance"]["acceptance_token"],
                "accept_personal_auth": data["presigned_personal_data_auth"]["acceptance_token"],
            }

    def _generate_signature(self, reference: str, amount_in_cents: int, currency: str = "COP") -> str:
        """SHA256(reference + amount_in_cents + currency + integrity_secret)."""
        raw = f"{reference}{amount_in_cents}{currency}{self.integrity_secret}"
        return hashlib.sha256(raw.encode()).hexdigest()

    def _build_payment_method(self, method_type: str, details: dict) -> dict:
        t = method_type.upper()
        pm: dict = {"type": t}
        if t == "CARD":
            pm["token"] = details.get("card_token")
            pm["installments"] = details.get("installments", 1)
        elif t == "NEQUI":
            pm["phone_number"] = details.get("phone_number")
        elif t == "PSE":
            pm["user_type"] = details.get("user_type", 0)
            pm["user_legal_id_type"] = details.get("user_legal_id_type", "CC")
            pm["user_legal_id"] = details.get("user_legal_id")
            pm["financial_institution_code"] = details.get("financial_institution_code")
            pm["payment_description"] = details.get("payment_description", "Pago Papelería Boyacá")
        elif t == "BANCOLOMBIA_TRANSFER":
            pm["payment_description"] = details.get("payment_description", "Pago Papelería Boyacá")
            pm["ecommerce_url"] = details.get("ecommerce_url", f"{settings.FRONTEND_URL}/pedido-confirmado")
        elif t == "BANCOLOMBIA_QR":
            pm["payment_description"] = details.get("payment_description", "Pago Papelería Boyacá")
            if details.get("sandbox_status"):
                pm["sandbox_status"] = details["sandbox_status"]
        elif t in ("DAVIPLATA",):
            pm["user_legal_id"] = details.get("user_legal_id")
            pm["user_legal_id_type"] = details.get("user_legal_id_type", "CC")
            pm["payment_description"] = details.get("payment_description", "Pago Papelería Boyacá")
        return pm

    async def create_payment(self, amount_in_cents: int, reference: str,
                             customer_email: str, payment_method: dict,
                             redirect_url: str | None = None) -> dict:
        tokens = await self.get_acceptance_tokens()
        signature = self._generate_signature(reference, amount_in_cents)
        payload = {
            "acceptance_token": tokens["acceptance_token"],
            "accept_personal_auth": tokens["accept_personal_auth"],
            "amount_in_cents": amount_in_cents,
            "currency": "COP",
            "customer_email": customer_email,
            "payment_method": payment_method,
            "reference": reference,
            "signature": signature,
            "redirect_url": redirect_url or f"{settings.FRONTEND_URL}/payments/success",
        }
        async with httpx.AsyncClient(timeout=30) as client:
            r = await client.post(
                f"{self.base_url}/transactions",
                json=payload,
                headers={"Authorization": f"Bearer {self.private_key}"},
            )
            if r.status_code >= 400:
                logger.error("Wompi POST /transactions %s: %s", r.status_code, r.text)
            r.raise_for_status()
            return r.json()

    async def get_transaction(self, wompi_transaction_id: str) -> dict:
        async with httpx.AsyncClient(timeout=30) as client:
            r = await client.get(
                f"{self.base_url}/transactions/{wompi_transaction_id}",
                headers={"Authorization": f"Bearer {self.public_key}"},
            )
            r.raise_for_status()
            return r.json()

    def verify_webhook(self, event: dict) -> bool:
        """Verify Wompi webhook: SHA256(prop_values... + timestamp + events_secret).
        Properties are listed dynamically in event.signature.properties."""
        sig = event.get("signature", {})
        properties = sig.get("properties", [])
        checksum = sig.get("checksum", "")
        timestamp = str(event.get("timestamp", ""))
        if not checksum or not properties:
            return False
        data = event.get("data", {})
        parts = []
        for prop in properties:
            keys = prop.split(".")
            val: object = data
            for k in keys:
                val = val.get(k, "") if isinstance(val, dict) else ""
            parts.append(str(val))
        raw = "".join(parts) + timestamp + self.events_secret
        expected = hashlib.sha256(raw.encode()).hexdigest()
        return hmac.compare_digest(expected.upper(), checksum.upper())


class PaymentService:
    def __init__(self, transaction_repo: TransactionRepository,
                 method_repo: PaymentMethodRepository,
                 webhook_repo: WebhookLogRepository):
        self.transaction_repo = transaction_repo
        self.method_repo = method_repo
        self.webhook_repo = webhook_repo
        self.wompi = WompiClient()

    async def create_transaction(self, order_id: UUID, user_id: UUID,
                                amount: float, payment_method: str) -> TransactionResponse:
        # Idempotencia rápida: si ya existe transacción activa, retornarla
        existing = await self.transaction_repo.find_active_by_order(order_id)
        if existing:
            if existing.status == "completed":
                raise ValueError("Order already paid")
            if existing.status in ("pending", "processing"):
                logger.info("Returning existing transaction %s for order %s (status=%s)",
                            existing.id, order_id, existing.status)
                return TransactionResponse.from_orm(existing)

        order_total = await _order_get_total(order_id, user_id)
        if order_total is None:
            raise ValueError("Order not found or total unavailable")

        failed_attempts = await self.transaction_repo.count_failed_by_order(order_id)
        if failed_attempts >= 5:
            raise ValueError("Maximum payment attempts reached for this order")

        # Race-safe: el UNIQUE PARTIAL INDEX en DB (uq_transaction_active_order)
        # garantiza que solo una transacción activa por orden pueda existir.
        try:
            transaction = await self.transaction_repo.create(
                order_id=order_id,
                user_id=user_id,
                amount=order_total,
                payment_method=payment_method,
                status="pending",
            )
            await self.transaction_repo.save()
        except IntegrityError:
            await self.transaction_repo.session.rollback()
            winner = await self.transaction_repo.find_active_by_order(order_id)
            if winner:
                logger.warning("create_transaction race lost for order %s, returning %s",
                               order_id, winner.id)
                return TransactionResponse.from_orm(winner)
            raise ValueError("Transaction creation conflict")

        logger.info("Transaction created: %s order=%s amount=%.2f method=%s",
                    transaction.id, order_id, order_total, payment_method)
        return TransactionResponse.from_orm(transaction)

    async def get_transaction(self, transaction_id: UUID, requesting_user_id: UUID | None = None,
                              is_admin: bool = False) -> TransactionResponse:
        transaction = await self.transaction_repo.find_by_id(transaction_id)
        if not transaction:
            raise ValueError("Transaction not found")
        if requesting_user_id and not is_admin and transaction.user_id != requesting_user_id:
            raise PermissionError("Not authorized to view this transaction")
        return TransactionResponse.from_orm(transaction)

    async def get_checkout_url(self, transaction_id: UUID,
                               customer_email: str,  # TODO: remove next cleanup sprint — Wompi collects email on their page
                               requesting_user_id: UUID | None = None) -> dict:
        transaction = await self.transaction_repo.find_by_id(transaction_id)
        if not transaction:
            raise ValueError("Transaction not found")
        if requesting_user_id and transaction.user_id != requesting_user_id:
            raise PermissionError("Not authorized to checkout this transaction")
        if transaction.status != "pending":
            raise ValueError(f"Transaction already in status '{transaction.status}'")

        # Increment attempt counter stored in meta to ensure unique Wompi references per attempt.
        meta = dict(transaction.meta or {})
        attempt = meta.get("checkout_attempts", 0) + 1
        meta["checkout_attempts"] = attempt
        transaction.meta = meta
        await self.transaction_repo.session.flush()
        await self.transaction_repo.save()

        amount_in_cents = int(transaction.amount * 100)
        # Attempt 1 → PB-{hex}, attempt 2+ → PB-{hex}-{attempt} (all unique to Wompi)
        reference = f"PB-{transaction_id.hex}" if attempt == 1 else f"PB-{transaction_id.hex}-{attempt}"
        signature = self.wompi._generate_signature(reference, amount_in_cents)
        redirect_url = f"{settings.FRONTEND_URL}/pedido-confirmado/{transaction.order_id}"

        params = {
            "public-key": self.wompi.public_key,
            "currency": "COP",
            "amount-in-cents": str(amount_in_cents),
            "reference": reference,
            "signature:integrity": signature,
            "redirect-url": redirect_url,
            "customer-data:email": customer_email,
        }
        checkout_url = f"https://checkout.wompi.co/p/?{urlencode(params)}"
        logger.info("Checkout URL generated: txn=%s order=%s amount=%s",
                    transaction_id, transaction.order_id, amount_in_cents)
        return {"checkout_url": checkout_url}

    async def list_user_transactions(self, user_id: UUID, skip: int = 0,
                                     limit: int = 20) -> list[TransactionResponse]:
        txns = await self.transaction_repo.find_by_user(user_id, skip, limit)
        return [TransactionResponse.from_orm(t) for t in txns]

    async def list_all_transactions(self, skip: int = 0,
                                    limit: int = 100) -> list[TransactionResponse]:
        txns = await self.transaction_repo.find_all(skip, limit)
        return [TransactionResponse.from_orm(t) for t in txns]

    async def handle_wompi_webhook(self, payload: dict, signature_header: str) -> dict:
        if not self.wompi.verify_webhook(payload):
            raise ValueError("Invalid webhook signature")

        event_type = payload.get("event")          # "transaction.updated"
        transaction = payload.get("data", {}).get("transaction", {})
        wompi_reference = transaction.get("id")
        status = transaction.get("status")         # APPROVED / DECLINED / VOIDED / ERROR

        # Wompi no envía `id` en el root del payload — usamos event_type:wompi_reference
        # como clave de idempotencia (mismo evento para la misma transacción).
        event_id = payload.get("id") or payload.get("event_id") or (
            f"{event_type}:{wompi_reference}" if wompi_reference else None
        )
        if not event_id:
            logger.error("Webhook sin event_id — rechazado")
            return {"status": "rejected", "reason": "missing_event_id"}
        seen = await self.webhook_repo.find_by_event_id(event_id)
        if seen:
            logger.info("Webhook duplicate ignored: event_id=%s", event_id)
            return {"status": "duplicate"}

        try:
            log = await self.webhook_repo.create(
                event_id=event_id,
                event_type=event_type,
                payload=payload,
                wompi_reference=wompi_reference,
            )
        except IntegrityError:
            await self.webhook_repo.session.rollback()
            logger.info("Webhook duplicate race (IntegrityError): event_id=%s", event_id)
            return {"status": "duplicate"}

        if event_type == "transaction.updated" and wompi_reference:
            txn = await self.transaction_repo.find_by_wompi_reference(wompi_reference)

            if not txn:
                # Hosted checkout: wompi_reference is NULL until this webhook fires.
                # The reference we passed to Wompi encodes the transaction_id as PB-{hex}.
                internal_reference = transaction.get("reference", "")
                # Format: PB-{32 hex chars}[-{attempt}]  — extract the 32-char UUID hex
                if internal_reference.startswith("PB-") and len(internal_reference) >= 35:
                    try:
                        txn_id = UUID(internal_reference[3:35])
                        txn = await self.transaction_repo.find_by_id(txn_id)
                    except ValueError:
                        pass

            if txn:
                current_status = txn.status

                if status == "APPROVED":
                    if current_status == "completed":
                        logger.info("Webhook APPROVED duplicate ignored: ref=%s already completed", wompi_reference)
                    else:
                        # Validación de monto y moneda contra DB (defensa en profundidad)
                        wompi_amount = transaction.get("amount_in_cents")
                        wompi_currency = transaction.get("currency", "COP")
                        expected_amount = int(txn.amount * 100)  # Decimal arithmetic — avoids float precision loss
                        if wompi_amount is not None and int(wompi_amount) != expected_amount:
                            logger.error(
                                "Webhook amount mismatch: ref=%s db=%s wompi=%s — REJECTING",
                                wompi_reference, expected_amount, wompi_amount,
                            )
                            await self.webhook_repo.mark_processed(log.id)
                            await self.webhook_repo.save()
                            return {"status": "rejected", "reason": "amount_mismatch"}
                        if wompi_currency != "COP":
                            logger.error(
                                "Webhook currency mismatch: ref=%s wompi=%s — REJECTING",
                                wompi_reference, wompi_currency,
                            )
                            await self.webhook_repo.mark_processed(log.id)
                            await self.webhook_repo.save()
                            return {"status": "rejected", "reason": "currency_mismatch"}

                        await self.transaction_repo.update_status(txn.id, "completed", wompi_reference=wompi_reference)
                        await self.transaction_repo.save()  # commit before calling order service — must not roll back on network failure
                        logger.info("Webhook approved: ref=%s txn=%s order=%s", wompi_reference, txn.id, txn.order_id)
                        try:
                            await _order_update_status(txn.order_id, "paid")
                        except Exception as exc:
                            logger.critical(
                                "RECONCILIATION NEEDED: transaction %s completed (order %s) but order status update failed: %s",
                                txn.id, txn.order_id, exc,
                            )

                elif status in ("DECLINED", "ERROR"):
                    if current_status == "completed":
                        logger.warning("Webhook %s ignored: ref=%s transaction already completed", status, wompi_reference)
                    else:
                        reason = transaction.get("status_message", "Payment declined")
                        await self.transaction_repo.update_status(txn.id, "failed", error_message=reason)
                        await self.transaction_repo.save()
                        logger.warning("Webhook %s: ref=%s reason=%s", status, wompi_reference, reason)

                elif status == "VOIDED":
                    if current_status == "refunded":
                        logger.info("Webhook VOIDED duplicate ignored: ref=%s already refunded", wompi_reference)
                    else:
                        await self.transaction_repo.update_status(txn.id, "refunded")
                        await self.transaction_repo.save()  # commit before calling order service
                        try:
                            await _order_update_status(txn.order_id, "cancelled")
                        except Exception as exc:
                            logger.critical(
                                "RECONCILIATION NEEDED: transaction %s refunded (order %s) but order cancel failed: %s",
                                txn.id, txn.order_id, exc,
                            )
                        logger.info("Webhook voided: ref=%s", wompi_reference)

        await self.webhook_repo.mark_processed(log.id)
        await self.webhook_repo.save()
        return {"status": "received"}

    async def save_payment_method(self, user_id: UUID, method_type: str, 
                                 reference: str, **kwargs) -> dict:
        method = await self.method_repo.create(
            user_id=user_id,
            method_type=method_type,
            reference=reference,
            **kwargs
        )
        await self.method_repo.save()
        
        return {
            "id": method.id,
            "method_type": method.method_type,
            "is_default": method.is_default,
        }
