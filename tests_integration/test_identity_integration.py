"""
Tests de INTEGRACIÓN del identity-service contra PostgreSQL real.
Requieren: export TEST_DATABASE_URL=postgresql+asyncpg://...
           El rol CLIENTE debe existir en la BD de test.

Ejecutar: pytest tests_integration/test_identity_integration.py -v -m integration
"""
import pytest
from uuid import uuid4


@pytest.mark.integration
async def test_register_and_login_real_db(identity_client_integration):
    """Flujo completo register → login usando PostgreSQL real."""
    uid = uuid4().hex[:6]
    payload = {
        "email": f"integ_{uid}@papeleria.com",
        "password": "IntegPass123",
        "first_name": "Integración",
        "last_name": "Test",
    }

    # Register
    resp = await identity_client_integration.post("/auth/register", json=payload)
    assert resp.status_code == 200, resp.text
    assert resp.json()["email"] == payload["email"]

    # Login
    resp = await identity_client_integration.post(
        "/auth/login",
        json={"email": payload["email"], "password": payload["password"]},
    )
    assert resp.status_code == 200
    assert "access_token" in resp.json()
    # El ROLLBACK del fixture limpia el usuario automáticamente


@pytest.mark.integration
async def test_duplicate_email_real_db(identity_client_integration):
    """Duplicado de email detectado por constraint único de PostgreSQL."""
    uid = uuid4().hex[:6]
    payload = {
        "email": f"dup_{uid}@papeleria.com",
        "password": "SecurePass123",
        "first_name": "Dup",
        "last_name": "Test",
    }
    await identity_client_integration.post("/auth/register", json=payload)
    resp = await identity_client_integration.post("/auth/register", json=payload)
    assert resp.status_code == 400
