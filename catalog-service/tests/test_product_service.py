import pytest
from uuid import uuid4
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import StaticPool

from src.infrastructure.database import Base
from src.infrastructure.models import Category, Product
from src.infrastructure.repositories import ProductRepository, CategoryRepository
from src.application.services import ProductService, CategoryService
from src.application.dtos import ProductCreate


@pytest.fixture
async def db_session():
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    async with engine.begin() as conn:
        await conn.run_sync(lambda c: [setattr(t, "schema", None) for t in Base.metadata.sorted_tables])
        await conn.run_sync(Base.metadata.create_all)

    async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        category = Category(name="Test Category", slug="test-category", description="Test")
        session.add(category)
        await session.commit()
        yield session

    await engine.dispose()


@pytest.fixture
async def product_service(db_session):
    return ProductService(ProductRepository(db_session), CategoryRepository(db_session))


@pytest.fixture
async def category_service(db_session):
    return CategoryService(CategoryRepository(db_session))


async def _get_category_id(db_session):
    cats = await CategoryRepository(db_session).list_all()
    return cats[0].id


# ── Productos ─────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_create_product(db_session, product_service):
    category_id = await _get_category_id(db_session)
    product = await product_service.create_product(
        ProductCreate(sku="SKU-001", name="Lápiz HB", price=500.0, category_id=category_id, stock=100)
    )
    assert product.sku == "SKU-001"
    assert product.stock == 100
    assert product.price == 500.0


@pytest.mark.asyncio
async def test_create_product_duplicate_sku(db_session, product_service):
    category_id = await _get_category_id(db_session)
    data = ProductCreate(sku="SKU-DUP", name="Cuaderno", price=2000.0, category_id=category_id, stock=10)
    await product_service.create_product(data)
    with pytest.raises(ValueError, match="already exists"):
        await product_service.create_product(data)


@pytest.mark.asyncio
async def test_create_product_invalid_category(db_session, product_service):
    with pytest.raises(ValueError, match="Category not found"):
        await product_service.create_product(
            ProductCreate(sku="SKU-X", name="X", price=100.0, category_id=uuid4(), stock=1)
        )


@pytest.mark.asyncio
async def test_get_product_by_id(db_session, product_service):
    category_id = await _get_category_id(db_session)
    created = await product_service.create_product(
        ProductCreate(sku="SKU-GET", name="Borrador", price=300.0, category_id=category_id, stock=5)
    )
    retrieved = await product_service.get_product_by_id(created.id)
    assert retrieved.id == created.id


@pytest.mark.asyncio
async def test_get_product_not_found(product_service):
    with pytest.raises(ValueError, match="Product not found"):
        await product_service.get_product_by_id(uuid4())


@pytest.mark.asyncio
async def test_search_products(db_session, product_service):
    category_id = await _get_category_id(db_session)
    await product_service.create_product(
        ProductCreate(sku="SRCH-001", name="Marcador Azul", price=1500.0, category_id=category_id, stock=20)
    )
    results = await product_service.search_products("Marcador")
    assert len(results) > 0
    assert results[0].name == "Marcador Azul"


@pytest.mark.asyncio
async def test_search_products_no_results(product_service):
    results = await product_service.search_products("xyznotexist")
    assert results == []


@pytest.mark.asyncio
async def test_check_stock_available(db_session, product_service):
    category_id = await _get_category_id(db_session)
    p = await product_service.create_product(
        ProductCreate(sku="STK-001", name="Papel", price=100.0, category_id=category_id, stock=50)
    )
    assert await product_service.check_stock(p.id, 30) is True
    assert await product_service.check_stock(p.id, 60) is False


@pytest.mark.asyncio
async def test_check_stock_product_not_found(product_service):
    with pytest.raises(ValueError, match="Product not found"):
        await product_service.check_stock(uuid4(), 1)


@pytest.mark.asyncio
async def test_deactivate_product(db_session, product_service):
    category_id = await _get_category_id(db_session)
    p = await product_service.create_product(
        ProductCreate(sku="DEL-001", name="Goma", price=200.0, category_id=category_id, stock=10)
    )
    result = await product_service.deactivate_product(p.id)
    assert result is True


@pytest.mark.asyncio
async def test_deactivate_product_not_found(product_service):
    result = await product_service.deactivate_product(uuid4())
    assert result is False


@pytest.mark.asyncio
async def test_update_product(db_session, product_service):
    category_id = await _get_category_id(db_session)
    p = await product_service.create_product(
        ProductCreate(sku="UPD-001", name="Tijeras", price=1000.0, category_id=category_id, stock=15)
    )
    updated = await product_service.update_product(p.id, {"price": 1200.0, "stock": 20})
    assert updated.price == 1200.0
    assert updated.stock == 20


@pytest.mark.asyncio
async def test_update_product_not_found(product_service):
    with pytest.raises(ValueError, match="Product not found"):
        await product_service.update_product(uuid4(), {"price": 999.0})


# ── Categorías ────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_create_category(category_service):
    cat = await category_service.create_category("Útiles", "utiles", "Útiles escolares")
    assert cat.name == "Útiles"
    assert cat.slug == "utiles"


@pytest.mark.asyncio
async def test_create_category_duplicate_slug(category_service):
    await category_service.create_category("Cat A", "dup-slug")
    with pytest.raises(ValueError, match="already exists"):
        await category_service.create_category("Cat B", "dup-slug")


@pytest.mark.asyncio
async def test_list_categories(category_service):
    cats = await category_service.list_all_categories()
    assert len(cats) >= 1


@pytest.mark.asyncio
async def test_get_category_not_found(category_service):
    with pytest.raises(ValueError, match="Category not found"):
        await category_service.get_category_by_id(uuid4())
