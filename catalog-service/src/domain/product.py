from uuid import UUID
from datetime import datetime


class Product:
    def __init__(
        self,
        id: UUID,
        sku: str,
        name: str,
        price: float,
        stock: int,
        category_id: UUID,
        is_active: bool = True,
        created_at: datetime = None
    ):
        self.id = id
        self.sku = sku
        self.name = name
        self.price = price
        self.stock = stock
        self.category_id = category_id
        self.is_active = is_active
        self.created_at = created_at or datetime.now()

    def __repr__(self):
        return f"<Product {self.name}>"
