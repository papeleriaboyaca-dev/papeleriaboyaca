import re
from pydantic import BaseModel, EmailStr, Field, field_validator
from uuid import UUID
from datetime import datetime
from typing import Optional

_SPECIAL = r"[!@#$%^&*()\-_=+\[\]{}|\\:;\"'<>,.?/~`]"


def _check_password_strength(v: str) -> str:
    if len(v) < 8 or len(v) > 72:
        raise ValueError("La contraseña debe tener entre 8 y 72 caracteres")
    if not re.search(r"[A-Z]", v):
        raise ValueError("La contraseña debe tener al menos una mayúscula")
    if not re.search(r"[a-z]", v):
        raise ValueError("La contraseña debe tener al menos una minúscula")
    if not re.search(r"\d", v):
        raise ValueError("La contraseña debe tener al menos un número")
    if not re.search(_SPECIAL, v):
        raise ValueError("La contraseña debe tener al menos un carácter especial")
    return v


class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=72)
    first_name: str = Field(min_length=1, max_length=100)
    last_name: str = Field(min_length=1, max_length=100)

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        return _check_password_strength(v)

    @field_validator("first_name", "last_name")
    @classmethod
    def validate_names(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("El campo no puede estar vacío")
        return v


class UserUpdate(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: Optional[EmailStr] = None


class UserUpdateMe(BaseModel):
    first_name: Optional[str] = Field(None, min_length=1, max_length=100)
    last_name: Optional[str] = Field(None, min_length=1, max_length=100)
    phone: Optional[str] = None
    city: Optional[str] = None
    address: Optional[str] = None
    document_id: Optional[str] = None

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        v = v.strip()
        if not v:
            return None
        if not re.match(r"^\+?[\d\s\-]{7,15}$", v):
            raise ValueError("Número de teléfono inválido")
        if len(re.sub(r"\D", "", v)) < 7:
            raise ValueError("El teléfono debe tener al menos 7 dígitos")
        return v

    @field_validator("first_name", "last_name")
    @classmethod
    def strip_names(cls, v: Optional[str]) -> Optional[str]:
        return v.strip() if v else v


class UserResponse(BaseModel):
    id: UUID
    email: str
    first_name: str
    last_name: str
    is_active: bool
    created_at: datetime
    role_name: Optional[str] = None
    phone: Optional[str] = None
    city: Optional[str] = None
    document_id: Optional[str] = None

    class Config:
        from_attributes = True


class LoginRequest(BaseModel):
    email: str
    password: str


class ForgotPasswordRequest(BaseModel):
    email: EmailStr
    redirect_url: Optional[str] = None


class ChangePasswordRequest(BaseModel):
    supabase_id: str
    new_password: str = Field(min_length=8, max_length=72)

    @field_validator("new_password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        return _check_password_strength(v)


class TokenResponse(BaseModel):
    access_token: str = ""
    refresh_token: str = ""
    token_type: str = "bearer"
    expires_in: int = 86400
    requires_confirmation: bool = False
