from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import update
from uuid import UUID
from .models import Order, OrderItem, ShippingAddress, OrderHistory


class OrderRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def find_by_id(self, order_id: UUID) -> Order | None:
        result = await self.session.execute(
            select(Order).where(Order.id == order_id)
        )
        return result.scalars().first()

    async def find_by_order_number(self, order_number: str) -> Order | None:
        result = await self.session.execute(
            select(Order).where(Order.order_number == order_number)
        )
        return result.scalars().first()

    async def find_by_user(self, user_id: UUID, skip: int = 0,
                          limit: int = 20) -> list[Order]:
        result = await self.session.execute(
            select(Order)
            .where(Order.user_id == user_id)
            .order_by(Order.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        return result.scalars().all()

    async def find_all(self, skip: int = 0, limit: int = 100) -> list[Order]:
        result = await self.session.execute(
            select(Order)
            .order_by(Order.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        return result.scalars().all()

    async def create(self, order_number: str, user_id: UUID, total: float, 
                    **kwargs) -> Order:
        order = Order(
            order_number=order_number,
            user_id=user_id,
            total=total,
            **kwargs
        )
        self.session.add(order)
        await self.session.flush()
        return order

    async def update_status(self, order_id: UUID, new_status: str,
                            tracking_number: str | None = None,
                            shipping_carrier: str | None = None) -> Order | None:
        order = await self.find_by_id(order_id)
        if not order:
            return None
        order.status = new_status
        if tracking_number is not None:
            order.tracking_number = tracking_number
        if shipping_carrier is not None:
            order.shipping_carrier = shipping_carrier
        await self.session.flush()
        return order

    async def cancel_if_cancellable(self, order_id: UUID, allowed_statuses: set) -> bool:
        """Atomic conditional cancel — prevents double stock restoration with cleanup job."""
        result = await self.session.execute(
            update(Order)
            .where(Order.id == order_id, Order.status.in_(allowed_statuses))
            .values(status="cancelled")
        )
        await self.session.flush()
        return result.rowcount == 1

    async def expire_if_pending(self, order_id: UUID) -> bool:
        """Atomic conditional expire — prevents double stock restoration with cancel_order."""
        result = await self.session.execute(
            update(Order)
            .where(Order.id == order_id, Order.status.in_(("pending", "pending_payment")))
            .values(status="expired")
        )
        await self.session.flush()
        return result.rowcount == 1

    async def save(self) -> None:
        await self.session.commit()


class OrderItemRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def find_by_order(self, order_id: UUID) -> list[OrderItem]:
        result = await self.session.execute(
            select(OrderItem).where(OrderItem.order_id == order_id)
        )
        return result.scalars().all()

    async def create(self, order_id: UUID, product_id: UUID, quantity: int,
                    unit_price: float, product_name: str | None = None) -> OrderItem:
        subtotal = quantity * unit_price
        item = OrderItem(
            order_id=order_id,
            product_id=product_id,
            product_name=product_name,
            quantity=quantity,
            unit_price=unit_price,
            subtotal=subtotal,
        )
        self.session.add(item)
        await self.session.flush()
        return item

    async def save(self) -> None:
        await self.session.commit()


class OrderHistoryRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, order_id: UUID, new_status: str,
                     old_status: str | None = None,
                     changed_by: UUID | None = None,
                     notes: str | None = None) -> OrderHistory:
        entry = OrderHistory(
            order_id=order_id,
            old_status=old_status,
            new_status=new_status,
            changed_by=changed_by,
            notes=notes,
        )
        self.session.add(entry)
        await self.session.flush()
        return entry

    async def find_by_order(self, order_id: UUID) -> list[OrderHistory]:
        result = await self.session.execute(
            select(OrderHistory)
            .where(OrderHistory.order_id == order_id)
            .order_by(OrderHistory.created_at.asc())
        )
        return result.scalars().all()

    async def save(self) -> None:
        await self.session.commit()


class ShippingAddressRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def find_by_id(self, address_id: UUID) -> ShippingAddress | None:
        result = await self.session.execute(
            select(ShippingAddress).where(ShippingAddress.id == address_id)
        )
        return result.scalars().first()

    async def find_by_user(self, user_id: UUID) -> list[ShippingAddress]:
        result = await self.session.execute(
            select(ShippingAddress)
            .where(ShippingAddress.user_id == user_id)
            .order_by(ShippingAddress.created_at.desc())
        )
        return result.scalars().all()

    async def create(self, user_id: UUID, address_line1: str, city: str,
                    postal_code: str, **kwargs) -> ShippingAddress:
        address = ShippingAddress(
            user_id=user_id,
            address_line1=address_line1,
            city=city,
            postal_code=postal_code,
            **kwargs
        )
        self.session.add(address)
        await self.session.flush()
        return address

    async def update(self, address_id: UUID, **kwargs) -> ShippingAddress | None:
        address = await self.find_by_id(address_id)
        if not address:
            return None
        for key, value in kwargs.items():
            setattr(address, key, value)
        await self.session.flush()
        return address

    async def delete(self, address_id: UUID) -> bool:
        address = await self.find_by_id(address_id)
        if not address:
            return False
        await self.session.delete(address)
        await self.session.flush()
        return True

    async def save(self) -> None:
        await self.session.commit()
