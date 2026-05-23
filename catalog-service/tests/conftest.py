"""
Fixtures compartidas del catalog-service.
"""
import pytest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# Must be set before any src import so Settings() captures the value
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")

from uuid import uuid4
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import StaticPool
from httpx import AsyncClient, ASGITransport

from src.infrastructure.database import Base, get_db
from src.infrastructure.models import Category, Product
from src.infrastructure.repositories import CategoryRepository, ProductRepository
from src.application.dtos import ProductCreate


@pytest.fixture(scope="function")
async def db_engine():
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with engine.begin() as conn:
        await conn.run_sync(
            lambda c: [setattr(t, "schema", None) for t in Base.metadata.sorted_tables]
        )
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest.fixture(scope="function")
async def db_session(db_engine):
    factory = async_sessionmaker(
        db_engine, class_=AsyncSession, expire_on_commit=False, autoflush=False
    )
    async with factory() as session:
        yield session


@pytest.fixture(scope="function")
async def async_client(db_session):
    from src.main import app

    async def _override():
        yield db_session

    app.dependency_overrides[get_db] = _override
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c
    app.dependency_overrides.clear()


# ── Datos de prueba ────────────────────────────────────────────────────────────

@pytest.fixture
async def sample_category(db_session) -> Category:
    """Categoría base disponible en todos los tests."""
    cat = Category(name="Útiles Escolares", slug="utiles-escolares", description="Productos escolares")
    db_session.add(cat)
    await db_session.commit()
    return cat


@pytest.fixture
async def sample_product(db_session, sample_category) -> Product:
    """Producto base disponible en todos los tests."""
    product = Product(
        sku=f"SKU-{uuid4().hex[:6].upper()}",
        name="Lápiz HB 2B",
        price=500.0,
        stock=100,
        category_id=sample_category.id,
    )
    db_session.add(product)
    await db_session.commit()
    return product


@pytest.fixture
def product_payload(sample_category):
    """Payload JSON válido para crear un producto."""
    return {
        "sku": f"SKU-{uuid4().hex[:6].upper()}",
        "name": "Cuaderno Cuadriculado",
        "price": 3500.0,
        "stock": 50,
        "category_id": str(sample_category.id),
        "description": "100 hojas",
    }


@pytest.fixture
def category_payload():
    slug = uuid4().hex[:8]
    return {"name": "Papelería", "slug": slug, "description": "Artículos de papelería"}
