from fastapi import APIRouter, Depends, HTTPException, status, Header, Request, Query
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID
from typing import Optional
from ..application.dtos import TransactionResponse, TransactionCreate, WompiCheckoutRequest
from ..application.services import PaymentService
from ..infrastructure.database import get_db
from ..infrastructure.repositories import (
    TransactionRepository, PaymentMethodRepository, WebhookLogRepository
)


router = APIRouter(prefix="/payments", tags=["payments"])


async def get_payment_service(db: AsyncSession = Depends(get_db)) -> PaymentService:
    transaction_repo = TransactionRepository(db)
    method_repo = PaymentMethodRepository(db)
    webhook_repo = WebhookLogRepository(db)
    return PaymentService(transaction_repo, method_repo, webhook_repo)


@router.post("/transactions", response_model=TransactionResponse, status_code=status.HTTP_201_CREATED)
async def create_transaction(
    body: TransactionCreate,
    user_id: UUID,
    payment_service: PaymentService = Depends(get_payment_service),
):
    try:
        return await payment_service.create_transaction(
            body.order_id, user_id, body.amount, body.payment_method
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.get("/transactions", response_model=list[TransactionResponse])
async def list_transactions(
    user_id: Optional[UUID] = None,
    is_admin: bool = Query(False),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=200),
    payment_service: PaymentService = Depends(get_payment_service),
):
    if is_admin:
        return await payment_service.list_all_transactions(skip, limit)
    if user_id is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="user_id required")
    return await payment_service.list_user_transactions(user_id, skip, limit)


@router.get("/transactions/{transaction_id}", response_model=TransactionResponse)
async def get_transaction(
    transaction_id: UUID,
    user_id: UUID = Query(None),
    is_admin: bool = Query(False),
    payment_service: PaymentService = Depends(get_payment_service),
):
    try:
        return await payment_service.get_transaction(transaction_id, user_id, is_admin)
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )


@router.post("/wompi/checkout")
async def create_wompi_checkout(
    body: WompiCheckoutRequest,
    user_id: UUID = Query(...),
    payment_service: PaymentService = Depends(get_payment_service),
):
    try:
        return await payment_service.get_checkout_url(
            transaction_id=body.transaction_id,
            customer_email=body.customer_email,
            requesting_user_id=user_id,
        )
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/webhooks/wompi")
async def wompi_webhook(
    request: Request,
    x_event_checksum: str = Header(None),
    payment_service: PaymentService = Depends(get_payment_service),
):
    if not x_event_checksum:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing X-Event-Checksum header",
        )

    raw_body = await request.body()
    try:
        import json
        request_body = json.loads(raw_body)
        result = await payment_service.handle_wompi_webhook(request_body, x_event_checksum)
        return result
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
        )
