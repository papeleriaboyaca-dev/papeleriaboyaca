from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func
from uuid import UUID
from .models import Transaction, PaymentMethod, WebhookLog
from datetime import datetime, timezone


class TransactionRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def find_by_id(self, transaction_id: UUID) -> Transaction | None:
        result = await self.session.execute(
            select(Transaction).where(Transaction.id == transaction_id)
        )
        return result.scalars().first()

    async def find_by_wompi_reference(self, wompi_reference: str) -> Transaction | None:
        result = await self.session.execute(
            select(Transaction).where(Transaction.wompi_reference == wompi_reference)
        )
        return result.scalars().first()

    async def find_by_order(self, order_id: UUID) -> Transaction | None:
        result = await self.session.execute(
            select(Transaction).where(Transaction.order_id == order_id)
        )
        return result.scalars().first()

    async def find_active_by_order(self, order_id: UUID) -> Transaction | None:
        """Returns the most recent active/completed transaction for an order.
        Deterministic: active states (pending/processing) first, then completed."""
        result = await self.session.execute(
            select(Transaction)
            .where(
                Transaction.order_id == order_id,
                Transaction.status.in_(["pending", "processing", "completed"]),
            )
            .order_by(Transaction.created_at.desc())
        )
        return result.scalars().first()

    async def count_failed_by_order(self, order_id: UUID) -> int:
        result = await self.session.execute(
            select(func.count(Transaction.id)).where(
                Transaction.order_id == order_id,
                Transaction.status == "failed",
            )
        )
        return result.scalar() or 0

    async def find_by_user(self, user_id: UUID, skip: int = 0,
                           limit: int = 20) -> list[Transaction]:
        result = await self.session.execute(
            select(Transaction)
            .where(Transaction.user_id == user_id)
            .order_by(Transaction.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        return result.scalars().all()

    async def find_all(self, skip: int = 0, limit: int = 100) -> list[Transaction]:
        result = await self.session.execute(
            select(Transaction)
            .order_by(Transaction.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        return result.scalars().all()

    async def create(self, order_id: UUID, user_id: UUID, amount: float, 
                    payment_method: str, **kwargs) -> Transaction:
        transaction = Transaction(
            order_id=order_id,
            user_id=user_id,
            amount=amount,
            payment_method=payment_method,
            **kwargs
        )
        self.session.add(transaction)
        await self.session.flush()
        return transaction

    async def update_status(self, transaction_id: UUID, status: str, 
                           wompi_reference: str | None = None, 
                           error_message: str | None = None) -> Transaction | None:
        transaction = await self.find_by_id(transaction_id)
        if not transaction:
            return None
        
        transaction.status = status
        transaction.updated_at = datetime.now(timezone.utc)
        if wompi_reference:
            transaction.wompi_reference = wompi_reference
        if error_message:
            transaction.error_message = error_message
        
        await self.session.flush()
        return transaction

    async def save(self) -> None:
        await self.session.commit()


class PaymentMethodRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def find_by_id(self, method_id: UUID) -> PaymentMethod | None:
        result = await self.session.execute(
            select(PaymentMethod).where(PaymentMethod.id == method_id)
        )
        return result.scalars().first()

    async def find_by_user(self, user_id: UUID) -> list[PaymentMethod]:
        result = await self.session.execute(
            select(PaymentMethod)
            .where((PaymentMethod.user_id == user_id) & (PaymentMethod.is_active == True))
            .order_by(PaymentMethod.created_at.desc())
        )
        return result.scalars().all()

    async def find_default_by_user(self, user_id: UUID) -> PaymentMethod | None:
        result = await self.session.execute(
            select(PaymentMethod).where(
                (PaymentMethod.user_id == user_id) & 
                (PaymentMethod.is_default == True) &
                (PaymentMethod.is_active == True)
            )
        )
        return result.scalars().first()

    async def create(self, user_id: UUID, method_type: str, reference: str, 
                    **kwargs) -> PaymentMethod:
        method = PaymentMethod(
            user_id=user_id,
            method_type=method_type,
            reference=reference,
            **kwargs
        )
        self.session.add(method)
        await self.session.flush()
        return method

    async def deactivate(self, method_id: UUID) -> bool:
        method = await self.find_by_id(method_id)
        if not method:
            return False
        method.is_active = False
        await self.session.flush()
        return True

    async def save(self) -> None:
        await self.session.commit()


class WebhookLogRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def find_by_event_id(self, event_id: str) -> WebhookLog | None:
        result = await self.session.execute(
            select(WebhookLog).where(WebhookLog.event_id == event_id)
        )
        return result.scalars().first()

    async def create(self, event_type: str, payload: dict,
                    wompi_reference: str | None = None,
                    event_id: str | None = None) -> WebhookLog:
        log = WebhookLog(
            event_id=event_id,
            event_type=event_type,
            payload=payload,
            wompi_reference=wompi_reference,
        )
        self.session.add(log)
        await self.session.flush()
        return log

    async def mark_processed(self, log_id: UUID) -> bool:
        log = await self.session.execute(
            select(WebhookLog).where(WebhookLog.id == log_id)
        )
        webhook = log.scalars().first()
        if not webhook:
            return False
        webhook.processed = True
        await self.session.flush()
        return True

    async def save(self) -> None:
        await self.session.commit()
