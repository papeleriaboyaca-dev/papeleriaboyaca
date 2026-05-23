from uuid import UUID
from datetime import datetime


class User:
    def __init__(
        self,
        id: UUID,
        email: str,
        first_name: str,
        last_name: str,
        role_id: UUID,
        is_active: bool = True,
        created_at: datetime = None
    ):
        self.id = id
        self.email = email
        self.first_name = first_name
        self.last_name = last_name
        self.role_id = role_id
        self.is_active = is_active
        self.created_at = created_at or datetime.now()

    def __repr__(self):
        return f"<User {self.email}>"
