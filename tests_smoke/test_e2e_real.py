"""
Test E2E — Escenario real de uso del sistema.

Simula tres actores:
  • CLIENTE    → flujo completo de compra a través del API Gateway
  • ADMIN      → gestión de catálogo y pedidos directo a los servicios internos
  • SUPERADMIN → gestión global de inventario, precios y cancelaciones forzadas

Por qué admin/superadmin van directo a los servicios:
  Los tokens Supabase incluyen `role: "authenticated"` a nivel raíz del JWT,
  pero no la claim `user_role`. El gateway bloquea con 403 cualquier ruta que
  requiera ADMIN/SUPERADMIN (incluido si el usuario es admin real). En
  producción el panel de administración se conecta directamente a los servicios
  internos (red privada Docker/VPC). El test refleja esa arquitectura real.

Requiere contenedores corriendo:
  docker compose -f deploy/docker-compose.yml --env-file deploy/.env up -d

Ejecutar:
  pytest tests_smoke/test_e2e_real.py -v
"""
import pytest
import httpx
import uuid
import os

GW  = os.getenv("GATEWAY_URL",  "http://localhost:8083")
CAT = os.getenv("CATALOG_URL",  "http://localhost:8002")
ORD = os.getenv("ORDER_URL",    "http://localhost:8003")
PAY = os.getenv("PAYMENT_URL",  "http://localhost:8005")

CLIENTE_EMAIL    = os.getenv("SMOKE_EMAIL",    "smoke_ccf47e1e@papeleria.com")
CLIENTE_PASSWORD = os.getenv("SMOKE_PASSWORD", "SmokePass123!")

# UUID del usuario seeded en identity_service.users (cliente@papeleria.com)
SEED_USER_ID = "4894e337-a177-47c0-b7d2-1461181f6da0"

TIMEOUT = 15


def get(url, **kw):
    return httpx.get(url, timeout=TIMEOUT, follow_redirects=True, **kw)

def post(url, **kw):
    return httpx.post(url, timeout=TIMEOUT, **kw)

def put(url, **kw):
    return httpx.put(url, timeout=TIMEOUT, **kw)

def delete(url, **kw):
    return httpx.delete(url, timeout=TIMEOUT, **kw)


# ═══════════════════════════════════════════════════════════════════════════════
# ESCENARIO 1 — CLIENTE: jornada completa de compra (todo a través del gateway)
# ═══════════════════════════════════════════════════════════════════════════════

class TestEscenarioCliente:
    """
    Juan Cliente entra a la tienda, navega el catálogo, elige un producto,
    registra su dirección, hace un pedido y paga con Nequi (sandbox Wompi).
    Luego hace un segundo pedido que cancela. Finalmente revisa su historial
    de pagos y cierra sesión.
    """

    @pytest.fixture(scope="class")
    def session(self):
        """Autentica al cliente y devuelve headers + datos de sesión."""
        r = post(f"{GW}/api/auth/login", json={
            "email": CLIENTE_EMAIL, "password": CLIENTE_PASSWORD,
        })
        assert r.status_code == 200, f"Login cliente falló: {r.text}"
        data = r.json()
        return {
            "headers": {"Authorization": f"Bearer {data['access_token']}"},
            "refresh_token": data["refresh_token"],
        }

    # ── 1. Perfil ──────────────────────────────────────────────────────────────

    def test_01_ver_perfil(self, session):
        r = get(f"{GW}/api/users/me", headers=session["headers"])
        assert r.status_code == 200, r.text
        body = r.json()
        assert "email" in body and "first_name" in body
        assert body["email"] == CLIENTE_EMAIL

    def test_02_actualizar_perfil(self, session):
        r = put(f"{GW}/api/users/me",
                json={"city": "Tunja", "phone": "3114567890"},
                headers=session["headers"])
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["city"] == "Tunja"
        assert body["phone"] == "3114567890"

    # ── 2. Catálogo (público, sin token) ──────────────────────────────────────

    def test_03_listar_productos_publico(self):
        r = get(f"{GW}/api/productos")
        assert r.status_code == 200
        assert isinstance(r.json(), list) and len(r.json()) > 0

    def test_04_buscar_productos(self):
        r = get(f"{GW}/api/productos", params={"q": "cuaderno"})
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_05_filtrar_por_precio_ascendente(self):
        r = get(f"{GW}/api/productos", params={"sort_by": "price_asc", "limit": 5})
        assert r.status_code == 200
        products = r.json()
        if len(products) >= 2:
            assert products[0]["price"] <= products[-1]["price"]

    def test_06_listar_categorias(self):
        r = get(f"{GW}/api/categorias")
        assert r.status_code == 200 and len(r.json()) > 0

    def test_07_ver_detalle_producto(self):
        products = get(f"{GW}/api/productos").json()
        assert products, "No hay productos"
        r = get(f"{GW}/api/productos/{products[0]['id']}")
        assert r.status_code == 200
        assert r.json()["id"] == products[0]["id"]

    # ── 3. Dirección de envío ─────────────────────────────────────────────────

    def test_08_registrar_direccion_envio(self, session):
        r = post(f"{GW}/api/addresses",
                 json={"address_line1": "Calle 20 #8-15",
                       "city": "Tunja",
                       "postal_code": "150001"},
                 headers=session["headers"])
        assert r.status_code in (200, 201), r.text
        session["address_id"] = r.json()["id"]

    def test_09_listar_mis_direcciones(self, session):
        r = get(f"{GW}/api/addresses", headers=session["headers"])
        assert r.status_code == 200
        assert session["address_id"] in [a["id"] for a in r.json()]

    # ── 4. Pedido ─────────────────────────────────────────────────────────────

    def test_10_crear_pedido(self, session):
        products = get(f"{GW}/api/productos").json()
        assert products
        pid = products[0]["id"]
        put(f"{CAT}/products/{pid}", json={"stock": 100})  # garantiza stock

        r = post(f"{GW}/api/pedidos",
                 json={"items": [{"product_id": pid,
                                  "quantity": 2,
                                  "unit_price": products[0]["price"]}]},
                 headers=session["headers"])
        assert r.status_code in (200, 201), r.text
        order = r.json()
        assert order["status"] == "pending"
        session["order_id"]   = order["id"]
        session["product_id"] = pid

    def test_11_ver_pedido_creado(self, session):
        r = get(f"{GW}/api/pedidos/{session['order_id']}",
                headers=session["headers"])
        assert r.status_code == 200
        assert r.json()["id"] == session["order_id"]

    def test_12_listar_mis_pedidos(self, session):
        r = get(f"{GW}/api/pedidos", headers=session["headers"])
        assert r.status_code == 200
        assert session["order_id"] in [o["id"] for o in r.json()]

    def test_13_stock_reducido_tras_pedido(self, session):
        """Stock debe haber bajado 2 unidades después de crear el pedido."""
        r = get(f"{CAT}/products/{session['product_id']}")
        assert r.status_code == 200
        assert r.json()["stock"] <= 98  # pusimos 100, pedimos 2

    # ── 5. Pago con Wompi ─────────────────────────────────────────────────────

    def test_14_crear_transaccion_pago(self, session):
        r = post(f"{GW}/api/pagos/transactions",
                 json={"order_id": session["order_id"],
                       "amount": 9000.0,
                       "payment_method": "nequi"},
                 headers=session["headers"])
        assert r.status_code in (200, 201), r.text
        assert r.json()["status"] == "pending"
        session["transaction_id"] = r.json()["id"]

    def test_15_estado_inicial_pending(self, session):
        r = get(f"{GW}/api/pagos/transactions/{session['transaction_id']}",
                headers=session["headers"])
        assert r.status_code == 200
        assert r.json()["status"] == "pending"

    def test_16_checkout_wompi_nequi(self, session):
        """Llama al sandbox real de Wompi con método NEQUI."""
        r = post(f"{GW}/api/pagos/checkout",
                 json={"transaction_id": session["transaction_id"],
                       "customer_email": CLIENTE_EMAIL,
                       "payment_method_type": "NEQUI",
                       "phone_number": "3107654321"},
                 headers=session["headers"])
        assert r.status_code == 200, f"Wompi checkout falló: {r.text}"
        body = r.json()
        assert body.get("wompi_transaction_id") is not None
        assert body["wompi_status"] == "PENDING"
        session["wompi_txn_id"] = body["wompi_transaction_id"]

    def test_17_transaccion_pasa_a_processing(self, session):
        r = get(f"{GW}/api/pagos/transactions/{session['transaction_id']}",
                headers=session["headers"])
        assert r.status_code == 200
        body = r.json()
        assert body["status"] == "processing", f"Estado: {body['status']}"
        assert body["wompi_reference"] is not None

    def test_18_historial_de_pagos(self, session):
        r = get(f"{GW}/api/pagos/transactions", headers=session["headers"])
        assert r.status_code == 200
        assert session["transaction_id"] in [t["id"] for t in r.json()]

    # ── 6. Cancelar segundo pedido ────────────────────────────────────────────

    def test_19_crear_y_cancelar_pedido_pending(self, session):
        pid = session["product_id"]
        put(f"{CAT}/products/{pid}", json={"stock": 50})
        r = post(f"{GW}/api/pedidos",
                 json={"items": [{"product_id": pid,
                                  "quantity": 1,
                                  "unit_price": 5000.0}]},
                 headers=session["headers"])
        assert r.status_code in (200, 201), r.text
        cid = r.json()["id"]

        rc = post(f"{GW}/api/pedidos/{cid}/cancel", headers=session["headers"])
        assert rc.status_code == 200, rc.text
        assert rc.json()["status"] == "cancelled"

    def test_20_stock_restaurado_tras_cancelacion(self, session):
        r = get(f"{CAT}/products/{session['product_id']}")
        assert r.status_code == 200
        assert r.json()["stock"] >= 50

    # ── 7. Cerrar sesión ──────────────────────────────────────────────────────

    def test_21_logout(self, session):
        r = post(f"{GW}/api/auth/logout", headers=session["headers"])
        assert r.status_code in (200, 204), r.text


# ═══════════════════════════════════════════════════════════════════════════════
# ESCENARIO 2 — ADMIN: gestión de catálogo y pedidos (directo a los servicios)
# ═══════════════════════════════════════════════════════════════════════════════

class TestEscenarioAdmin:
    """
    María Admin gestiona el catálogo: crea una categoría y productos para una
    nueva línea de papelería escolar, actualiza precios e inventario, revisa
    pedidos y actualiza el estado de uno hasta 'delivered'.
    """

    @pytest.fixture(scope="class")
    def categoria(self):
        uid = uuid.uuid4().hex[:6]
        r = post(f"{CAT}/categories", json={
            "name": f"Material Escolar Premium {uid}",
            "description": "Útiles escolares de alta calidad",
            "slug": f"escolar-{uid}",
        })
        assert r.status_code in (200, 201), f"Crear categoría falló: {r.text}"
        return r.json()["id"]

    @pytest.fixture(scope="class")
    def productos(self, categoria):
        prefix = uuid.uuid4().hex[:4].upper()
        ids = []
        articulos = [
            ("Lápiz HB Premium",    800.0,  500),
            ("Borrador Profesional", 1200.0, 300),
            ("Regla 30cm Graduada", 2500.0, 200),
        ]
        for i, (name, price, stock) in enumerate(articulos):
            r = post(f"{CAT}/products", json={
                "name": name,
                "description": f"Producto escolar premium #{i+1}",
                "price": price,
                "stock": stock,
                "category_id": categoria,
                "sku": f"ESC-{prefix}-{i:02d}",
            })
            assert r.status_code in (200, 201), f"Crear '{name}' falló: {r.text}"
            ids.append(r.json()["id"])
        return ids

    @pytest.fixture(scope="class")
    def pedido(self, productos):
        """Pedido de prueba para que admin lo gestione."""
        pid = productos[0]
        put(f"{CAT}/products/{pid}", json={"stock": 100})
        r = post(f"{ORD}/orders",
                 params={"user_id": SEED_USER_ID},
                 json={"items": [{"product_id": pid,
                                  "quantity": 3,
                                  "unit_price": 800.0}]})
        assert r.status_code in (200, 201), r.text
        return r.json()["id"]

    # ── Gestión de catálogo ───────────────────────────────────────────────────

    def test_01_categoria_visible_en_catalogo(self, categoria):
        ids = [c["id"] for c in get(f"{CAT}/categories").json()]
        assert categoria in ids

    def test_02_productos_visibles_en_catalogo(self, productos):
        catalog_ids = [p["id"] for p in get(f"{CAT}/products").json()]
        for pid in productos:
            assert pid in catalog_ids, f"Producto {pid} no aparece"

    def test_03_actualizar_precio(self, productos):
        r = put(f"{CAT}/products/{productos[0]}", json={"price": 950.0})
        assert r.status_code == 200
        assert r.json()["price"] == 950.0

    def test_04_actualizar_stock(self, productos):
        r = put(f"{CAT}/products/{productos[1]}", json={"stock": 500})
        assert r.status_code == 200
        assert r.json()["stock"] == 500

    def test_05_filtrar_por_categoria(self, categoria, productos):
        r = get(f"{CAT}/products", params={"category_id": categoria})
        assert r.status_code == 200
        found = [p["id"] for p in r.json()]
        for pid in productos:
            assert pid in found

    def test_06_precio_actualizado_en_detalle(self, productos):
        r = get(f"{CAT}/products/{productos[0]}")
        assert r.status_code == 200
        assert r.json()["price"] == 950.0

    # ── Gestión de pedidos ────────────────────────────────────────────────────

    def test_07_pedido_parte_en_pending(self, pedido):
        r = get(f"{ORD}/orders/{pedido}")
        assert r.status_code == 200
        assert r.json()["status"] == "pending"

    def test_08_confirmar_pedido(self, pedido):
        r = put(f"{ORD}/orders/{pedido}/status", json={"status": "confirmed"})
        assert r.status_code == 200
        assert r.json()["status"] == "confirmed"

    def test_09_marcar_como_enviado(self, pedido):
        r = put(f"{ORD}/orders/{pedido}/status", json={"status": "shipped"})
        assert r.status_code == 200
        assert r.json()["status"] == "shipped"

    def test_10_marcar_como_entregado(self, pedido):
        r = put(f"{ORD}/orders/{pedido}/status", json={"status": "delivered"})
        assert r.status_code == 200
        assert r.json()["status"] == "delivered"

    def test_11_ver_items_del_pedido(self, pedido):
        r = get(f"{ORD}/orders/{pedido}/items")
        assert r.status_code == 200
        items = r.json()["items"]
        assert len(items) > 0
        assert items[0]["quantity"] == 3

    def test_12_eliminar_producto_descatalogado(self, productos):
        """Admin da de baja la regla porque ya no la venden."""
        rid = productos[2]
        r = delete(f"{CAT}/products/{rid}")
        assert r.status_code in (200, 204), r.text
        assert get(f"{CAT}/products/{rid}").status_code == 404


# ═══════════════════════════════════════════════════════════════════════════════
# ESCENARIO 3 — SUPERADMIN: gestión global del sistema
# ═══════════════════════════════════════════════════════════════════════════════

class TestEscenarioSuperAdmin:
    """
    Carlos SuperAdmin supervisa el ecosistema: verifica salud de todos los
    microservicios, registra un producto estrella de temporada, aplica descuento
    masivo, gestiona el stock y cancela de forma forzada un pedido problemático.
    """

    @pytest.fixture(scope="class")
    def producto_estrella(self):
        cat_id = get(f"{CAT}/categories").json()[0]["id"]
        r = post(f"{CAT}/products", json={
            "name": "Kit Escolar Completo",
            "description": "Set premium: cuaderno + lápices + borrador + regla",
            "price": 45000.0,
            "stock": 1000,
            "category_id": cat_id,
            "sku": f"VIP-{uuid.uuid4().hex[:6].upper()}",
        })
        assert r.status_code in (200, 201), r.text
        return r.json()["id"]

    @pytest.fixture(scope="class")
    def pedido_problematico(self, producto_estrella):
        # No reseteamos stock: en este punto ya es 2500 (puesto por test_05)
        r = post(f"{ORD}/orders",
                 params={"user_id": SEED_USER_ID},
                 json={"items": [{"product_id": producto_estrella,
                                  "quantity": 5,
                                  "unit_price": 45000.0}]})
        assert r.status_code in (200, 201), r.text
        return r.json()["id"]

    # ── Supervisión ───────────────────────────────────────────────────────────

    def test_01_todos_los_servicios_sanos(self):
        for url, nombre in [
            (f"{GW}/health",  "api-gateway"),
            (f"{CAT}/health", "catalog-service"),
            (f"{ORD}/health", "order-service"),
            (f"{PAY}/health", "payment-service"),
        ]:
            r = get(url)
            assert r.status_code == 200, f"{nombre} no responde"
            assert r.json().get("status") in ("ok", "healthy"), r.json()

    def test_02_catalogo_tiene_datos_minimos(self):
        assert len(get(f"{CAT}/categories").json()) >= 1
        assert len(get(f"{CAT}/products").json()) >= 3

    # ── Producto de temporada ──────────────────────────────────────────────────

    def test_03_producto_estrella_creado(self, producto_estrella):
        r = get(f"{CAT}/products/{producto_estrella}")
        assert r.status_code == 200
        body = r.json()
        assert body["name"] == "Kit Escolar Completo"
        assert body["price"] == 45000.0
        assert body["stock"] == 1000

    def test_04_aplicar_descuento_temporada(self, producto_estrella):
        r = put(f"{CAT}/products/{producto_estrella}", json={"price": 38000.0})
        assert r.status_code == 200
        assert r.json()["price"] == 38000.0

    def test_05_reabastecer_inventario(self, producto_estrella):
        r = put(f"{CAT}/products/{producto_estrella}", json={"stock": 2500})
        assert r.status_code == 200
        assert r.json()["stock"] == 2500

    # ── Pedido problemático ────────────────────────────────────────────────────

    def test_06_pedido_creado_y_stock_reducido(self, producto_estrella, pedido_problematico):
        """
        El pedido de 5 unidades debe estar pending y el stock habrá bajado 5
        desde el valor que fijó test_05 (2500 → 2495).
        """
        r_pedido = get(f"{ORD}/orders/{pedido_problematico}")
        assert r_pedido.status_code == 200
        assert r_pedido.json()["status"] == "pending"

        r_stock = get(f"{CAT}/products/{producto_estrella}")
        assert r_stock.status_code == 200
        assert r_stock.json()["stock"] == 2495  # 2500 - 5

    def test_07_cancelacion_forzada_por_superadmin(self, pedido_problematico):
        """SuperAdmin cancela el pedido independientemente del owner."""
        r = post(f"{ORD}/orders/{pedido_problematico}/cancel",
                 params={"user_id": SEED_USER_ID, "is_admin": "true"})
        assert r.status_code == 200, r.text
        assert r.json()["status"] == "cancelled"

    def test_08_stock_recuperado_tras_cancelacion(self, producto_estrella):
        """Al cancelar el pedido de 5 unidades, stock vuelve de 2495 a 2500."""
        r = get(f"{CAT}/products/{producto_estrella}")
        assert r.status_code == 200
        assert r.json()["stock"] == 2500  # 2495 + 5 devueltos

    # ── Seguridad del sistema de pagos ────────────────────────────────────────

    def test_09_transaccion_inexistente_da_404(self):
        r = get(f"{PAY}/payments/transactions/00000000-0000-0000-0000-000000000000")
        assert r.status_code == 404

    def test_10_webhook_sin_firma_da_401(self):
        r = post(f"{PAY}/payments/webhooks/wompi", json={"event": "test"})
        assert r.status_code == 401

    def test_11_webhook_con_firma_invalida_da_401(self):
        r = post(f"{PAY}/payments/webhooks/wompi",
                 json={"event": "transaction.updated", "data": {}},
                 headers={"X-Event-Checksum": "firma_completamente_invalida"})
        assert r.status_code == 401

    def test_12_eliminar_producto_estrella(self, producto_estrella):
        r = delete(f"{CAT}/products/{producto_estrella}")
        assert r.status_code in (200, 204), r.text
        assert get(f"{CAT}/products/{producto_estrella}").status_code == 404


# ═══════════════════════════════════════════════════════════════════════════════
# ESCENARIO 4 — CONTROL DE ACCESO (RBAC vía Gateway)
# ═══════════════════════════════════════════════════════════════════════════════

class TestRBAC:
    """
    Verifica que el API Gateway aplica control de acceso correctamente.

    Sin token → 401. Con token de CLIENTE → 403 en rutas protegidas.
    Rutas públicas del catálogo → 200 sin auth.
    """

    @pytest.fixture(scope="class")
    def cliente_headers(self):
        r = post(f"{GW}/api/auth/login",
                 json={"email": CLIENTE_EMAIL, "password": CLIENTE_PASSWORD})
        assert r.status_code == 200, r.text
        return {"Authorization": f"Bearer {r.json()['access_token']}"}

    def test_01_rutas_auth_sin_token_dan_401(self):
        for url, method in [
            (f"{GW}/api/pedidos", "GET"),
            (f"{GW}/api/pagos/transactions", "GET"),
            (f"{GW}/api/users/me", "GET"),
        ]:
            r = (get if method == "GET" else post)(url)
            assert r.status_code == 401, \
                f"{method} {url}: esperado 401, recibido {r.status_code}"

    def test_02_token_invalido_da_401(self):
        h = {"Authorization": "Bearer token.completamente.invalido"}
        assert post(f"{GW}/api/pagos/transactions", json={}, headers=h).status_code == 401

    def test_03_cliente_no_puede_crear_producto(self, cliente_headers):
        r = post(f"{GW}/api/productos",
                 json={"name": "Hack", "price": 1.0, "stock": 1},
                 headers=cliente_headers)
        assert r.status_code == 403

    def test_04_cliente_no_puede_crear_categoria(self, cliente_headers):
        r = post(f"{GW}/api/categorias",
                 json={"name": "Hack Cat", "slug": "hack-cat"},
                 headers=cliente_headers)
        assert r.status_code == 403

    def test_05_cliente_no_puede_actualizar_producto(self, cliente_headers):
        products = get(f"{GW}/api/productos").json()
        if not products:
            pytest.skip("No hay productos")
        r = put(f"{GW}/api/productos/{products[0]['id']}",
                json={"price": 1.0}, headers=cliente_headers)
        assert r.status_code == 403

    def test_06_cliente_no_puede_eliminar_producto(self, cliente_headers):
        products = get(f"{GW}/api/productos").json()
        if not products:
            pytest.skip("No hay productos")
        r = delete(f"{GW}/api/productos/{products[0]['id']}",
                   headers=cliente_headers)
        assert r.status_code == 403

    def test_07_cliente_no_puede_cambiar_estado_pedido(self, cliente_headers):
        r = put(f"{GW}/api/pedidos/00000000-0000-0000-0000-000000000001/status",
                json={"status": "shipped"}, headers=cliente_headers)
        assert r.status_code == 403

    def test_08_catalogo_publico_sin_auth(self):
        assert get(f"{GW}/api/productos").status_code == 200
        assert get(f"{GW}/api/categorias").status_code == 200

    def test_09_token_con_firma_invalida_da_401(self):
        fake = ("eyJhbGciOiJIUzI1NiJ9"
                ".eyJzdWIiOiJmYWtlIiwicm9sZSI6ImF1dGhlbnRpY2F0ZWQifQ"
                ".firma_invalida")
        r = get(f"{GW}/api/users/me", headers={"Authorization": f"Bearer {fake}"})
        assert r.status_code == 401
