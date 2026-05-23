from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, Text, Numeric, Index, text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func
from datetime import datetime
import uuid
from .database import Base


class Transaction(Base):
    __tablename__ = "transactions"
    __table_args__ = (
        # UNIQUE PARTIAL INDEX: solo una transacción activa por orden.
        # "failed" y "refunded" pueden coexistir con un retry posterior.
        Index(
            "uq_transaction_active_order",
            "order_id",
            unique=True,
            postgresql_where=text("status IN ('pending', 'processing', 'completed')"),
            sqlite_where=text("status IN ('pending', 'processing', 'completed')"),
        ),
        {"schema": "payment_service"},
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    order_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    user_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    amount = Column(Numeric(14, 2), nullable=False)
    status = Column(String(20), default="pending", nullable=False, index=True)
    payment_method = Column(String(50), nullable=False)
    wompi_reference = Column(String(100), nullable=True, unique=True)
    wompi_transaction_id = Column(String(100), nullable=True)
    error_message = Column(Text, nullable=True)
    meta = Column(JSONB, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)


class PaymentMethod(Base):
    __tablename__ = "payment_methods"
    __table_args__ = {"schema": "payment_service"}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    method_type = Column(String(50), nullable=False)
    reference = Column(String(255), nullable=False)
    last_four_digits = Column(String(4), nullable=True)
    card_brand = Column(String(50), nullable=True)
    expiry_date = Column(String(10), nullable=True)
    is_default = Column(Boolean, default=False, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)


class WebhookLog(Base):
    __tablename__ = "webhooks_log"
    __table_args__ = (
        Index(
            "uq_webhook_event_id",
            "event_id",
            unique=True,
            postgresql_where=text("event_id IS NOT NULL"),
            sqlite_where=text("event_id IS NOT NULL"),
        ),
        {"schema": "payment_service"},
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    event_id = Column(String(100), nullable=True)
    event_type = Column(String(100), nullable=False)
    wompi_reference = Column(String(100), nullable=True)
    payload = Column(JSONB, nullable=False)
    processed = Column(Boolean, default=False, nullable=False)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
