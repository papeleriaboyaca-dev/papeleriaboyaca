"""
Tests HTTP del identity-service — endpoints /auth/*
Ejecutar: cd identity-service && pytest tests/test_http_auth.py -v
"""
import pytest


# ═══════════════════════════════════════════════════════════════════════════════
# POST /auth/register
# ═══════════════════════════════════════════════════════════════════════════════

class TestRegister:

    @pytest.mark.unit
    async def test_register_success(self, async_client, user_payload):
        """201 — registro válido devuelve tokens de acceso."""
        resp = await async_client.post("/auth/register", json=user_payload)
        assert resp.status_code == 201
        body = resp.json()
        assert "access_token" in body
        assert "refresh_token" in body
        assert body["token_type"] == "bearer"
        assert body["expires_in"] > 0

    @pytest.mark.unit
    async def test_register_duplicate_email(self, async_client, user_payload):
        """400 — email ya registrado."""
        await async_client.post("/auth/register", json=user_payload)
        resp = await async_client.post("/auth/register", json=user_payload)
        assert resp.status_code == 400
        assert "already registered" in resp.json()["detail"].lower()

    @pytest.mark.unit
    async def test_register_missing_fields(self, async_client):
        """422 — campos requeridos faltantes."""
        resp = await async_client.post("/auth/register", json={"email": "x@x.com"})
        assert resp.status_code == 422

    @pytest.mark.unit
    async def test_register_invalid_email(self, async_client):
        """422 — email con formato inválido."""
        resp = await async_client.post(
            "/auth/register",
            json={"email": "not-an-email", "password": "Pass1234!", "first_name": "A", "last_name": "B"},
        )
        assert resp.status_code == 422

    @pytest.mark.unit
    async def test_register_short_password(self, async_client):
        """422 — password menor a 8 caracteres."""
        resp = await async_client.post(
            "/auth/register",
            json={"email": "ok@ok.com", "password": "short", "first_name": "A", "last_name": "B"},
        )
        assert resp.status_code == 422

    @pytest.mark.unit
    async def test_register_empty_body(self, async_client):
        """422 — body vacío."""
        resp = await async_client.post("/auth/register", json={})
        assert resp.status_code == 422


# ═══════════════════════════════════════════════════════════════════════════════
# POST /auth/login
# ═══════════════════════════════════════════════════════════════════════════════

class TestLogin:

    @pytest.mark.unit
    async def test_login_success(self, async_client, registered_user):
        """200 — credenciales correctas devuelven access + refresh token."""
        payload = registered_user["payload"]
        resp = await async_client.post(
            "/auth/login",
            json={"email": payload["email"], "password": payload["password"]},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert "access_token" in body
        assert "refresh_token" in body
        assert body["token_type"] == "bearer"
        assert body["expires_in"] > 0

    @pytest.mark.unit
    async def test_login_wrong_password(self, async_client, registered_user):
        """401 — password incorrecto."""
        from unittest.mock import patch, MagicMock
        payload = registered_user["payload"]
        mock_sb = MagicMock()
        mock_sb.auth.sign_in_with_password.side_effect = Exception("Invalid credentials")
        with patch("src.application.services._get_supabase", return_value=mock_sb):
            resp = await async_client.post(
                "/auth/login",
                json={"email": payload["email"], "password": "WrongPass999"},
            )
        assert resp.status_code == 401
        assert "invalid" in resp.json()["detail"].lower()

    @pytest.mark.unit
    async def test_login_nonexistent_user(self, async_client):
        """401 — usuario no existe."""
        resp = await async_client.post(
            "/auth/login",
            json={"email": "ghost@papeleria.com", "password": "AnyPass123"},
        )
        assert resp.status_code == 401

    @pytest.mark.unit
    async def test_login_missing_password(self, async_client):
        """422 — falta campo password."""
        resp = await async_client.post("/auth/login", json={"email": "x@x.com"})
        assert resp.status_code == 422

    @pytest.mark.unit
    async def test_login_empty_email(self, async_client):
        """401 — email vacío no corresponde a ningún usuario (LoginRequest usa str, no EmailStr)."""
        resp = await async_client.post("/auth/login", json={"email": "", "password": "Pass1234"})
        assert resp.status_code == 401


# ═══════════════════════════════════════════════════════════════════════════════
# POST /auth/refresh
# ═══════════════════════════════════════════════════════════════════════════════

class TestRefresh:

    @pytest.mark.unit
    async def test_refresh_success(self, async_client, auth_tokens):
        """200 — refresh token válido devuelve nueva estructura de tokens."""
        resp = await async_client.post(
            "/auth/refresh",
            json={"token": auth_tokens["refresh_token"]},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert "access_token" in body
        assert "refresh_token" in body
        assert body["token_type"] == "bearer"
        assert body["expires_in"] > 0

    @pytest.mark.unit
    async def test_refresh_with_invalid_token_rejected(self, async_client):
        """401 — token totalmente inválido."""
        from unittest.mock import patch, MagicMock
        mock_sb = MagicMock()
        mock_sb.auth.refresh_session.side_effect = Exception("Invalid refresh token")
        with patch("src.application.services._get_supabase", return_value=mock_sb):
            resp = await async_client.post(
                "/auth/refresh",
                json={"token": "not.a.valid.token"},
            )
        assert resp.status_code == 401

    @pytest.mark.unit
    async def test_refresh_invalid_token(self, async_client):
        """401 — token completamente inválido."""
        from unittest.mock import patch, MagicMock
        mock_sb = MagicMock()
        mock_sb.auth.refresh_session.side_effect = Exception("Invalid refresh token")
        with patch("src.application.services._get_supabase", return_value=mock_sb):
            resp = await async_client.post(
                "/auth/refresh",
                json={"token": "this.is.garbage"},
            )
        assert resp.status_code == 401

    @pytest.mark.unit
    async def test_refresh_missing_token(self, async_client):
        """422 — sin parámetro token."""
        resp = await async_client.post("/auth/refresh")
        assert resp.status_code == 422


# ═══════════════════════════════════════════════════════════════════════════════
# GET /health
# ═══════════════════════════════════════════════════════════════════════════════

class TestHealth:

    @pytest.mark.unit
    async def test_health(self, async_client):
        resp = await async_client.get("/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"
