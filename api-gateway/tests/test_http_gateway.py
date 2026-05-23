"""
Tests HTTP del api-gateway — proxy + autenticación JWT.
Ejecutar: cd api-gateway && pytest tests/ -v
"""
import pytest
from unittest.mock import patch
from tests.conftest import make_mock_client, make_mock_response


# ═══════════════════════════════════════════════════════════════════════════════
# Health
# ═══════════════════════════════════════════════════════════════════════════════

class TestHealth:

    @pytest.mark.unit
    async def test_health(self, async_client):
        resp = await async_client.get("/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "healthy"


# ═══════════════════════════════════════════════════════════════════════════════
# Auth (endpoints públicos — sin JWT)
# ═══════════════════════════════════════════════════════════════════════════════

class TestAuthProxy:

    @pytest.mark.unit
    async def test_register_proxied(self, async_client):
        """POST /api/auth/register → identity-service, devuelve usuario creado."""
        user_resp = {
            "id": "abc",
            "email": "new@test.com",
            "first_name": "Ana",
            "last_name": "García",
            "is_active": True,
        }
        mock = make_mock_client({"post": make_mock_response(200, user_resp)})
        with patch("httpx.AsyncClient", return_value=mock):
            resp = await async_client.post(
                "/api/auth/register",
                json={
                    "email": "new@test.com",
                    "password": "Secret1234",
                    "first_name": "Ana",
                    "last_name": "García",
                },
            )
        assert resp.status_code == 200
        assert resp.json()["email"] == "new@test.com"

    @pytest.mark.unit
    async def test_register_missing_fields(self, async_client):
        """422 — campos requeridos faltantes (validación en el gateway, no llega al servicio)."""
        resp = await async_client.post("/api/auth/register", json={"email": "x@x.com"})
        assert resp.status_code == 422

    @pytest.mark.unit
    async def test_login_success(self, async_client):
        """POST /api/auth/login → devuelve access + refresh token."""
        token_resp = {
            "access_token": "tok.access",
            "refresh_token": "tok.refresh",
            "token_type": "bearer",
            "expires_in": 86400,
        }
        mock = make_mock_client({"post": make_mock_response(200, token_resp)})
        with patch("httpx.AsyncClient", return_value=mock):
            resp = await async_client.post(
                "/api/auth/login",
                json={"email": "user@test.com", "password": "Pass1234"},
            )
        assert resp.status_code == 200
        body = resp.json()
        assert "access_token" in body
        assert body["token_type"] == "bearer"

    @pytest.mark.unit
    async def test_login_bad_credentials_propagated(self, async_client):
        """401 del identity-service se propaga correctamente."""
        mock = make_mock_client({"post": make_mock_response(401, {"detail": "Invalid credentials"})})
        with patch("httpx.AsyncClient", return_value=mock):
            resp = await async_client.post(
                "/api/auth/login",
                json={"email": "x@x.com", "password": "wrong"},
            )
        assert resp.status_code == 401

    @pytest.mark.unit
    async def test_login_missing_password(self, async_client):
        """422 — falta campo password."""
        resp = await async_client.post("/api/auth/login", json={"email": "x@x.com"})
        assert resp.status_code == 422


# ═══════════════════════════════════════════════════════════════════════════════
# Catálogo (endpoints públicos)
# ═══════════════════════════════════════════════════════════════════════════════

class TestCatalogProxy:

    @pytest.mark.unit
    async def test_list_products(self, async_client):
        """GET /api/productos — no requiere autenticación."""
        products = [{"id": "1", "name": "Cuaderno", "price": 5000}]
        mock = make_mock_client({"get": make_mock_response(200, products)})
        with patch("httpx.AsyncClient", return_value=mock):
            resp = await async_client.get("/api/productos")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    @pytest.mark.unit
    async def test_get_product(self, async_client):
        """GET /api/productos/{id} — público."""
        product = {"id": "abc", "name": "Lapicero", "price": 1500}
        mock = make_mock_client({"get": make_mock_response(200, product)})
        with patch("httpx.AsyncClient", return_value=mock):
            resp = await async_client.get("/api/productos/abc")
        assert resp.status_code == 200
        assert resp.json()["name"] == "Lapicero"

    @pytest.mark.unit
    async def test_get_product_not_found_propagated(self, async_client):
        """404 del catalog-service se propaga."""
        mock = make_mock_client({"get": make_mock_response(404, {"detail": "Not found"})})
        with patch("httpx.AsyncClient", return_value=mock):
            resp = await async_client.get("/api/productos/nonexistent")
        assert resp.status_code == 404


# ═══════════════════════════════════════════════════════════════════════════════
# JWT — validación en el gateway
# ═══════════════════════════════════════════════════════════════════════════════

class TestJWTValidation:

    @pytest.mark.unit
    async def test_protected_no_token(self, async_client):
        """401 — sin header Authorization."""
        resp = await async_client.get("/api/pedidos/some-id")
        assert resp.status_code == 401

    @pytest.mark.unit
    async def test_protected_bad_format(self, async_client):
        """401 — header con formato incorrecto (sin 'Bearer ')."""
        resp = await async_client.get(
            "/api/pedidos/some-id",
            headers={"Authorization": "tok.access"},
        )
        assert resp.status_code == 401

    @pytest.mark.unit
    async def test_protected_invalid_token(self, async_client):
        """401 — token JWT inválido."""
        resp = await async_client.get(
            "/api/pedidos/some-id",
            headers={"Authorization": "Bearer garbage.token.here"},
        )
        assert resp.status_code == 401

    @pytest.mark.unit
    async def test_protected_valid_token(self, async_client, auth_headers):
        """200 — token válido pasa y se proxea al order-service."""
        order = {"id": "ord-1", "status": "pending", "total": 25000}
        mock = make_mock_client({"get": make_mock_response(200, order)})
        with patch("httpx.AsyncClient", return_value=mock):
            resp = await async_client.get("/api/pedidos/ord-1", headers=auth_headers)
        assert resp.status_code == 200


# ═══════════════════════════════════════════════════════════════════════════════
# Pedidos (requieren auth)
# ═══════════════════════════════════════════════════════════════════════════════

class TestOrdersProxy:

    @pytest.mark.unit
    async def test_create_order_no_auth(self, async_client):
        """401 — crear pedido sin token."""
        resp = await async_client.post(
            "/api/pedidos",
            json={"items": [{"product_id": "p1", "quantity": 1, "unit_price": 5000}]},
        )
        assert resp.status_code == 401

    @pytest.mark.unit
    async def test_create_order_with_auth(self, async_client, auth_headers):
        """201 — token válido, order proxeado al order-service."""
        order = {"id": "ord-new", "status": "pending", "total": 5000}
        mock = make_mock_client({"post": make_mock_response(200, order)})
        with patch("httpx.AsyncClient", return_value=mock):
            resp = await async_client.post(
                "/api/pedidos",
                json={"items": [{"product_id": "p1", "quantity": 1, "unit_price": 5000}]},
                headers=auth_headers,
            )
        assert resp.status_code == 201

    @pytest.mark.unit
    async def test_get_order_with_auth(self, async_client, auth_headers):
        """200 — consultar pedido con token."""
        order = {"id": "ord-1", "status": "pending"}
        mock = make_mock_client({"get": make_mock_response(200, order)})
        with patch("httpx.AsyncClient", return_value=mock):
            resp = await async_client.get("/api/pedidos/ord-1", headers=auth_headers)
        assert resp.status_code == 200


# ═══════════════════════════════════════════════════════════════════════════════
# Pagos (requieren auth)
# ═══════════════════════════════════════════════════════════════════════════════

class TestPaymentsProxy:

    @pytest.mark.unit
    async def test_create_transaction_no_auth(self, async_client):
        """401 — sin token."""
        resp = await async_client.post(
            "/api/pagos/transactions",
            json={"order_id": "ord-1", "amount": 50000, "payment_method": "card"},
        )
        assert resp.status_code == 401

    @pytest.mark.unit
    async def test_create_transaction_with_auth(self, async_client, auth_headers):
        """201 — proxeado al payment-service."""
        tx = {"id": "tx-1", "status": "pending", "amount": 50000}
        mock = make_mock_client({"post": make_mock_response(200, tx)})
        with patch("httpx.AsyncClient", return_value=mock):
            resp = await async_client.post(
                "/api/pagos/transactions",
                json={"order_id": "ord-1", "amount": 50000, "payment_method": "card"},
                headers=auth_headers,
            )
        assert resp.status_code == 200

    @pytest.mark.unit
    async def test_get_transaction_with_auth(self, async_client, auth_headers):
        """200 — consultar transacción con token."""
        tx = {"id": "tx-1", "status": "completed"}
        mock = make_mock_client({"get": make_mock_response(200, tx)})
        with patch("httpx.AsyncClient", return_value=mock):
            resp = await async_client.get("/api/pagos/transactions/tx-1", headers=auth_headers)
        assert resp.status_code == 200

    @pytest.mark.unit
    async def test_get_transaction_no_auth(self, async_client):
        """401 — sin token."""
        resp = await async_client.get("/api/pagos/transactions/tx-1")
        assert resp.status_code == 401


# ═══════════════════════════════════════════════════════════════════════════════
# Errores de red → 502
# ═══════════════════════════════════════════════════════════════════════════════

class TestNetworkErrors:

    @pytest.mark.unit
    async def test_upstream_unreachable_returns_503(self, async_client):
        """503 — servicio downstream no disponible (ConnectError)."""
        import httpx
        mock = make_mock_client()
        mock.get.side_effect = httpx.ConnectError("Connection refused")
        with patch("httpx.AsyncClient", return_value=mock):
            resp = await async_client.get("/api/productos")
        assert resp.status_code == 503

    @pytest.mark.unit
    async def test_upstream_timeout_returns_502(self, async_client):
        """502 — timeout en servicio downstream."""
        import httpx
        mock = make_mock_client()
        mock.get.side_effect = httpx.TimeoutException("Timed out")
        with patch("httpx.AsyncClient", return_value=mock):
            resp = await async_client.get("/api/productos")
        assert resp.status_code == 502
