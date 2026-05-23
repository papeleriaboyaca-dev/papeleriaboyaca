from sqlalchemy import Column, String, Integer, Boolean, DateTime, ForeignKey, Text, Numeric
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from datetime import datetime
import uuid
from .database import Base


class Category(Base):
    __tablename__ = "categories"
    __table_args__ = {"schema": "catalog_service"}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(100), nullable=False, index=True)
    slug = Column(String(100), unique=True, nullable=False)
    description = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)


class Product(Base):
    __tablename__ = "products"
    __table_args__ = {"schema": "catalog_service"}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    sku = Column(String(50), unique=True, nullable=False, index=True)
    name = Column(String(255), nullable=False, index=True)
    description = Column(Text, nullable=True)
    price = Column(Numeric(14, 2), nullable=False)
    cost_price = Column(Numeric(14, 2), nullable=True)
    stock = Column(Integer, default=0, nullable=False)
    category_id = Column(UUID(as_uuid=True), ForeignKey("catalog_service.categories.id"), nullable=False)
    weight = Column(Numeric(8, 3), nullable=True)
    dimensions = Column(String(100), nullable=True)
    sku_barcode = Column(String(100), nullable=True, unique=True)
    supplier_id = Column(String(100), nullable=True)
    image_url = Column(String(500), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)


class MarketingContent(Base):
    __tablename__ = "marketing_content"
    __table_args__ = {"schema": "catalog_service"}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title = Column(String(200), nullable=False)
    image_url = Column(Text, nullable=False, default="")
    image_path = Column(Text, nullable=False, default="")
    type = Column(String(20), nullable=False)  # "carousel" | "panel"
    display_order = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
