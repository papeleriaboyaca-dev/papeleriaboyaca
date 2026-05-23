"""
Tests del AuthService — mockea Supabase Auth para no hacer llamadas reales.
"""
import pytest
import jwt
import os
from uuid import uuid4
from unittest.mock import MagicMock, patch
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import StaticPool

from src.infrastructure.database import Base
from src.infrastructure.models import User, Role
from src.infrastructure.repositories import UserRepository, RoleRepository
from src.application.services import AuthService
from src.application.dtos import UserCreate

os.environ.setdefault("SUPABASE_URL", "https://test.supabase.co")
os.environ.setdefault("SUPABASE_KEY", "test-service-key")
os.environ.setdefault("SUPABASE_JWT_SECRET", "test-jwt-secret-for-unit-tests-only-32chars!!")


# ── Fixtures DB ───────────────────────────────────────────────────────────────

@pytest.fixture
async def db_session():
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with engine.begin() as conn:
        await conn.run_sync(lambda c: [setattr(t, "schema", None) for t in Base.metadata.sorted_tables])
        await conn.run_sync(Base.metadata.create_all)

    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        role = Role(name="CLIENTE", description="Client")
        session.add(role)
        await session.commit()
        yield session

    await engine.dispose()


@pytest.fixture
async def auth_service(db_session):
    return AuthService(UserRepository(db_session), RoleRepository(db_session))


# ── Helper: mock del cliente Supabase ─────────────────────────────────────────

def _make_supabase_mock(supabase_uid=None, email="test@example.com",
                        access_token="fake.access.token",
                        refresh_token="fake.refresh.token"):
    supabase_uid = supabase_uid or str(uuid4())

    mock_user = MagicMock()
    mock_user.id = supabase_uid

    mock_session = MagicMock()
    mock_session.access_token = access_token
    mock_session.refresh_token = refresh_token
    mock_session.expires_in = 3600

    mock_resp = MagicMock()
    mock_resp.user = mock_user
    mock_resp.session = mock_session

    mock_sb = MagicMock()
    mock_sb.auth.sign_up.return_value = mock_resp
    mock_sb.auth.sign_in_with_password.return_value = mock_resp
    mock_sb.auth.refresh_session.return_value = mock_resp

    return mock_sb


# ── Register ──────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_register_user(auth_service):
    with patch("src.application.services._get_supabase", return_value=_make_supabase_mock()):
        user = await auth_service.register_user(
            email="test@example.com", password="Secure123",
            first_name="Test", last_name="User",
        )
    assert user.email == "test@example.com"
    assert user.is_active is True


@pytest.mark.asyncio
async def test_register_user_duplicate_email(auth_service):
    with patch("src.application.services._get_supabase", return_value=_make_supabase_mock()):
        await auth_service.register_user(
            email="dup@example.com", password="Secure123",
            first_name="A", last_name="B",
        )
        with pytest.raises(ValueError, match="Email already registered"):
            await auth_service.register_user(
                email="dup@example.com", password="Secure123",
                first_name="A", last_name="B",
            )


@pytest.mark.asyncio
async def test_register_user_short_password_rejected():
    """Pydantic rechaza passwords de menos de 8 caracteres."""
    with pytest.raises(Exception):
        UserCreate(email="a@b.com", password="short", first_name="X", last_name="Y")


@pytest.mark.asyncio
async def test_register_supabase_failure_propagates(auth_service):
    """Si Supabase falla, se lanza ValueError."""
    mock_sb = MagicMock()
    mock_sb.auth.sign_up.side_effect = Exception("Supabase error")
    with patch("src.application.services._get_supabase", return_value=mock_sb):
        with pytest.raises(ValueError, match="Supabase auth error"):
            await auth_service.register_user(
                email="fail@example.com", password="Secure123",
                first_name="A", last_name="B",
            )


# ── Login ─────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_login_user(auth_service):
    mock_sb = _make_supabase_mock()
    with patch("src.application.services._get_supabase", return_value=mock_sb):
        await auth_service.register_user(
            email="login@example.com", password="Secure123",
            first_name="A", last_name="B",
        )
        tokens = await auth_service.login_user("login@example.com", "Secure123")

    assert tokens.access_token == "fake.access.token"
    assert tokens.refresh_token == "fake.refresh.token"
    assert tokens.token_type == "bearer"


@pytest.mark.asyncio
async def test_login_user_invalid_password(auth_service):
    mock_sb = _make_supabase_mock()
    mock_sb.auth.sign_in_with_password.side_effect = Exception("Invalid credentials")

    with patch("src.application.services._get_supabase", return_value=mock_sb):
        await auth_service.register_user(
            email="x@x.com", password="Secure123",
            first_name="A", last_name="B",
        )
        with pytest.raises(ValueError, match="Invalid email or password"):
            await auth_service.login_user("x@x.com", "wrong_password")


@pytest.mark.asyncio
async def test_login_nonexistent_user(auth_service):
    mock_sb = MagicMock()
    mock_sb.auth.sign_in_with_password.side_effect = Exception("User not found")
    with patch("src.application.services._get_supabase", return_value=mock_sb):
        with pytest.raises(ValueError, match="Invalid email or password"):
            await auth_service.login_user("ghost@example.com", "any_password_123")


# ── Validate token ────────────────────────────────────────────────────────────

def _make_supabase_jwt(sub=None, email="user@test.com"):
    """Genera un JWT con la misma firma que Supabase usaría."""
    from datetime import datetime, timedelta
    import os
    secret = os.environ["SUPABASE_JWT_SECRET"]
    payload = {
        "sub": str(sub or uuid4()),
        "email": email,
        "aud": "authenticated",
        "role": "authenticated",
        "iat": datetime.utcnow(),
        "exp": datetime.utcnow() + timedelta(hours=1),
    }
    return jwt.encode(payload, secret, algorithm="HS256")


@pytest.mark.asyncio
async def test_validate_access_token(auth_service):
    token = _make_supabase_jwt(email="user@test.com")
    payload = await auth_service.validate_token(token)
    assert payload["email"] == "user@test.com"
    assert payload["aud"] == "authenticated"


@pytest.mark.asyncio
async def test_validate_invalid_token(auth_service):
    with pytest.raises(ValueError, match="Invalid token"):
        await auth_service.validate_token("this.is.not.a.token")
