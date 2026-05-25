from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError
from uuid import UUID
from typing import Optional
from pydantic import BaseModel
import base64, json as _json
from ..application.dtos import (
    ProductResponse, ProductCreate, ProductUpdate, CategoryResponse, CategoryBase, CategoryUpdate,
    MarketingContentCreate, MarketingContentUpdate, MarketingContentResponse,
)
from ..application.services import ProductService, CategoryService
from ..infrastructure.database import get_db
from ..infrastructure.repositories import ProductRepository, CategoryRepository, MarketingContentRepository


def _decode_cursor(cursor: str) -> tuple:
    try:
        data = _json.loads(base64.b64decode(cursor).decode())
        from datetime import datetime, timezone
        return datetime.fromisoformat(data["ts"]), UUID(data["id"])
    except Exception:
        return None, None


def _encode_cursor(product: ProductResponse) -> str:
    data = {"ts": product.created_at.isoformat(), "id": str(product.id)}
    return base64.b64encode(_json.dumps(data).encode()).decode()


router = APIRouter()


async def get_product_service(db: AsyncSession = Depends(get_db)) -> ProductService:
    product_repo = ProductRepository(db)
    category_repo = CategoryRepository(db)
    return ProductService(product_repo, category_repo)


async def get_category_service(db: AsyncSession = Depends(get_db)) -> CategoryService:
    category_repo = CategoryRepository(db)
    return CategoryService(category_repo)


@router.get("/categories", response_model=list[CategoryResponse])
async def list_categories(
    category_service: CategoryService = Depends(get_category_service),
):
    return await category_service.list_all_categories()


@router.get("/categories/{category_id}", response_model=CategoryResponse)
async def get_category(
    category_id: UUID,
    category_service: CategoryService = Depends(get_category_service),
):
    try:
        return await category_service.get_category_by_id(category_id)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )


@router.post("/categories", response_model=CategoryResponse, status_code=status.HTTP_201_CREATED)
async def create_category(
    body: CategoryBase,
    category_service: CategoryService = Depends(get_category_service),
):
    try:
        return await category_service.create_category(body.name, body.slug, body.description)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except IntegrityError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Ya existe una categoría con ese nombre",
        )


@router.put("/categories/{category_id}", response_model=CategoryResponse)
async def update_category(
    category_id: UUID,
    body: CategoryUpdate,
    category_service: CategoryService = Depends(get_category_service),
):
    try:
        return await category_service.update_category(
            category_id, name=body.name, description=body.description
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except IntegrityError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Ya existe una categoría con ese nombre",
        )


@router.delete("/categories/{category_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_category(
    category_id: UUID,
    category_service: CategoryService = Depends(get_category_service),
):
    try:
        deleted = await category_service.delete_category(category_id)
    except IntegrityError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="No se puede eliminar: la categoría tiene productos asociados",
        )
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Category not found")


@router.get("/products", response_model=list[ProductResponse])
async def list_products(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=200),
    category_id: Optional[UUID] = Query(None),
    min_price: Optional[float] = Query(None, ge=0),
    max_price: Optional[float] = Query(None, ge=0),
    sort_by: Optional[str] = Query(None, pattern="^(price_asc|price_desc|name)$"),
    after: Optional[str] = Query(None, description="Opaque cursor from X-Next-Cursor header"),
    active_only: bool = Query(True),
    product_service: ProductService = Depends(get_product_service),
):
    after_ts, after_id = _decode_cursor(after) if after else (None, None)
    products = await product_service.list_all_products(
        skip, limit, category_id=category_id,
        min_price=min_price, max_price=max_price, sort_by=sort_by,
        after_created_at=after_ts, after_id=after_id,
        active_only=active_only,
    )
    headers = {}
    if len(products) == limit:
        headers["X-Next-Cursor"] = _encode_cursor(products[-1])
    return JSONResponse(
        content=[p.model_dump(mode="json") for p in products],
        headers=headers,
    )


@router.get("/products/search", response_model=list[ProductResponse])
async def search_products(
    q: str = Query(..., min_length=1),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    product_service: ProductService = Depends(get_product_service),
):
    return await product_service.search_products(q, skip, limit)


@router.get("/products/{product_id}", response_model=ProductResponse)
async def get_product(
    product_id: UUID,
    product_service: ProductService = Depends(get_product_service),
):
    try:
        return await product_service.get_product_by_id(product_id)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )


@router.post("/products", response_model=ProductResponse, status_code=status.HTTP_201_CREATED)
async def create_product(
    product: ProductCreate,
    product_service: ProductService = Depends(get_product_service),
):
    try:
        return await product_service.create_product(product)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.put("/products/{product_id}", response_model=ProductResponse)
async def update_product(
    product_id: UUID,
    updates: ProductUpdate,
    product_service: ProductService = Depends(get_product_service),
):
    try:
        return await product_service.update_product(
            product_id, updates.model_dump(exclude_unset=True)
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND if "not found" in str(e).lower()
            else status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.delete("/products/{product_id}")
async def deactivate_product(
    product_id: UUID,
    product_service: ProductService = Depends(get_product_service),
):
    success = await product_service.deactivate_product(product_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found",
        )
    return {"message": "Product deactivated"}


@router.get("/products/{product_id}/stock")
async def check_product_stock(
    product_id: UUID,
    quantity: int = Query(..., ge=1),
    product_service: ProductService = Depends(get_product_service),
):
    try:
        available = await product_service.check_stock(product_id, quantity)
        return {"available": available, "quantity_requested": quantity}
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )


class StockDelta(BaseModel):
    quantity: int


@router.post("/products/{product_id}/reduce-stock")
async def reduce_stock(
    product_id: UUID,
    body: StockDelta,
    product_service: ProductService = Depends(get_product_service),
):
    try:
        ok = await product_service.reduce_stock(product_id, body.quantity)
        if not ok:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Insufficient stock")
        return {"ok": True}
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.post("/products/{product_id}/restore-stock")
async def restore_stock(
    product_id: UUID,
    body: StockDelta,
    product_service: ProductService = Depends(get_product_service),
):
    try:
        ok = await product_service.restore_stock(product_id, body.quantity)
        if not ok:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")
        return {"ok": True}
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


# ── Marketing Content ─────────────────────────────────────────────────────────

@router.get("/marketing/public")
async def get_public_marketing(db: AsyncSession = Depends(get_db)):
    repo = MarketingContentRepository(db)
    items = await repo.find_active()
    return {
        "carousel": [MarketingContentResponse.model_validate(i) for i in items if i.type == "carousel"],
        "panels": [MarketingContentResponse.model_validate(i) for i in items if i.type == "panel"],
    }


@router.get("/marketing", response_model=list[MarketingContentResponse])
async def list_marketing(db: AsyncSession = Depends(get_db)):
    repo = MarketingContentRepository(db)
    return await repo.find_all()


@router.post("/marketing", response_model=MarketingContentResponse, status_code=201)
async def create_marketing(body: MarketingContentCreate, db: AsyncSession = Depends(get_db)):
    repo = MarketingContentRepository(db)
    content = await repo.create(
        title=body.title, type=body.type,
        display_order=body.display_order, is_active=body.is_active,
    )
    await repo.save()
    return content


@router.put("/marketing/{content_id}", response_model=MarketingContentResponse)
async def update_marketing(
    content_id: UUID, body: MarketingContentUpdate, db: AsyncSession = Depends(get_db)
):
    repo = MarketingContentRepository(db)
    updates = {k: v for k, v in body.model_dump().items() if v is not None}
    # is_active can be False — pass it explicitly
    if body.is_active is not None:
        updates["is_active"] = body.is_active
    content = await repo.update(content_id, **updates)
    if not content:
        raise HTTPException(status_code=404, detail="Not found")
    await repo.save()
    return content


@router.delete("/marketing/{content_id}", status_code=204)
async def delete_marketing(content_id: UUID, db: AsyncSession = Depends(get_db)):
    repo = MarketingContentRepository(db)
    deleted = await repo.delete(content_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Not found")
    await repo.save()
