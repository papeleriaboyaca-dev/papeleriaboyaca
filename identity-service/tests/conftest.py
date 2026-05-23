"""
Fixtures compartidas del identity-service.
"""
import pytest
import sys
import os
import jwt
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch
from uuid import uuid4

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# Deben estar antes de importar src para que Settings() los capture
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
os.environ.setdefault("SUPABASE_URL", "https://test.supabase.co")
os.environ.setdefault("SUPABASE_KEY", "test-service-key")
os.environ.setdefault("SUPABASE_JWT_SECRET", "test-jwt-secret-for-unit-tests-only-32chars!!")
os.environ.setdefault("JWT_SECRET_KEY", "test-jwt-secret-for-unit-tests-only-32chars!!")

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import StaticPool
from httpx import AsyncClient, ASGITransport

from src.infrastructure.database import Base, get_db
from src.infrastructure.models import Role
from src.infrastructure.repositories import UserRepository, RoleRepository
from src.application.services import AuthService

_JWT_SECRET = os.environ["SUPABASE_JWT_SECRET"]


# ── Supabase mock ─────────────────────────────────────────────────────────────

def _make_supabase_jwt(sub=None, email="user@test.com") -> str:
    """JWT compatible con el formato de Supabase Auth."""
    payload = {
        "sub": str(sub or uuid4()),
        "email": email,
        "aud": "authenticated",
        "role": "authenticated",
        "iat": datetime.utcnow(),
        "exp": datetime.utcnow() + timedelta(hours=1),
    }
    return jwt.encode(payload, _JWT_SECRET, algorithm="HS256")


def make_supabase_mock(email="user@papeleria.com"):
    uid = str(uuid4())
    access = _make_supabase_jwt(sub=uid, email=email)
    refresh = "fake-refresh-token-" + uid[:8]

    mock_user = MagicMock()
    mock_user.id = uid

    mock_session = MagicMock()
    mock_session.access_token = access
    mock_session.refresh_token = refresh
    mock_session.expires_in = 3600

    mock_resp = MagicMock()
    mock_resp.user = mock_user
    mock_resp.session = mock_session

    mock_sb = MagicMock()
    mock_sb.auth.sign_up.return_value = mock_resp
    mock_sb.auth.sign_in_with_password.return_value = mock_resp
    mock_sb.auth.refresh_session.return_value = mock_resp
    return mock_sb


# ── DB en memoria ─────────────────────────────────────────────────────────────

@pytest.fixture(scope="function")
async def db_engine():
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with engine.begin() as conn:
        await conn.run_sync(
            lambda c: [setattr(t, "schema", None) for t in Base.metadata.sorted_tables]
        )
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest.fixture(scope="function")
async def db_session(db_engine):
    factory = async_sessionmaker(
        db_engine, class_=AsyncSession, expire_on_commit=False, autoflush=False
    )
    async with factory() as session:
        session.add(Role(name="CLIENTE", description="Cliente por defecto"))
        await session.commit()
        yield session


@pytest.fixture(scope="function")
async def auth_service(db_session):
    return AuthService(UserRepository(db_session), RoleRepository(db_session))


# ── Cliente HTTP (con Supabase mockeado) ──────────────────────────────────────

@pytest.fixture(scope="function")
async def async_client(db_session):
    from src.main import app

    async def _override():
        yield db_session

    app.dependency_overrides[get_db] = _override
    with patch("src.application.services._get_supabase",
               side_effect=lambda: make_supabase_mock()):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            yield c
    app.dependency_overrides.clear()


# ── Datos de prueba ────────────────────────────────────────────────────────────

@pytest.fixture
def user_payload():
    uid = uuid4().hex[:6]
    return {
        "email": f"user_{uid}@papeleria.com",
        "password": "SecurePass123!",
        "first_name": "Juan",
        "last_name": "Pérez",
    }


@pytest.fixture
async def registered_user(async_client, user_payload):
    resp = await async_client.post("/auth/register", json=user_payload)
    assert resp.status_code == 201, resp.text
    return {"payload": user_payload, "response": resp.json()}


@pytest.fixture
async def auth_tokens(async_client, user_payload):
    await async_client.post("/auth/register", json=user_payload)
    resp = await async_client.post(
        "/auth/login",
        json={"email": user_payload["email"], "password": user_payload["password"]},
    )
    assert resp.status_code == 200, resp.text
    return resp.json()
