"""
Fixtures del api-gateway. Sin BD — el gateway es un proxy puro.
"""
import pytest
import sys
import os
import jwt
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# Must be set before any src import so main.py env-var check passes
_JWT_SECRET = "dev-secret"
os.environ.setdefault("SUPABASE_JWT_SECRET", _JWT_SECRET)
os.environ.setdefault("IDENTITY_SERVICE_URL", "http://identity-service:8004")
os.environ.setdefault("CATALOG_SERVICE_URL", "http://catalog-service:8002")
os.environ.setdefault("ORDER_SERVICE_URL", "http://order-service:8003")
os.environ.setdefault("PAYMENT_SERVICE_URL", "http://payment-service:8005")

from httpx import AsyncClient, ASGITransport

_JWT_ALGORITHM = "HS256"


@pytest.fixture(scope="session")
def async_client_session():
    """App compartida a nivel de sesión (el gateway no tiene estado por request)."""
    return None


@pytest.fixture
async def async_client():
    from src.main import app
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


@pytest.fixture
def valid_token():
    """JWT de acceso válido firmado con el secret de desarrollo."""
    now = datetime.utcnow()
    payload = {
        "sub": "00000000-0000-0000-0000-000000000001",
        "email": "user@test.com",
        "user_role": "CLIENTE",
        "aud": "authenticated",
        "iat": now,
        "exp": now + timedelta(hours=1),
    }
    return jwt.encode(payload, _JWT_SECRET, algorithm=_JWT_ALGORITHM)


@pytest.fixture
def auth_headers(valid_token):
    return {"Authorization": f"Bearer {valid_token}"}


def make_mock_response(status_code: int = 200, json_data: dict = None):
    """Respuesta httpx simulada."""
    resp = MagicMock()
    resp.status_code = status_code
    resp.json.return_value = json_data or {}
    if status_code >= 400:
        from httpx import HTTPStatusError, Request, Response
        resp.raise_for_status.side_effect = HTTPStatusError(
            message=f"HTTP {status_code}",
            request=MagicMock(),
            response=resp,
        )
    else:
        resp.raise_for_status.return_value = None
    return resp


def make_mock_client(responses: dict = None):
    """
    Factory que devuelve un AsyncMock de httpx.AsyncClient.
    responses: {"get": resp, "post": resp, ...}
    """
    responses = responses or {}
    client = AsyncMock()
    client.__aenter__.return_value = client
    client.__aexit__.return_value = False

    for method, resp in responses.items():
        getattr(client, method).return_value = resp

    return client
