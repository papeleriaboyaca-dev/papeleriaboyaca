"""
Fixtures compartidas entre todos los servicios.
Ejecutar desde la raíz: pytest identity-service/tests/ catalog-service/tests/ ...
"""
import pytest
import jwt
from datetime import datetime, timedelta
from uuid import uuid4, UUID


# ── Constantes de test (nunca usar en producción) ─────────────────────────────
TEST_JWT_SECRET = "test-secret-key-for-testing-only-not-production"
TEST_JWT_ALGORITHM = "HS256"


# ── Helpers de JWT ────────────────────────────────────────────────────────────

def make_access_token(
    user_id: UUID = None,
    email: str = "test@papeleria.com",
    role_id: UUID = None,
    secret: str = TEST_JWT_SECRET,
    expired: bool = False,
) -> str:
    now = datetime.utcnow()
    exp = now - timedelta(hours=1) if expired else now + timedelta(hours=24)
    payload = {
        "sub": str(user_id or uuid4()),
        "email": email,
        "role_id": str(role_id or uuid4()),
        "iat": now,
        "exp": exp,
        "type": "access",
    }
    return jwt.encode(payload, secret, algorithm=TEST_JWT_ALGORITHM)


def make_refresh_token(user_id: UUID = None, secret: str = TEST_JWT_SECRET) -> str:
    now = datetime.utcnow()
    payload = {
        "sub": str(user_id or uuid4()),
        "iat": now,
        "exp": now + timedelta(days=7),
        "type": "refresh",
    }
    return jwt.encode(payload, secret, algorithm=TEST_JWT_ALGORITHM)


def auth_headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}
