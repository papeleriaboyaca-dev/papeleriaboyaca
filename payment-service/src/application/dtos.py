from pydantic import BaseModel, field_validator
from uuid import UUID
from datetime import datetime
from typing import Optional, Literal


VALID_PAYMENT_METHODS = Literal["card", "nequi", "bancolombia_transfer", "pse", "cash", "wompi"]

class TransactionCreate(BaseModel):
    order_id: UUID
    amount: float
    payment_method: VALID_PAYMENT_METHODS

    @field_validator("amount")
    @classmethod
    def amount_must_be_positive(cls, v: float) -> float:
        if v <= 0:
            raise ValueError("amount must be greater than 0")
        return v


class TransactionResponse(BaseModel):
    id: UUID
    order_id: UUID
    user_id: UUID
    status: str
    amount: float
    payment_method: str
    created_at: datetime
    wompi_reference: Optional[str] = None

    class Config:
        from_attributes = True


class PaymentMethodCreate(BaseModel):
    method_type: str
    reference: str
    last_four_digits: Optional[str] = None
    card_brand: Optional[str] = None


class PaymentMethodResponse(PaymentMethodCreate):
    id: UUID
    is_default: bool
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class WebhookPayload(BaseModel):
    event_type: str
    data: dict


class WompiCheckoutRequest(BaseModel):
    transaction_id: UUID
    customer_email: str
