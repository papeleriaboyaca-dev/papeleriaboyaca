from typing import Optional
from uuid import UUID
from ..config import settings
from ..infrastructure.repositories import UserRepository, RoleRepository
from ..application.dtos import UserResponse, TokenResponse


_supabase_client = None


def _get_supabase():
    """Retorna cliente Supabase sync (singleton, usado vía run_in_executor)."""
    global _supabase_client
    if _supabase_client is None:
        from supabase import create_client
        _supabase_client = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)
    return _supabase_client


class AuthService:
    def __init__(self, user_repo: UserRepository, role_repo: RoleRepository):
        self.user_repo = user_repo
        self.role_repo = role_repo

    # ── Auth vía Supabase ─────────────────────────────────────────────────────

    async def register_user(self, email: str, password: str, first_name: str,
                            last_name: str, **kwargs) -> UserResponse:
        import asyncio

        existing = await self.user_repo.find_by_email(email)
        if existing:
            raise ValueError("Email already registered")

        cliente_role = await self.role_repo.find_by_name("CLIENTE")
        if not cliente_role:
            raise ValueError("Default role not found")

        # Crear usuario en Supabase Auth
        loop = asyncio.get_running_loop()
        supabase = await loop.run_in_executor(None, _get_supabase)

        try:
            response = await loop.run_in_executor(
                None,
                lambda: supabase.auth.sign_up({"email": email, "password": password}),
            )
        except Exception as e:
            raise ValueError(f"Supabase auth error: {str(e)}")

        if not response.user:
            raise ValueError("Failed to create user in Supabase Auth")

        supabase_id = UUID(str(response.user.id))

        # Guardar en nuestra PostgreSQL con el supabase_id
        user = await self.user_repo.create(
            email=email,
            password_hash="managed-by-supabase",  # contraseña la maneja Supabase
            first_name=first_name,
            last_name=last_name,
            role_id=cliente_role.id,
            supabase_id=supabase_id,
            **kwargs,
        )
        await self.user_repo.save()

        return UserResponse(
            id=user.id,
            email=user.email,
            first_name=user.first_name,
            last_name=user.last_name,
            is_active=user.is_active,
            created_at=user.created_at,
        )

    async def login_user(self, email: str, password: str) -> TokenResponse:
        import asyncio

        # Verificar en nuestra BD antes de llamar a Supabase
        user = await self.user_repo.find_by_email(email)
        if not user:
            raise ValueError("Invalid email or password")
        if not user.is_active:
            raise ValueError("User account is disabled")

        loop = asyncio.get_running_loop()
        supabase = await loop.run_in_executor(None, _get_supabase)

        try:
            response = await loop.run_in_executor(
                None,
                lambda: supabase.auth.sign_in_with_password(
                    {"email": email, "password": password}
                ),
            )
        except Exception:
            raise ValueError("Invalid email or password")

        if not response.session:
            raise ValueError("Invalid email or password")

        return TokenResponse(
            access_token=response.session.access_token,
            refresh_token=response.session.refresh_token,
            token_type="bearer",
            expires_in=response.session.expires_in or 3600,
        )

    async def refresh_token(self, refresh_token: str) -> TokenResponse:
        import asyncio

        loop = asyncio.get_running_loop()
        supabase = await loop.run_in_executor(None, _get_supabase)

        try:
            response = await loop.run_in_executor(
                None,
                lambda: supabase.auth.refresh_session(refresh_token),
            )
        except Exception as e:
            raise ValueError("Invalid or expired refresh token")

        if not response.session:
            raise ValueError("Could not refresh session")

        return TokenResponse(
            access_token=response.session.access_token,
            refresh_token=response.session.refresh_token,
            token_type="bearer",
            expires_in=response.session.expires_in or 3600,
        )

    async def get_me(self, supabase_id: UUID) -> UserResponse:
        user = await self.user_repo.find_by_supabase_id(supabase_id)
        if not user:
            raise ValueError("User not found")

        role = await self.role_repo.find_by_id(user.role_id)
        return UserResponse(
            id=user.id,
            email=user.email,
            first_name=user.first_name,
            last_name=user.last_name,
            is_active=user.is_active,
            created_at=user.created_at,
            role_name=role.name if role else None,
            phone=user.phone,
            city=user.city,
            document_id=user.document_id,
        )

    async def update_me(self, supabase_id: UUID, **kwargs) -> UserResponse:
        user = await self.user_repo.find_by_supabase_id(supabase_id)
        if not user:
            raise ValueError("User not found")

        allowed = {"first_name", "last_name", "phone", "city", "address", "document_id"}
        filtered = {k: v for k, v in kwargs.items() if k in allowed and v is not None}
        updated = await self.user_repo.update(user.id, **filtered)
        await self.user_repo.save()

        role = await self.role_repo.find_by_id(updated.role_id)
        return UserResponse(
            id=updated.id,
            email=updated.email,
            first_name=updated.first_name,
            last_name=updated.last_name,
            is_active=updated.is_active,
            created_at=updated.created_at,
            role_name=role.name if role else None,
            phone=updated.phone,
            city=updated.city,
            document_id=updated.document_id,
        )

    async def logout(self, supabase_user_id: str, jwt_token: str | None = None) -> None:
        import asyncio
        if not jwt_token:
            return  # nada que invalidar sin el token de sesión
        loop = asyncio.get_running_loop()
        supabase = await loop.run_in_executor(None, _get_supabase)
        try:
            await loop.run_in_executor(
                None,
                lambda: supabase.auth.admin.sign_out(jwt_token),
            )
        except Exception as e:
            raise ValueError(f"Logout failed: {e}")

    async def forgot_password(self, email: str, redirect_url: str | None = None) -> None:
        import asyncio
        loop = asyncio.get_running_loop()
        supabase = await loop.run_in_executor(None, _get_supabase)
        options = {"redirect_to": redirect_url} if redirect_url else {}
        try:
            await loop.run_in_executor(
                None,
                lambda: supabase.auth.reset_password_email(email, options),
            )
        except Exception as e:
            raise ValueError(f"Password reset failed: {e}")

    async def change_password(self, supabase_user_id: str, new_password: str) -> None:
        import asyncio
        loop = asyncio.get_running_loop()
        supabase = await loop.run_in_executor(None, _get_supabase)
        try:
            await loop.run_in_executor(
                None,
                lambda: supabase.auth.admin.update_user_by_id(
                    supabase_user_id,
                    {"password": new_password},
                ),
            )
        except Exception as e:
            raise ValueError(f"Password change failed: {e}")

    async def list_users(self, skip: int = 0, limit: int = 50) -> list[UserResponse]:
        users = await self.user_repo.list_all(skip, limit)
        roles = {r.id: r for r in await self.role_repo.list_all()}
        return [
            UserResponse(
                id=u.id,
                email=u.email,
                first_name=u.first_name,
                last_name=u.last_name,
                is_active=u.is_active,
                created_at=u.created_at,
                role_name=roles[u.role_id].name if u.role_id in roles else None,
                phone=u.phone,
                city=u.city,
                document_id=u.document_id,
            )
            for u in users
        ]

    async def set_user_active(self, user_id: UUID, is_active: bool) -> UserResponse:
        user = await self.user_repo.find_by_id(user_id)
        if not user:
            raise ValueError("User not found")
        updated = await self.user_repo.update(user_id, is_active=is_active)
        await self.user_repo.save()
        role = await self.role_repo.find_by_id(updated.role_id)
        return UserResponse(
            id=updated.id,
            email=updated.email,
            first_name=updated.first_name,
            last_name=updated.last_name,
            is_active=updated.is_active,
            created_at=updated.created_at,
            role_name=role.name if role else None,
        )

    async def change_user_role(self, user_id: UUID, role_name: str) -> UserResponse:
        user = await self.user_repo.find_by_id(user_id)
        if not user:
            raise ValueError("User not found")
        role = await self.role_repo.find_by_name(role_name)
        if not role:
            raise ValueError(f"Role '{role_name}' not found")
        updated = await self.user_repo.update(user_id, role_id=role.id)
        await self.user_repo.save()
        return UserResponse(
            id=updated.id,
            email=updated.email,
            first_name=updated.first_name,
            last_name=updated.last_name,
            is_active=updated.is_active,
            created_at=updated.created_at,
            role_name=role.name,
        )

    async def validate_token(self, token: str) -> dict:
        """Valida un JWT de Supabase con el JWT secret."""
        import jwt
        try:
            payload = jwt.decode(
                token,
                settings.SUPABASE_JWT_SECRET,
                algorithms=["HS256"],
                audience="authenticated",
            )
            return payload
        except jwt.ExpiredSignatureError:
            raise ValueError("Token expired")
        except jwt.InvalidTokenError as e:
            raise ValueError(f"Invalid token: {e}")
