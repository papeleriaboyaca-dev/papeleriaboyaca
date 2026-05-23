"""
Smoke tests contra el stack de contenedores en modo producción.
Requiere que los contenedores estén corriendo:
  docker compose -f deploy/docker-compose.yml --env-file deploy/.env up -d

Ejecutar: pytest tests_smoke/ -v

Nota: Para que TestAuth pase completamente, los usuarios de prueba deben
      existir en Supabase con email confirmado. Si el rate-limit de Supabase
      lo impide, los tests que dependen de `registered` se saltan
      automáticamente.
"""
import pytest
import httpx
import uuid
import os

GW   = os.getenv("GATEWAY_URL",  "http://localhost:8083")
ID   = os.getenv("IDENTITY_URL", "http://localhost:8004")
CAT  = os.getenv("CATALOG_URL",  "http://localhost:8002")
ORD  = os.getenv("ORDER_URL",    "http://localhost:8003")
PAY  = os.getenv("PAYMENT_URL",  "http://localhost:8005")

# Usuario pre-existente y confirmado en Supabase (creado en el primer smoke run)
SMOKE_EMAIL    = os.getenv("SMOKE_EMAIL",    "smoke_ccf47e1e@papeleria.com")
SMOKE_PASSWORD = os.getenv("SMOKE_PASSWORD", "SmokePass123!")

INTERNAL_SECRET = os.getenv("INTERNAL_API_SECRET", "")
_INT_HEADERS = {"X-Internal-Auth": INTERNAL_SECRET} if INTERNAL_SECRET else {}

TIMEOUT = 10

# Servicios internos — todas las rutas requieren X-Internal-Auth (excepto /health)
_INTERNAL_BASES = (ID, CAT, ORD, PAY)


def _maybe_add_internal(url: str, kw: dict) -> None:
    if _INT_HEADERS and any(url.startswith(b) for b in _INTERNAL_BASES):
        merged = {**_INT_HEADERS, **kw.get("headers", {})}
        kw["headers"] = merged


def get(url, **kw):
    _maybe_add_internal(url, kw)
    return httpx.get(url, timeout=TIMEOUT, follow_redirects=True, **kw)

def post(url, **kw):
    _maybe_add_internal(url, kw)
    return httpx.post(url, timeout=TIMEOUT, **kw)

def put(url, **kw):
    _maybe_add_internal(url, kw)
    return httpx.put(url, timeout=TIMEOUT, **kw)


# ═══════════════════════════════════════════════════════════════════════════════
# Health — todos los servicios deben responder
# ═══════════════════════════════════════════════════════════════════════════════

class TestHealth:

    def test_gateway_health(self):
        r = get(f"{GW}/health")
        assert r.status_code == 200
        assert r.json().get("status") in ("ok", "healthy")

    def test_identity_health(self):
        r = get(f"{ID}/health")
        assert r.status_code == 200
        assert r.json()["status"] == "ok"

    def test_catalog_health(self):
        r = get(f"{CAT}/health")
        assert r.status_code == 200
        assert r.json()["status"] == "ok"

    def test_order_health(self):
        r = get(f"{ORD}/health")
        assert r.status_code == 200
        assert r.json()["status"] == "ok"

    def test_payment_health(self):
        r = get(f"{PAY}/health")
        assert r.status_code == 200
        assert r.json()["status"] == "ok"


# ═══════════════════════════════════════════════════════════════════════════════
# Auth — registro, login, refresh, validación de token
# ═══════════════════════════════════════════════════════════════════════════════

class TestAuth:

    @pytest.fixture(scope="class")
    def tokens(self):
        """Login con el usuario de smoke pre-existente y confirmado en Supabase."""
        r = post(f"{GW}/api/auth/login", json={
            "email": SMOKE_EMAIL,
            "password": SMOKE_PASSWORD,
        })
        assert r.status_code == 200, (
            f"Login falló ({r.status_code}). "
            "Verifica que el usuario exista y tenga email confirmado en Supabase."
        )
        return r.json()

    def test_login_returns_tokens(self, tokens):
        assert "access_token" in tokens
        assert "refresh_token" in tokens
        assert tokens["token_type"] == "bearer"
        assert tokens["expires_in"] > 0

    def test_login_wrong_password_401(self):
        r = post(f"{GW}/api/auth/login", json={
            "email": SMOKE_EMAIL,
            "password": "WrongPass999",
        })
        assert r.status_code == 401

    def test_login_nonexistent_user_401(self):
        r = post(f"{GW}/api/auth/login", json={
            "email": "ghost@papeleria.com",
            "password": "AnyPass123",
        })
        assert r.status_code == 401

    def test_invalid_token_rejected_by_gateway(self):
        r = post(f"{GW}/api/pagos/transactions",
                 headers={"Authorization": "Bearer garbage.token.here"}, json={})
        assert r.status_code == 401

    def test_missing_token_rejected_by_gateway(self):
        r = post(f"{GW}/api/pagos/transactions", json={})
        assert r.status_code == 401

    def test_refresh_token(self, tokens):
        r = post(f"{GW}/api/auth/refresh", json={"token": tokens["refresh_token"]})
        assert r.status_code == 200
        body = r.json()
        assert "access_token" in body
        assert "refresh_token" in body

    def test_valid_supabase_token_passes_gateway(self, tokens):
        """Un token Supabase válido no es rechazado por el gateway."""
        r = get(f"{GW}/api/pedidos/00000000-0000-0000-0000-000000000001",
                headers={"Authorization": f"Bearer {tokens['access_token']}"})
        assert r.status_code != 401, f"Token válido rechazado: {r.text}"

    def test_register_and_duplicate_rejected(self):
        """Registrar un usuario nuevo → 200; intentar de nuevo → 400."""
        uid = uuid.uuid4().hex[:8]
        payload = {
            "email": f"dup_{uid}@papeleria.com",
            "password": "DupPass123!",
            "first_name": "Dup",
            "last_name": "Test",
        }
        r1 = post(f"{GW}/api/auth/register", json=payload)
        # Puede fallar por rate-limit de Supabase (400 con "rate limit")
        if r1.status_code == 400 and "rate limit" in r1.text.lower():
            pytest.skip("Supabase email rate limit — omitiendo test de registro")
        assert r1.status_code == 200, f"Primer registro falló: {r1.text}"
        r2 = post(f"{GW}/api/auth/register", json=payload)
        assert r2.status_code == 400
        detail = r2.json().get("detail", "")
        detail_str = detail if isinstance(detail, str) else str(detail)
        assert "already registered" in detail_str.lower()


# ═══════════════════════════════════════════════════════════════════════════════
# Catálogo — CRUD de productos (directo al servicio)
# ═══════════════════════════════════════════════════════════════════════════════

class TestCatalog:

    @pytest.fixture(scope="class")
    def category_id(self):
        """Usa la primera categoría existente en el catálogo."""
        r = get(f"{CAT}/categories")
        assert r.status_code == 200 and len(r.json()) > 0, "No hay categorías"
        return r.json()[0]["id"]

    @pytest.fixture(scope="class")
    def product_id(self, category_id):
        sku = f"SKU-SMOKE-{uuid.uuid4().hex[:6].upper()}"
        r = post(f"{CAT}/products", json={
            "name": "Cuaderno Smoke Test",
            "description": "Cuaderno de prueba automatizada",
            "price": 4500.0,
            "stock": 100,
            "category_id": category_id,
            "sku": sku,
        })
        assert r.status_code in (200, 201), f"Create product failed: {r.text}"
        return r.json()["id"]

    def test_list_products(self):
        r = get(f"{CAT}/products")
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_list_categories(self):
        r = get(f"{CAT}/categories")
        assert r.status_code == 200
        assert len(r.json()) > 0

    def test_get_product(self, product_id):
        r = get(f"{CAT}/products/{product_id}")
        assert r.status_code == 200
        body = r.json()
        assert body["id"] == product_id
        assert body["name"] == "Cuaderno Smoke Test"

    def test_update_product_price(self, product_id):
        r = put(f"{CAT}/products/{product_id}", json={"price": 5000.0})
        assert r.status_code == 200
        assert r.json()["price"] == 5000.0

    def test_get_nonexistent_product_404(self):
        r = get(f"{CAT}/products/00000000-0000-0000-0000-000000000000")
        assert r.status_code == 404

    def test_catalog_via_gateway(self):
        r = get(f"{GW}/api/productos")
        assert r.status_code == 200
        assert isinstance(r.json(), list)


# ═══════════════════════════════════════════════════════════════════════════════
# Pedidos — crear y consultar (directo al servicio)
# ═══════════════════════════════════════════════════════════════════════════════

class TestOrders:

    # Must be a real user in identity_service.users (cliente@papeleria.com seed)
    _USER_ID = "4894e337-a177-47c0-b7d2-1461181f6da0"

    @pytest.fixture(scope="class")
    def product_id(self):
        """Get a real product ID and ensure it has sufficient stock."""
        r = get(f"{CAT}/products")
        assert r.status_code == 200 and r.json(), "No products in catalog"
        pid = r.json()[0]["id"]
        put(f"{CAT}/products/{pid}", json={"stock": 200})
        return pid

    @pytest.fixture(scope="class")
    def order_id(self, product_id):
        r = post(
            f"{ORD}/orders",
            params={"user_id": self._USER_ID},
            json={
                "items": [
                    {"product_id": product_id, "quantity": 2, "unit_price": 4500.0}
                ],
            },
        )
        assert r.status_code in (200, 201), f"Create order failed: {r.text}"
        return r.json()["id"]

    def test_create_order(self, order_id):
        assert order_id is not None

    def test_get_order(self, order_id):
        r = get(f"{ORD}/orders/{order_id}", params={"user_id": self._USER_ID})
        assert r.status_code == 200
        assert r.json()["id"] == order_id

    def test_list_orders(self):
        r = get(f"{ORD}/orders", params={"user_id": self._USER_ID})
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_get_nonexistent_order_404(self):
        r = get(f"{ORD}/orders/00000000-0000-0000-0000-000000000000",
                params={"user_id": self._USER_ID})
        assert r.status_code == 404


# ═══════════════════════════════════════════════════════════════════════════════
# Pagos — endpoints básicos (directo al servicio)
# ═══════════════════════════════════════════════════════════════════════════════

class TestPayments:

    def test_get_nonexistent_transaction_404(self):
        r = get(f"{PAY}/payments/transactions/00000000-0000-0000-0000-000000000000")
        assert r.status_code == 404

    def test_wompi_webhook_requires_signature(self):
        """Sin header X-Event-Checksum → 401."""
        r = post(f"{PAY}/payments/webhooks/wompi", json={})
        assert r.status_code == 401

    def test_create_transaction_requires_order(self):
        """Crear transacción sin body válido → 422."""
        r = post(f"{PAY}/payments/transactions", json={})
        assert r.status_code == 422


# ═══════════════════════════════════════════════════════════════════════════════
# Wompi — flujo real contra el sandbox
# ═══════════════════════════════════════════════════════════════════════════════

class TestWompiFlow:

    @pytest.fixture(scope="class")
    def auth_header(self):
        r = post(f"{GW}/api/auth/login", json={
            "email": SMOKE_EMAIL, "password": SMOKE_PASSWORD,
        })
        assert r.status_code == 200
        return {"Authorization": f"Bearer {r.json()['access_token']}"}

    @pytest.fixture(scope="class")
    def order_and_transaction(self, auth_header):
        """Crea un pedido y una transacción local para el flujo de pago."""
        products = get(f"{CAT}/products").json()
        assert products, "No hay productos en el catálogo"
        pid = products[0]["id"]
        put(f"{CAT}/products/{pid}", json={"stock": 50})

        order = post(f"{GW}/api/pedidos",
                     json={"items": [{"product_id": pid, "quantity": 1, "unit_price": 5000.0}]},
                     headers=auth_header)
        assert order.status_code in (200, 201), f"Create order failed: {order.text}"
        order_id = order.json()["id"]

        txn = post(f"{GW}/api/pagos/transactions",
                   json={"order_id": order_id, "amount": 5000.0, "payment_method": "nequi"},
                   headers=auth_header)
        assert txn.status_code in (200, 201), f"Create transaction failed: {txn.text}"

        return {"order_id": order_id, "transaction_id": txn.json()["id"]}

    def test_transaction_starts_pending(self, order_and_transaction, auth_header):
        tid = order_and_transaction["transaction_id"]
        r = get(f"{GW}/api/pagos/transactions/{tid}", headers=auth_header)
        assert r.status_code == 200
        assert r.json()["status"] == "pending"

    def test_wompi_checkout_nequi(self, order_and_transaction, auth_header):
        """Llama al sandbox de Wompi con NEQUI — verifica que la integración responda."""
        tid = order_and_transaction["transaction_id"]
        r = post(f"{GW}/api/pagos/checkout",
                 json={
                     "transaction_id": tid,
                     "customer_email": SMOKE_EMAIL,
                     "payment_method_type": "NEQUI",
                     "phone_number": "3107654321",
                 },
                 headers=auth_header)
        assert r.status_code == 200, f"Wompi checkout falló: {r.text}"
        body = r.json()
        assert "wompi_transaction_id" in body, f"Sin wompi_transaction_id: {body}"
        assert body["wompi_transaction_id"] is not None
        assert body["wompi_status"] == "PENDING"

    def test_transaction_moves_to_processing(self, order_and_transaction, auth_header):
        """Después del checkout, la transacción local debe estar en 'processing'."""
        tid = order_and_transaction["transaction_id"]
        r = get(f"{GW}/api/pagos/transactions/{tid}", headers=auth_header)
        assert r.status_code == 200
        assert r.json()["status"] == "processing", f"Status inesperado: {r.json()['status']}"
        assert r.json()["wompi_reference"] is not None


# ═══════════════════════════════════════════════════════════════════════════════
# API Gateway — proxy y auth con token Supabase real
# ═══════════════════════════════════════════════════════════════════════════════

class TestGatewayProxy:

    @pytest.fixture(scope="class")
    def auth_header(self):
        login = post(f"{GW}/api/auth/login", json={
            "email": SMOKE_EMAIL,
            "password": SMOKE_PASSWORD,
        })
        assert login.status_code == 200, f"Login falló: {login.text}"
        return {"Authorization": f"Bearer {login.json()['access_token']}"}

    def test_catalog_list_via_gateway_no_auth(self):
        r = get(f"{GW}/api/productos")
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_payment_requires_auth_via_gateway(self):
        r = post(f"{GW}/api/pagos/transactions", json={})
        assert r.status_code == 401

    def test_order_create_with_auth_via_gateway(self, auth_header):
        r = post(
            f"{GW}/api/pedidos",
            json={
                "user_id": "00000000-0000-0000-0000-000000000001",
                "items": [{"product_id": "00000000-0000-0000-0000-000000000001",
                            "quantity": 1, "unit_price": 4500.0}],
            },
            headers=auth_header,
        )
        # 401 sería fallo del gateway; errores del upstream (4xx/5xx) son aceptables
        assert r.status_code != 401, f"Token válido rechazado por el gateway: {r.text}"

    def test_order_get_with_auth_via_gateway(self, auth_header):
        r = get(f"{GW}/api/pedidos/00000000-0000-0000-0000-000000000001",
                headers=auth_header)
        assert r.status_code != 401

    def test_get_me_returns_user_profile(self, auth_header):
        r = get(f"{GW}/api/users/me", headers=auth_header)
        assert r.status_code == 200, f"GET /api/users/me falló: {r.text}"
        body = r.json()
        assert "email" in body
        assert "first_name" in body
        assert "last_name" in body
        assert body["email"] == SMOKE_EMAIL

    def test_get_me_without_token_401(self):
        r = get(f"{GW}/api/users/me")
        assert r.status_code == 401

    def test_update_me(self, auth_header):
        r = put(f"{GW}/api/users/me",
                json={"city": "Tunja", "phone": "3101234567"},
                headers=auth_header)
        assert r.status_code == 200, f"PUT /api/users/me falló: {r.text}"
        body = r.json()
        assert body["city"] == "Tunja"
        assert body["phone"] == "3101234567"

    def test_catalog_filters_via_gateway(self):
        r = get(f"{GW}/api/productos", params={"sort_by": "price_asc", "limit": 5})
        assert r.status_code == 200
        products = r.json()
        if len(products) >= 2:
            assert products[0]["price"] <= products[-1]["price"]

    def test_catalog_search_via_gateway(self):
        r = get(f"{GW}/api/productos", params={"q": "cuaderno"})
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_shipping_address_crud(self, auth_header):
        r = post(f"{GW}/api/addresses",
                 json={"address_line1": "Calle 10 #5-20",
                       "city": "Tunja", "postal_code": "150001"},
                 headers=auth_header)
        assert r.status_code in (200, 201), f"Create address failed: {r.text}"
        addr_id = r.json()["id"]

        r2 = get(f"{GW}/api/addresses", headers=auth_header)
        assert r2.status_code == 200
        ids = [a["id"] for a in r2.json()]
        assert addr_id in ids

    def test_transaction_history_via_gateway(self, auth_header):
        r = get(f"{GW}/api/pagos/transactions", headers=auth_header)
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_cancel_order_pending_allowed(self, auth_header):
        products = get(f"{CAT}/products").json()
        if not products:
            pytest.skip("No products available")
        product_id = products[0]["id"]
        put(f"{CAT}/products/{product_id}", json={"stock": 50})

        # create a fresh order
        login_data = post(f"{GW}/api/auth/login",
                          json={"email": SMOKE_EMAIL, "password": SMOKE_PASSWORD}).json()
        token = login_data["access_token"]
        h = {"Authorization": f"Bearer {token}"}

        r = post(f"{GW}/api/pedidos",
                 json={"items": [{"product_id": product_id,
                                  "quantity": 1, "unit_price": 100.0}]},
                 headers=h)
        assert r.status_code in (200, 201), f"Create order failed: {r.text}"
        order_id = r.json()["id"]

        rc = post(f"{GW}/api/pedidos/{order_id}/cancel", headers=h)
        assert rc.status_code == 200, f"Cancel failed: {rc.text}"
        assert rc.json()["status"] == "cancelled"

    def test_admin_protected_endpoint_rejected_for_cliente(self, auth_header):
        r = post(f"{GW}/api/categorias",
                 json={"name": "Test", "slug": "test-cat"},
                 headers=auth_header)
        assert r.status_code == 403, f"Expected 403 for CLIENTE, got {r.status_code}"
