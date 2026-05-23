from pydantic import BaseModel, Field, field_validator
from uuid import UUID
from datetime import datetime
from typing import Optional, List


class OrderItemCreate(BaseModel):
    product_id: UUID
    # Tope conservador para papelería: previene DoS de inventario por compra masiva
    # con stock limitado (álbumes Mundial, productos populares).
    quantity: int = Field(ge=1, le=20)
    unit_price: Optional[float] = None  # ignored — price is fetched from catalog


class OrderCreate(BaseModel):
    shipping_address_id: Optional[UUID] = None
    items: List[OrderItemCreate] = Field(min_length=1, max_length=50)
    notes: Optional[str] = Field(None, max_length=500)


VALID_STATUSES = {
    "pending", "pending_payment", "paid", "confirmed",
    "processing", "shipped", "delivered", "cancelled", "expired",
}

class OrderUpdateStatus(BaseModel):
    status: str
    tracking_number: Optional[str] = Field(None, max_length=100)
    shipping_carrier: Optional[str] = Field(None, max_length=100)

    @field_validator("status")
    @classmethod
    def normalize_and_validate(cls, v: str) -> str:
        v = v.lower()
        if v not in VALID_STATUSES:
            raise ValueError(f"status must be one of {sorted(VALID_STATUSES)}")
        return v


class OrderResponse(BaseModel):
    id: UUID
    order_number: str
    user_id: UUID
    user_email: Optional[str] = None
    status: str
    subtotal: float
    tax_amount: float
    discount_percentage: float
    discount_amount: float
    total: float
    shipping_address_id: Optional[UUID] = None
    tracking_number: Optional[str] = None
    shipping_carrier: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class ShippingAddressCreate(BaseModel):
    address_line1: str = Field(min_length=5, max_length=200)
    address_line2: Optional[str] = Field(None, max_length=200)
    city: str = Field(min_length=2, max_length=100)
    postal_code: str = Field(min_length=3, max_length=20)


class ShippingAddressResponse(ShippingAddressCreate):
    id: UUID
    created_at: datetime

    class Config:
        from_attributes = True
