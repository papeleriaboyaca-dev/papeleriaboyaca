from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func, asc, desc, tuple_, update
from uuid import UUID
from typing import Optional
from datetime import datetime
from .models import Product, Category, MarketingContent


class ProductRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def find_by_id(self, product_id: UUID) -> Product | None:
        result = await self.session.execute(
            select(Product).where(Product.id == product_id)
        )
        return result.scalars().first()

    async def find_by_sku(self, sku: str) -> Product | None:
        result = await self.session.execute(
            select(Product).where(Product.sku == sku)
        )
        return result.scalars().first()

    async def list_by_category(self, category_id: UUID, skip: int = 0, 
                              limit: int = 20, active_only: bool = True) -> list[Product]:
        query = select(Product).where(Product.category_id == category_id)
        if active_only:
            query = query.where(Product.is_active == True)
        result = await self.session.execute(
            query.offset(skip).limit(limit)
        )
        return result.scalars().all()

    async def search(self, search_term: str, skip: int = 0, 
                    limit: int = 20) -> list[Product]:
        result = await self.session.execute(
            select(Product)
            .where(
                (Product.name.ilike(f"%{search_term}%")) |
                (Product.description.ilike(f"%{search_term}%")) |
                (Product.sku.ilike(f"%{search_term}%"))
            )
            .where(Product.is_active == True)
            .offset(skip)
            .limit(limit)
        )
        return result.scalars().all()

    async def create(self, sku: str, name: str, price: float, 
                    category_id: UUID, **kwargs) -> Product:
        product = Product(
            sku=sku,
            name=name,
            price=price,
            category_id=category_id,
            **kwargs
        )
        self.session.add(product)
        await self.session.flush()
        return product

    async def update(self, product_id: UUID, **kwargs) -> Product | None:
        product = await self.find_by_id(product_id)
        if not product:
            return None
        for key, value in kwargs.items():
            if hasattr(product, key):
                setattr(product, key, value)
        await self.session.flush()
        await self.session.refresh(product)
        return product

    async def deactivate(self, product_id: UUID) -> bool:
        product = await self.find_by_id(product_id)
        if not product:
            return False
        product.is_active = False
        await self.session.flush()
        return True

    async def list_all(self, skip: int = 0, limit: int = 20,
                      active_only: bool = True,
                      category_id: Optional[UUID] = None,
                      min_price: Optional[float] = None,
                      max_price: Optional[float] = None,
                      sort_by: Optional[str] = None,
                      after_created_at: Optional[datetime] = None,
                      after_id: Optional[UUID] = None) -> list[Product]:
        query = select(Product)
        if active_only:
            query = query.where(Product.is_active == True)
        if category_id:
            query = query.where(Product.category_id == category_id)
        if min_price is not None:
            query = query.where(Product.price >= min_price)
        if max_price is not None:
            query = query.where(Product.price <= max_price)
        if sort_by == "price_asc":
            query = query.order_by(asc(Product.price))
        elif sort_by == "price_desc":
            query = query.order_by(desc(Product.price))
        elif sort_by == "name":
            query = query.order_by(asc(Product.name))
        else:
            query = query.order_by(desc(Product.created_at), desc(Product.id))

        if after_created_at is not None and after_id is not None and not sort_by:
            query = query.where(
                tuple_(Product.created_at, Product.id) < (after_created_at, after_id)
            )
            result = await self.session.execute(query.limit(limit))
        else:
            result = await self.session.execute(query.offset(skip).limit(limit))
        return result.scalars().all()

    async def reduce_stock_atomic(self, product_id: UUID, quantity: int) -> bool:
        """Single atomic UPDATE — eliminates the read-modify-write race condition."""
        result = await self.session.execute(
            update(Product)
            .where(Product.id == product_id, Product.stock >= quantity, Product.is_active == True)
            .values(stock=Product.stock - quantity)
        )
        await self.session.flush()
        return result.rowcount == 1

    async def restore_stock(self, product_id: UUID, quantity: int) -> bool:
        result = await self.session.execute(
            update(Product)
            .where(Product.id == product_id)
            .values(stock=Product.stock + quantity)
        )
        await self.session.flush()
        return result.rowcount == 1

    async def save(self) -> None:
        await self.session.commit()


class CategoryRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def find_by_id(self, category_id: UUID) -> Category | None:
        result = await self.session.execute(
            select(Category).where(Category.id == category_id)
        )
        return result.scalars().first()

    async def find_by_slug(self, slug: str) -> Category | None:
        result = await self.session.execute(
            select(Category).where(Category.slug == slug)
        )
        return result.scalars().first()

    async def list_all(self, active_only: bool = True) -> list[Category]:
        query = select(Category)
        if active_only:
            query = query.where(Category.is_active == True)
        result = await self.session.execute(query)
        return result.scalars().all()

    async def create(self, name: str, slug: str, **kwargs) -> Category:
        category = Category(name=name, slug=slug, **kwargs)
        self.session.add(category)
        await self.session.flush()
        return category

    async def update(self, category_id: UUID, **kwargs) -> Category | None:
        category = await self.find_by_id(category_id)
        if not category:
            return None
        for key, value in kwargs.items():
            setattr(category, key, value)
        await self.session.flush()
        await self.session.refresh(category)
        return category

    async def delete(self, category_id: UUID) -> bool:
        category = await self.find_by_id(category_id)
        if not category:
            return False
        await self.session.delete(category)
        await self.session.flush()
        return True

    async def save(self) -> None:
        await self.session.commit()


class MarketingContentRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def find_all(self) -> list[MarketingContent]:
        result = await self.session.execute(
            select(MarketingContent).order_by(MarketingContent.display_order, MarketingContent.created_at)
        )
        return result.scalars().all()

    async def find_active(self) -> list[MarketingContent]:
        result = await self.session.execute(
            select(MarketingContent)
            .where(MarketingContent.is_active == True)
            .order_by(MarketingContent.display_order, MarketingContent.created_at)
        )
        return result.scalars().all()

    async def find_by_id(self, id: UUID) -> MarketingContent | None:
        result = await self.session.execute(
            select(MarketingContent).where(MarketingContent.id == id)
        )
        return result.scalar_one_or_none()

    async def create(self, title: str, type: str, display_order: int = 0,
                     is_active: bool = True) -> MarketingContent:
        content = MarketingContent(
            title=title, type=type, display_order=display_order, is_active=is_active,
        )
        self.session.add(content)
        await self.session.flush()
        return content

    async def update(self, id: UUID, **kwargs) -> MarketingContent | None:
        content = await self.find_by_id(id)
        if not content:
            return None
        for k, v in kwargs.items():
            setattr(content, k, v)
        await self.session.flush()
        await self.session.refresh(content)
        return content

    async def delete(self, id: UUID) -> MarketingContent | None:
        content = await self.find_by_id(id)
        if not content:
            return None
        await self.session.delete(content)
        await self.session.flush()
        return content

    async def save(self) -> None:
        await self.session.commit()
