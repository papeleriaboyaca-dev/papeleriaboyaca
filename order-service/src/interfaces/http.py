from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID
from typing import Optional
from ..application.dtos import OrderResponse, OrderCreate, OrderUpdateStatus, ShippingAddressCreate, ShippingAddressResponse
from ..application.services import OrderService
from ..infrastructure.database import get_db
from ..infrastructure.repositories import (
    OrderRepository, OrderItemRepository, ShippingAddressRepository, OrderHistoryRepository
)


router = APIRouter(prefix="/orders", tags=["orders"])


async def get_order_service(db: AsyncSession = Depends(get_db)) -> OrderService:
    order_repo = OrderRepository(db)
    item_repo = OrderItemRepository(db)
    address_repo = ShippingAddressRepository(db)
    history_repo = OrderHistoryRepository(db)
    return OrderService(order_repo, item_repo, address_repo, history_repo)


# ── Fixed-path routes first (must come before /{order_id} to avoid capture) ───

@router.post("", response_model=OrderResponse, status_code=status.HTTP_201_CREATED)
async def create_order(
    order: OrderCreate,
    user_id: UUID,
    user_email: Optional[str] = Query(None),
    order_service: OrderService = Depends(get_order_service),
):
    try:
        return await order_service.create_order(user_id, order, user_email=user_email)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("", response_model=list[OrderResponse])
async def list_orders(
    user_id: Optional[UUID] = Query(None),
    is_admin: bool = Query(False),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=200),
    order_service: OrderService = Depends(get_order_service),
):
    if is_admin:
        return await order_service.list_all_orders(skip, limit)
    if user_id is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="user_id required")
    return await order_service.list_user_orders(user_id, skip, limit)


# ── Shipping Addresses (fixed prefix "/addresses" — must be before /{order_id}) ─

@router.post("/addresses", response_model=ShippingAddressResponse, status_code=status.HTTP_201_CREATED)
async def create_address(
    body: ShippingAddressCreate,
    user_id: UUID = Query(...),
    order_service: OrderService = Depends(get_order_service),
):
    return await order_service.create_shipping_address(user_id, body)


@router.get("/addresses", response_model=list[ShippingAddressResponse])
async def list_addresses(
    user_id: UUID = Query(...),
    order_service: OrderService = Depends(get_order_service),
):
    return await order_service.list_shipping_addresses(user_id)


@router.get("/addresses/{address_id}", response_model=ShippingAddressResponse)
async def get_address(
    address_id: UUID,
    user_id: UUID = Query(...),
    is_admin: bool = Query(False),
    order_service: OrderService = Depends(get_order_service),
):
    try:
        return await order_service.get_shipping_address(address_id, user_id, is_admin)
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.put("/addresses/{address_id}", response_model=ShippingAddressResponse)
async def update_address(
    address_id: UUID,
    body: ShippingAddressCreate,
    user_id: UUID = Query(...),
    is_admin: bool = Query(False),
    order_service: OrderService = Depends(get_order_service),
):
    try:
        return await order_service.update_shipping_address(address_id, user_id, body, is_admin)
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.delete("/addresses/{address_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_address(
    address_id: UUID,
    user_id: UUID = Query(...),
    is_admin: bool = Query(False),
    order_service: OrderService = Depends(get_order_service),
):
    try:
        await order_service.delete_shipping_address(address_id, user_id, is_admin)
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


# ── Parameterized order routes ─────────────────────────────────────────────────

@router.get("/{order_id}", response_model=OrderResponse)
async def get_order(
    order_id: UUID,
    user_id: UUID = Query(...),
    is_admin: bool = Query(False),
    order_service: OrderService = Depends(get_order_service),
):
    try:
        return await order_service.get_order(order_id, user_id, is_admin)
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.put("/{order_id}/status", response_model=OrderResponse)
async def update_order_status(
    order_id: UUID,
    status_update: OrderUpdateStatus,
    order_service: OrderService = Depends(get_order_service),
):
    try:
        return await order_service.update_order_status(
            order_id,
            status_update.status,
            tracking_number=status_update.tracking_number,
            shipping_carrier=status_update.shipping_carrier,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST
            if "Invalid status" in str(e)
            else status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )


@router.get("/{order_id}/items")
async def get_order_items(
    order_id: UUID,
    order_service: OrderService = Depends(get_order_service),
):
    try:
        await order_service.get_order(order_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    items = await order_service.get_order_items(order_id)
    return {"items": items}


@router.post("/{order_id}/cancel", response_model=OrderResponse)
async def cancel_order(
    order_id: UUID,
    user_id: UUID = Query(...),
    is_admin: bool = Query(False),
    order_service: OrderService = Depends(get_order_service),
):
    try:
        return await order_service.cancel_order(order_id, user_id, is_admin)
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except ValueError as e:
        code = status.HTTP_404_NOT_FOUND if "not found" in str(e).lower() else status.HTTP_400_BAD_REQUEST
        raise HTTPException(status_code=code, detail=str(e))
