from pydantic import BaseModel, Field
from uuid import UUID
from datetime import datetime
from typing import Optional


class CategoryBase(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    slug: str = Field(min_length=1, max_length=100, pattern=r"^[a-z0-9-]+$")
    description: Optional[str] = Field(None, max_length=500)


class CategoryUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)


class CategoryResponse(CategoryBase):
    id: UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ProductCreate(BaseModel):
    sku: str = Field(min_length=1, max_length=50)
    name: str = Field(min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=2000)
    price: float = Field(gt=0, le=100_000_000)
    cost_price: Optional[float] = Field(None, ge=0, le=100_000_000)
    stock: int = Field(default=0, ge=0, le=999_999)
    category_id: UUID
    image_url: Optional[str] = Field(None, max_length=500)


class ProductUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    price: Optional[float] = Field(None, gt=0, le=100_000_000)
    stock: Optional[int] = Field(None, ge=0, le=999_999)
    is_active: Optional[bool] = None
    description: Optional[str] = Field(None, max_length=2000)
    image_url: Optional[str] = Field(None, max_length=500)
    category_id: Optional[UUID] = None


class ProductResponse(BaseModel):
    id: UUID
    sku: str
    name: str
    description: Optional[str] = None
    price: float
    stock: int
    is_active: bool
    category_id: UUID
    image_url: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class MarketingContentCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    type: str = Field(pattern=r"^(carousel|panel)$")
    display_order: int = Field(default=0, ge=0)
    is_active: bool = True


class MarketingContentUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=200)
    type: Optional[str] = Field(None, pattern=r"^(carousel|panel)$")
    display_order: Optional[int] = Field(None, ge=0)
    is_active: Optional[bool] = None
    image_url: Optional[str] = None
    image_path: Optional[str] = None


class MarketingContentResponse(BaseModel):
    id: UUID
    title: str
    image_url: str
    image_path: str
    type: str
    display_order: int
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
