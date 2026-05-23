from uuid import UUID
from ..infrastructure.repositories import ProductRepository, CategoryRepository
from ..application.dtos import ProductResponse, ProductCreate, CategoryResponse


class ProductService:
    def __init__(self, product_repo: ProductRepository, category_repo: CategoryRepository):
        self.product_repo = product_repo
        self.category_repo = category_repo

    async def get_product_by_id(self, product_id: UUID) -> ProductResponse:
        product = await self.product_repo.find_by_id(product_id)
        if not product or not product.is_active:
            raise ValueError("Product not found")
        return ProductResponse.from_orm(product)

    async def get_product_by_sku(self, sku: str) -> ProductResponse:
        product = await self.product_repo.find_by_sku(sku)
        if not product:
            raise ValueError("Product not found")
        return ProductResponse.from_orm(product)

    async def list_by_category(self, category_id: UUID, skip: int = 0, 
                               limit: int = 20) -> list[ProductResponse]:
        products = await self.product_repo.list_by_category(
            category_id, skip, limit
        )
        return [ProductResponse.from_orm(p) for p in products]

    async def search_products(self, query: str, skip: int = 0, 
                             limit: int = 20) -> list[ProductResponse]:
        products = await self.product_repo.search(query, skip, limit)
        return [ProductResponse.from_orm(p) for p in products]

    async def list_all_products(self, skip: int = 0, limit: int = 20,
                               category_id=None, min_price=None, max_price=None,
                               sort_by=None, after_created_at=None,
                               after_id=None, active_only: bool = True) -> list[ProductResponse]:
        products = await self.product_repo.list_all(
            skip, limit, active_only=active_only, category_id=category_id,
            min_price=min_price, max_price=max_price, sort_by=sort_by,
            after_created_at=after_created_at, after_id=after_id,
        )
        return [ProductResponse.from_orm(p) for p in products]

    async def create_product(self, product_data: ProductCreate) -> ProductResponse:
        existing_product = await self.product_repo.find_by_sku(product_data.sku)
        if existing_product:
            raise ValueError("Product with this SKU already exists")
        
        category = await self.category_repo.find_by_id(product_data.category_id)
        if not category:
            raise ValueError("Category not found")
        
        product = await self.product_repo.create(
            sku=product_data.sku,
            name=product_data.name,
            price=product_data.price,
            category_id=product_data.category_id,
            description=product_data.description,
            cost_price=product_data.cost_price,
            stock=product_data.stock,
            image_url=product_data.image_url,
        )
        await self.product_repo.save()
        return ProductResponse.from_orm(product)

    async def update_product(self, product_id: UUID, 
                            update_data: dict) -> ProductResponse:
        product = await self.product_repo.update(product_id, **update_data)
        if not product:
            raise ValueError("Product not found")
        await self.product_repo.save()
        return ProductResponse.from_orm(product)

    async def deactivate_product(self, product_id: UUID) -> bool:
        result = await self.product_repo.deactivate(product_id)
        if result:
            await self.product_repo.save()
        return result

    async def check_stock(self, product_id: UUID, quantity: int) -> bool:
        product = await self.product_repo.find_by_id(product_id)
        if not product:
            raise ValueError("Product not found")
        return product.stock >= quantity

    async def reduce_stock(self, product_id: UUID, quantity: int) -> bool:
        ok = await self.product_repo.reduce_stock_atomic(product_id, quantity)
        if ok:
            await self.product_repo.save()
        return ok

    async def restore_stock(self, product_id: UUID, quantity: int) -> bool:
        result = await self.product_repo.restore_stock(product_id, quantity)
        if result:
            await self.product_repo.save()
        return result


class CategoryService:
    def __init__(self, category_repo: CategoryRepository):
        self.category_repo = category_repo

    async def get_category_by_id(self, category_id: UUID) -> CategoryResponse:
        category = await self.category_repo.find_by_id(category_id)
        if not category:
            raise ValueError("Category not found")
        return CategoryResponse.from_orm(category)

    async def list_all_categories(self) -> list[CategoryResponse]:
        categories = await self.category_repo.list_all()
        return [CategoryResponse.from_orm(c) for c in categories]

    async def create_category(self, name: str, slug: str,
                             description: str | None = None) -> CategoryResponse:
        existing = await self.category_repo.find_by_slug(slug)
        if existing:
            raise ValueError("Category with this slug already exists")

        category = await self.category_repo.create(
            name=name, slug=slug, description=description
        )
        await self.category_repo.save()
        return CategoryResponse.from_orm(category)

    async def update_category(self, category_id: UUID, name: str | None = None,
                             description: str | None = None) -> CategoryResponse:
        updates = {}
        if name is not None:
            updates["name"] = name
        if description is not None:
            updates["description"] = description
        category = await self.category_repo.update(category_id, **updates)
        if not category:
            raise ValueError("Category not found")
        await self.category_repo.save()
        return CategoryResponse.from_orm(category)

    async def delete_category(self, category_id: UUID) -> bool:
        result = await self.category_repo.delete(category_id)
        if result:
            await self.category_repo.save()
        return result
