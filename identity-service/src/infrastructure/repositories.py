from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import joinedload
from uuid import UUID
from .models import User, Role
from ..domain.user import User as UserEntity


class UserRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def find_by_email(self, email: str) -> User | None:
        result = await self.session.execute(
            select(User).where(User.email == email)
        )
        return result.scalars().first()

    async def find_by_id(self, user_id: UUID) -> User | None:
        result = await self.session.execute(
            select(User).where(User.id == user_id)
        )
        return result.scalars().first()

    async def find_by_supabase_id(self, supabase_id: UUID) -> User | None:
        result = await self.session.execute(
            select(User).where(User.supabase_id == supabase_id)
        )
        return result.scalars().first()

    async def find_by_document_id(self, document_id: str) -> User | None:
        result = await self.session.execute(
            select(User).where(User.document_id == document_id)
        )
        return result.scalars().first()

    async def create(self, email: str, password_hash: str, first_name: str, 
                    last_name: str, role_id: UUID, **kwargs) -> User:
        user = User(
            email=email,
            password_hash=password_hash,
            first_name=first_name,
            last_name=last_name,
            role_id=role_id,
            **kwargs
        )
        self.session.add(user)
        await self.session.flush()
        return user

    async def update(self, user_id: UUID, **kwargs) -> User | None:
        user = await self.find_by_id(user_id)
        if not user:
            return None
        for key, value in kwargs.items():
            if hasattr(user, key):
                setattr(user, key, value)
        await self.session.flush()
        return user

    async def list_all(self, skip: int = 0, limit: int = 10) -> list[User]:
        result = await self.session.execute(
            select(User).offset(skip).limit(limit)
        )
        return result.scalars().all()

    async def save(self) -> None:
        await self.session.commit()


class RoleRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def find_by_id(self, role_id: UUID) -> Role | None:
        result = await self.session.execute(
            select(Role).where(Role.id == role_id)
        )
        return result.scalars().first()

    async def find_by_name(self, name: str) -> Role | None:
        result = await self.session.execute(
            select(Role).where(Role.name == name)
        )
        return result.scalars().first()

    async def list_all(self) -> list[Role]:
        result = await self.session.execute(select(Role))
        return result.scalars().all()

    async def save(self) -> None:
        await self.session.commit()


