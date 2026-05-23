import uuid
import logging
import httpx
from datetime import datetime, timezone, timedelta
from uuid import UUID
from sqlalchemy import select
from ..config import settings
from ..infrastructure.repositories import (
    OrderRepository, OrderItemRepository, ShippingAddressRepository, OrderHistoryRepository
)
from ..infrastructure.models import Order, OrderItem
from ..application.dtos import OrderResponse, OrderCreate, ShippingAddressCreate, ShippingAddressResponse

logger = logging.getLogger(__name__)


def _internal_headers() -> dict:
    return {"X-Internal-Auth": settings.INTERNAL_API_SECRET} if settings.INTERNAL_API_SECRET else {}


async def _catalog_reduce_stock(product_id: UUID, quantity: int) -> bool:
    try:
        async with httpx.AsyncClient(timeout=10, headers=_internal_headers()) as client:
            r = await client.post(
                f"{settings.CATALOG_SERVICE_URL}/products/{product_id}/reduce-stock",
                json={"quantity": quantity},
            )
            return r.status_code == 200
    except Exception as e:
        logger.error("Stock reduction failed for %s: %s", product_id, e)
        return False


async def _catalog_get_product(product_id: UUID) -> dict | None:
    try:
        async with httpx.AsyncClient(timeout=10, headers=_internal_headers()) as client:
            r = await client.get(f"{settings.CATALOG_SERVICE_URL}/products/{product_id}")
            if r.status_code == 200:
                data = r.json()
                return {"price": float(data["price"]), "name": data.get("name")}
    except Exception as e:
        logger.error("Product fetch failed for %s: %s", product_id, e)
    return None


async def _catalog_restore_stock(product_id: UUID, quantity: int) -> None:
    try:
        async with httpx.AsyncClient(timeout=10, headers=_internal_headers()) as client:
            await client.post(
                f"{settings.CATALOG_SERVICE_URL}/products/{product_id}/restore-stock",
                json={"quantity": quantity},
            )
    except Exception as e:
        logger.error("Stock restore failed for %s: %s", product_id, e)


class OrderService:
    def __init__(self, order_repo: OrderRepository,
                 item_repo: OrderItemRepository,
                 address_repo: ShippingAddressRepository,
                 history_repo: OrderHistoryRepository):
        self.order_repo = order_repo
        self.item_repo = item_repo
        self.address_repo = address_repo
        self.history_repo = history_repo

    async def create_order(self, user_id: UUID, order_data: OrderCreate,
                          user_email: str | None = None) -> OrderResponse:
        if not order_data.items:
            raise ValueError("Order must have at least one item")

        for item_data in order_data.items:
            if item_data.quantity <= 0:
                raise ValueError(f"Quantity must be positive for product {item_data.product_id}")

        # Previene IDOR: la dirección debe pertenecer al usuario que crea la orden.
        if order_data.shipping_address_id is not None:
            address = await self.address_repo.find_by_id(order_data.shipping_address_id)
            if not address or address.user_id != user_id:
                raise ValueError("Invalid shipping address for this user")

        # Fetch canonical prices and names from catalog — ignore client-supplied unit_price
        catalog_data: dict[UUID, dict] = {}
        for item_data in order_data.items:
            product = await _catalog_get_product(item_data.product_id)
            if product is None:
                raise ValueError(f"Product {item_data.product_id} not found or unavailable")
            catalog_data[item_data.product_id] = product

        # Reserve stock upfront — prevents overselling
        reserved: list[tuple[UUID, int]] = []
        for item_data in order_data.items:
            ok = await _catalog_reduce_stock(item_data.product_id, item_data.quantity)
            if not ok:
                for prod_id, qty in reserved:
                    await _catalog_restore_stock(prod_id, qty)
                raise ValueError(f"Insufficient stock for product {item_data.product_id}")
            reserved.append((item_data.product_id, item_data.quantity))

        order_number = f"ORD-{uuid.uuid4().hex[:8].upper()}"
        # Transacción DB explícita: si falla algo intermedio, rollback completo.
        try:
            order = await self.order_repo.create(
                order_number=order_number,
                user_id=user_id,
                user_email=user_email,
                total=0.0,
                subtotal=0.0,
                status="pending_payment",
                shipping_address_id=order_data.shipping_address_id,
                notes=order_data.notes,
            )

            subtotal = 0.0
            for item_data in order_data.items:
                prod = catalog_data[item_data.product_id]
                item = await self.item_repo.create(
                    order_id=order.id,
                    product_id=item_data.product_id,
                    product_name=prod.get("name"),
                    quantity=item_data.quantity,
                    unit_price=prod["price"],
                )
                subtotal += float(item.subtotal)

            order.subtotal = subtotal
            order.total = subtotal
            await self.history_repo.create(order_id=order.id, new_status="pending_payment", notes="Pedido creado")
            await self.order_repo.save()
        except Exception:
            try:
                await self.order_repo.session.rollback()
            except Exception:
                pass
            for prod_id, qty in reserved:
                await _catalog_restore_stock(prod_id, qty)
            raise

        logger.info("Order created: %s user=%s total=%.2f", order.order_number, user_id, order.total)
        return OrderResponse.from_orm(order)

    async def add_item_to_order(self, order_id: UUID, product_id: UUID, 
                               quantity: int, unit_price: float) -> dict:
        order = await self.order_repo.find_by_id(order_id)
        if not order:
            raise ValueError("Order not found")
        
        item = await self.item_repo.create(
            order_id=order_id,
            product_id=product_id,
            quantity=quantity,
            unit_price=unit_price,
        )
        
        order.total = float(order.total or 0) + float(item.subtotal)
        await self.item_repo.save()
        
        return {
            "item_id": item.id,
            "subtotal": item.subtotal,
            "order_total": order.total
        }

    async def get_order(self, order_id: UUID, requesting_user_id: UUID | None = None,
                        is_admin: bool = False) -> OrderResponse:
        order = await self.order_repo.find_by_id(order_id)
        if not order:
            raise ValueError("Order not found")
        if requesting_user_id and not is_admin and order.user_id != requesting_user_id:
            raise PermissionError("Not authorized to view this order")
        return OrderResponse.from_orm(order)

    async def list_user_orders(self, user_id: UUID, skip: int = 0,
                              limit: int = 20) -> list[OrderResponse]:
        orders = await self.order_repo.find_by_user(user_id, skip, limit)
        return [OrderResponse.from_orm(o) for o in orders]

    async def list_all_orders(self, skip: int = 0, limit: int = 100) -> list[OrderResponse]:
        orders = await self.order_repo.find_all(skip, limit)
        return [OrderResponse.from_orm(o) for o in orders]

    async def update_order_status(self, order_id: UUID, new_status: str,
                                  tracking_number: str | None = None,
                                  shipping_carrier: str | None = None) -> OrderResponse:
        from ..application.dtos import VALID_STATUSES
        new_status = new_status.lower()
        if new_status not in VALID_STATUSES:
            raise ValueError(f"Invalid status. Must be one of {sorted(VALID_STATUSES)}")

        order = await self.order_repo.find_by_id(order_id)
        if not order:
            raise ValueError("Order not found")

        # Bloquea resurrección desde estados terminales: si una orden fue expirada
        # por el cleanup job, su stock ya se restauró (y posiblemente vendido a otro).
        # Marcarla "paid" causaría doble venta. Webhook de Wompi llegando tarde
        # debe escalar a reconciliación manual + refund.
        _TERMINAL = {"expired", "cancelled", "delivered"}
        if order.status in _TERMINAL and new_status == "paid":
            logger.critical(
                "LATE PAYMENT ON TERMINAL ORDER: order=%s status=%s — manual refund required in Wompi",
                order_id, order.status,
            )
            raise ValueError(
                f"Order is {order.status}; cannot mark paid. Manual refund required."
            )

        old_status = order.status

        order = await self.order_repo.update_status(order_id, new_status,
                                                    tracking_number=tracking_number,
                                                    shipping_carrier=shipping_carrier)
        await self.history_repo.create(order_id=order_id, old_status=old_status, new_status=new_status)
        await self.order_repo.save()
        logger.info("Order status updated: %s -> %s", order_id, new_status)

        # Stock was already reserved at order creation; no action needed on confirm

        return OrderResponse.from_orm(order)

    async def cancel_order(self, order_id: UUID, requesting_user_id: UUID,
                           is_admin: bool = False) -> OrderResponse:
        order = await self.order_repo.find_by_id(order_id)
        if not order:
            raise ValueError("Order not found")

        if not is_admin and order.user_id != requesting_user_id:
            raise PermissionError("Not authorized to cancel this order")

        # Admin SOLO puede cancelar órdenes no pagadas vía este endpoint.
        # Para órdenes ya pagadas (paid/confirmed) debe procesar el refund en
        # Wompi primero — el webhook VOIDED disparará la cancelación automática.
        # Si se permitiera cancelar paid acá, se restauraría stock pero el cliente
        # seguiría cobrado.
        cancellable = {"pending", "pending_payment"}
        if order.status not in cancellable:
            if is_admin and order.status in ("paid", "confirmed"):
                raise ValueError(
                    f"Order is '{order.status}' (cliente cobrado). "
                    "Procesa el refund en Wompi Dashboard primero; "
                    "el webhook VOIDED cancelará la orden automáticamente."
                )
            raise ValueError(f"Cannot cancel order in status '{order.status}'")

        old_status = order.status
        # Atomic update: si el cleanup job expiró la orden justo antes, rowcount=0 y no restauramos stock.
        cancelled = await self.order_repo.cancel_if_cancellable(order_id, cancellable)
        if not cancelled:
            raise ValueError("Order can no longer be cancelled (status changed concurrently)")

        await self.history_repo.create(
            order_id=order_id, old_status=old_status, new_status="cancelled",
            changed_by=requesting_user_id,
        )
        await self.order_repo.save()

        items = await self.item_repo.find_by_order(order_id)
        for item in items:
            await _catalog_restore_stock(item.product_id, item.quantity)

        order = await self.order_repo.find_by_id(order_id)
        logger.info("Order cancelled: %s by user=%s admin=%s", order_id, requesting_user_id, is_admin)
        return OrderResponse.from_orm(order)

    async def get_order_items(self, order_id: UUID) -> list[dict]:
        items = await self.item_repo.find_by_order(order_id)
        return [
            {
                "id": item.id,
                "product_id": item.product_id,
                "product_name": item.product_name,
                "quantity": item.quantity,
                "unit_price": item.unit_price,
                "subtotal": item.subtotal,
            }
            for item in items
        ]

    async def create_shipping_address(self, user_id: UUID,
                                     data: ShippingAddressCreate) -> ShippingAddressResponse:
        address = await self.address_repo.create(
            user_id=user_id,
            address_line1=data.address_line1,
            address_line2=data.address_line2,
            city=data.city,
            postal_code=data.postal_code,
        )
        await self.address_repo.save()
        return ShippingAddressResponse.from_orm(address)

    async def list_shipping_addresses(self, user_id: UUID) -> list[ShippingAddressResponse]:
        addresses = await self.address_repo.find_by_user(user_id)
        return [ShippingAddressResponse.from_orm(a) for a in addresses]

    async def get_shipping_address(self, address_id: UUID, user_id: UUID,
                                   is_admin: bool = False) -> ShippingAddressResponse:
        address = await self.address_repo.find_by_id(address_id)
        if not address:
            raise ValueError("Address not found")
        if not is_admin and address.user_id != user_id:
            raise PermissionError("Not authorized")
        return ShippingAddressResponse.from_orm(address)

    async def update_shipping_address(self, address_id: UUID, user_id: UUID,
                                      data: ShippingAddressCreate,
                                      is_admin: bool = False) -> ShippingAddressResponse:
        address = await self.address_repo.find_by_id(address_id)
        if not address:
            raise ValueError("Address not found")
        if not is_admin and address.user_id != user_id:
            raise PermissionError("Not authorized")
        updated = await self.address_repo.update(
            address_id,
            address_line1=data.address_line1,
            address_line2=data.address_line2,
            city=data.city,
            postal_code=data.postal_code,
        )
        await self.address_repo.save()
        return ShippingAddressResponse.from_orm(updated)

    async def delete_shipping_address(self, address_id: UUID, user_id: UUID,
                                      is_admin: bool = False) -> None:
        address = await self.address_repo.find_by_id(address_id)
        if not address:
            raise ValueError("Address not found")
        if not is_admin and address.user_id != user_id:
            raise PermissionError("Not authorized")
        await self.address_repo.delete(address_id)
        await self.address_repo.save()

    async def cleanup_expired_orders(self, timeout_minutes: int = 30) -> int:
        """
        Marca como `expired` las órdenes en pending_payment/pending creadas hace > N min
        y restaura el stock reservado. Pensado para correr en background cada ~5 min.
        Retorna el número de órdenes expiradas.
        """
        cutoff = datetime.now(timezone.utc) - timedelta(minutes=timeout_minutes)
        result = await self.order_repo.session.execute(
            select(Order).where(
                Order.status.in_(("pending", "pending_payment")),
                Order.created_at < cutoff,
            )
        )
        candidates = result.scalars().all()
        if not candidates:
            return 0

        expired_count = 0
        for order in candidates:
            try:
                items = await self.item_repo.find_by_order(order.id)
                old_status = order.status
                # Atomic update: si cancel_order ganó la carrera, rowcount=0 → skip.
                expired = await self.order_repo.expire_if_pending(order.id)
                if not expired:
                    logger.info("Order %s skipped by cleanup: status changed concurrently", order.id)
                    continue
                await self.history_repo.create(
                    order_id=order.id,
                    old_status=old_status,
                    new_status="expired",
                    notes="Auto-expired: pago no confirmado en ventana de tiempo",
                )
                await self.order_repo.save()
                for item in items:
                    await _catalog_restore_stock(item.product_id, item.quantity)
                expired_count += 1
                logger.info("Order expired: %s (created_at=%s)", order.id, order.created_at)
            except Exception as e:
                logger.error("cleanup_expired_orders failed for order %s: %s", order.id, e)
        return expired_count
