from fastapi import APIRouter, Depends, HTTPException, status, Body, Header, Query
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID
from pydantic import BaseModel
from ..application.dtos import UserCreate, UserResponse, LoginRequest, TokenResponse, UserUpdateMe, ForgotPasswordRequest, ChangePasswordRequest
from ..application.services import AuthService
from ..infrastructure.database import get_db
from ..infrastructure.repositories import UserRepository, RoleRepository


router = APIRouter(prefix="/auth", tags=["auth"])


async def get_auth_service(db: AsyncSession = Depends(get_db)) -> AuthService:
    user_repo = UserRepository(db)
    role_repo = RoleRepository(db)
    return AuthService(user_repo, role_repo)


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(
    user_data: UserCreate,
    auth_service: AuthService = Depends(get_auth_service),
):
    try:
        await auth_service.register_user(
            email=user_data.email,
            password=user_data.password,
            first_name=user_data.first_name,
            last_name=user_data.last_name,
        )
        tokens = await auth_service.login_user(
            email=user_data.email,
            password=user_data.password,
        )
        return tokens
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.post("/login", response_model=TokenResponse)
async def login(
    credentials: LoginRequest,
    auth_service: AuthService = Depends(get_auth_service),
):
    try:
        tokens = await auth_service.login_user(
            email=credentials.email,
            password=credentials.password,
        )
        return tokens
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
        )


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    token: str = Body(..., embed=True),
    auth_service: AuthService = Depends(get_auth_service),
):
    try:
        return await auth_service.refresh_token(token)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
        )


@router.post("/logout", status_code=204)
async def logout(
    supabase_id: str,
    authorization: Optional[str] = Header(None),
    auth_service: AuthService = Depends(get_auth_service),
):
    jwt_token = (authorization.split(" ", 1)[1]
                 if authorization and authorization.startswith("Bearer ")
                 else None)
    try:
        await auth_service.logout(supabase_id, jwt_token)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/forgot-password", status_code=204)
async def forgot_password(
    body: ForgotPasswordRequest,
    auth_service: AuthService = Depends(get_auth_service),
):
    try:
        await auth_service.forgot_password(body.email, body.redirect_url)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/change-password", status_code=204)
async def change_password(
    body: ChangePasswordRequest,
    auth_service: AuthService = Depends(get_auth_service),
):
    try:
        await auth_service.change_password(body.supabase_id, body.new_password)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/me", response_model=UserResponse)
async def get_me(
    supabase_id: UUID,
    auth_service: AuthService = Depends(get_auth_service),
):
    try:
        return await auth_service.get_me(supabase_id)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )


@router.put("/me", response_model=UserResponse)
async def update_me(
    supabase_id: UUID,
    body: UserUpdateMe,
    auth_service: AuthService = Depends(get_auth_service),
):
    try:
        return await auth_service.update_me(supabase_id, **body.model_dump())
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )


# ── Admin user management (called by gateway with SUPERADMIN guard) ───────────

class SetActiveRequest(BaseModel):
    is_active: bool


class ChangeRoleRequest(BaseModel):
    role_name: str


@router.get("/admin/users", response_model=list[UserResponse])
async def admin_list_users(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    auth_service: AuthService = Depends(get_auth_service),
):
    return await auth_service.list_users(skip, limit)


@router.put("/admin/users/{user_id}/active", response_model=UserResponse)
async def admin_set_user_active(
    user_id: UUID,
    body: SetActiveRequest,
    auth_service: AuthService = Depends(get_auth_service),
):
    try:
        return await auth_service.set_user_active(user_id, body.is_active)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.put("/admin/users/{user_id}/role", response_model=UserResponse)
async def admin_change_user_role(
    user_id: UUID,
    body: ChangeRoleRequest,
    auth_service: AuthService = Depends(get_auth_service),
):
    try:
        return await auth_service.change_user_role(user_id, body.role_name)
    except ValueError as e:
        code = status.HTTP_404_NOT_FOUND if "not found" in str(e).lower() else status.HTTP_400_BAD_REQUEST
        raise HTTPException(status_code=code, detail=str(e))
