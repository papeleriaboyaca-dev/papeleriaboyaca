"""
Tests HTTP del order-service — endpoints /orders
Ejecutar: cd order-service && pytest tests/test_http_orders.py -v
"""
import pytest
from uuid import uuid4


# ═══════════════════════════════════════════════════════════════════════════════
# POST /orders
# ═══════════════════════════════════════════════════════════════════════════════

class TestCreateOrder:

    @pytest.mark.unit
    async def test_create_order_success(self, async_client, user_id, order_payload):
        resp = await async_client.post(
            "/orders",
            json=order_payload,
            params={"user_id": str(user_id)},
        )
        assert resp.status_code == 201
        body = resp.json()
        assert body["status"] == "pending_payment"
        assert body["total"] == 3000.0          # 2 × 1500 (catalog mock price)
        assert body["user_id"] == str(user_id)
        assert body["order_number"].startswith("ORD-")

    @pytest.mark.unit
    async def test_create_order_multiple_items(self, async_client, user_id):
        payload = {
            "items": [
                {"product_id": str(uuid4()), "quantity": 1, "unit_price": 1000.0},
                {"product_id": str(uuid4()), "quantity": 3, "unit_price": 500.0},
            ]
        }
        resp = await async_client.post("/orders", json=payload, params={"user_id": str(user_id)})
        assert resp.status_code == 201
        # unit_price from request is ignored; catalog mock returns 1500.0 for all products
        assert resp.json()["total"] == 6000.0   # (1 + 3) × 1500.0

    @pytest.mark.unit
    async def test_create_order_empty_items_rejected(self, async_client, user_id):
        """422 — orden sin items (min_length=1 validation)."""
        resp = await async_client.post(
            "/orders",
            json={"items": []},
            params={"user_id": str(user_id)},
        )
        assert resp.status_code == 422

    @pytest.mark.unit
    async def test_create_order_missing_user_id(self, async_client, order_payload):
        """422 — falta user_id como query param."""
        resp = await async_client.post("/orders", json=order_payload)
        assert resp.status_code == 422

    @pytest.mark.unit
    async def test_create_order_invalid_user_id(self, async_client, order_payload):
        """422 — user_id no es UUID válido."""
        resp = await async_client.post(
            "/orders",
            json=order_payload,
            params={"user_id": "not-a-uuid"},
        )
        assert resp.status_code == 422

    @pytest.mark.unit
    async def test_create_order_without_unit_price(self, async_client, user_id):
        """201 — unit_price is optional; catalog price is used instead."""
        resp = await async_client.post(
            "/orders",
            json={"items": [{"product_id": str(uuid4()), "quantity": 1}]},
            params={"user_id": str(user_id)},
        )
        assert resp.status_code == 201
        assert resp.json()["total"] == 1500.0  # catalog mock price × 1

    @pytest.mark.unit
    async def test_create_order_with_notes(self, async_client, user_id, order_payload):
        resp = await async_client.post(
            "/orders",
            json={**order_payload, "notes": "Llamar antes de entregar"},
            params={"user_id": str(user_id)},
        )
        assert resp.status_code == 201


# ═══════════════════════════════════════════════════════════════════════════════
# GET /orders/{id}
# ═══════════════════════════════════════════════════════════════════════════════

class TestGetOrder:

    @pytest.mark.unit
    async def test_get_order_success(self, async_client, user_id, created_order):
        resp = await async_client.get(
            f"/orders/{created_order['id']}",
            params={"user_id": str(user_id)},
        )
        assert resp.status_code == 200
        assert resp.json()["id"] == created_order["id"]
        assert resp.json()["order_number"] == created_order["order_number"]

    @pytest.mark.unit
    async def test_get_order_not_found(self, async_client, user_id):
        resp = await async_client.get(f"/orders/{uuid4()}", params={"user_id": str(user_id)})
        assert resp.status_code == 404

    @pytest.mark.unit
    async def test_get_order_invalid_uuid(self, async_client):
        resp = await async_client.get("/orders/not-a-uuid")
        assert resp.status_code == 422


# ═══════════════════════════════════════════════════════════════════════════════
# GET /orders?user_id=
# ═══════════════════════════════════════════════════════════════════════════════

class TestListOrders:

    @pytest.mark.unit
    async def test_list_orders_for_user(self, async_client, user_id, order_payload):
        # Crear 2 órdenes para el mismo usuario
        await async_client.post("/orders", json=order_payload, params={"user_id": str(user_id)})
        await async_client.post("/orders", json=order_payload, params={"user_id": str(user_id)})

        resp = await async_client.get("/orders", params={"user_id": str(user_id)})
        assert resp.status_code == 200
        assert len(resp.json()) == 2

    @pytest.mark.unit
    async def test_list_orders_no_orders(self, async_client):
        resp = await async_client.get("/orders", params={"user_id": str(uuid4())})
        assert resp.status_code == 200
        assert resp.json() == []

    @pytest.mark.unit
    async def test_list_orders_isolation(self, async_client, user_id, order_payload):
        """Las órdenes de un usuario no aparecen en las de otro."""
        other_user = uuid4()
        await async_client.post("/orders", json=order_payload, params={"user_id": str(user_id)})
        resp = await async_client.get("/orders", params={"user_id": str(other_user)})
        assert resp.json() == []

    @pytest.mark.unit
    async def test_list_orders_missing_user_id(self, async_client):
        """400 — falta user_id (endpoint returns 400 not 422)."""
        resp = await async_client.get("/orders")
        assert resp.status_code == 400

    @pytest.mark.unit
    async def test_list_orders_pagination(self, async_client, user_id, order_payload):
        for _ in range(5):
            await async_client.post("/orders", json=order_payload, params={"user_id": str(user_id)})
        resp = await async_client.get("/orders", params={"user_id": str(user_id), "limit": 2})
        assert len(resp.json()) == 2


# ═══════════════════════════════════════════════════════════════════════════════
# PUT /orders/{id}/status
# ═══════════════════════════════════════════════════════════════════════════════

class TestUpdateOrderStatus:

    @pytest.mark.unit
    async def test_update_status_confirmed(self, async_client, created_order):
        resp = await async_client.put(
            f"/orders/{created_order['id']}/status",
            json={"status": "confirmed"},
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "confirmed"

    @pytest.mark.parametrize("new_status", ["confirmed", "shipped", "delivered", "cancelled"])
    @pytest.mark.unit
    async def test_update_status_all_valid(self, async_client, user_id, order_payload, new_status):
        order = (await async_client.post(
            "/orders", json=order_payload, params={"user_id": str(user_id)}
        )).json()
        resp = await async_client.put(
            f"/orders/{order['id']}/status",
            json={"status": new_status},
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == new_status

    @pytest.mark.unit
    async def test_update_status_invalid(self, async_client, created_order):
        resp = await async_client.put(
            f"/orders/{created_order['id']}/status",
            json={"status": "en_camino"},   # status no permitido
        )
        assert resp.status_code == 422

    @pytest.mark.unit
    async def test_update_status_order_not_found(self, async_client):
        resp = await async_client.put(
            f"/orders/{uuid4()}/status",
            json={"status": "confirmed"},
        )
        assert resp.status_code == 404

    @pytest.mark.unit
    async def test_update_status_missing_body(self, async_client, created_order):
        resp = await async_client.put(f"/orders/{created_order['id']}/status", json={})
        assert resp.status_code == 422


# ═══════════════════════════════════════════════════════════════════════════════
# GET /orders/{id}/items
# ═══════════════════════════════════════════════════════════════════════════════

class TestGetOrderItems:

    @pytest.mark.unit
    async def test_get_items_success(self, async_client, created_order):
        resp = await async_client.get(f"/orders/{created_order['id']}/items")
        assert resp.status_code == 200
        items = resp.json()["items"]
        assert len(items) == 1
        assert items[0]["quantity"] == 2
        assert items[0]["unit_price"] == 1500.0
        assert items[0]["subtotal"] == 3000.0

    @pytest.mark.unit
    async def test_get_items_order_not_found(self, async_client):
        resp = await async_client.get(f"/orders/{uuid4()}/items")
        assert resp.status_code == 404

    @pytest.mark.unit
    async def test_get_items_multiple(self, async_client, user_id):
        payload = {
            "items": [
                {"product_id": str(uuid4()), "quantity": 1, "unit_price": 1000.0},
                {"product_id": str(uuid4()), "quantity": 2, "unit_price": 500.0},
            ]
        }
        order = (await async_client.post(
            "/orders", json=payload, params={"user_id": str(user_id)}
        )).json()
        resp = await async_client.get(f"/orders/{order['id']}/items")
        assert resp.status_code == 200
        assert len(resp.json()["items"]) == 2
