"""
Tests HTTP del catalog-service — endpoints /products y /categories
Ejecutar: cd catalog-service && pytest tests/test_http_catalog.py -v
"""
import pytest
from uuid import uuid4


# ═══════════════════════════════════════════════════════════════════════════════
# GET /categories
# ═══════════════════════════════════════════════════════════════════════════════

class TestListCategories:

    @pytest.mark.unit
    async def test_list_categories_empty(self, async_client):
        resp = await async_client.get("/categories")
        assert resp.status_code == 200
        assert resp.json() == []

    @pytest.mark.unit
    async def test_list_categories_with_data(self, async_client, sample_category):
        resp = await async_client.get("/categories")
        assert resp.status_code == 200
        body = resp.json()
        assert len(body) == 1
        assert body[0]["slug"] == sample_category.slug


# ═══════════════════════════════════════════════════════════════════════════════
# GET /categories/{id}
# ═══════════════════════════════════════════════════════════════════════════════

class TestGetCategory:

    @pytest.mark.unit
    async def test_get_category_success(self, async_client, sample_category):
        resp = await async_client.get(f"/categories/{sample_category.id}")
        assert resp.status_code == 200
        assert resp.json()["id"] == str(sample_category.id)
        assert resp.json()["name"] == sample_category.name

    @pytest.mark.unit
    async def test_get_category_not_found(self, async_client):
        resp = await async_client.get(f"/categories/{uuid4()}")
        assert resp.status_code == 404

    @pytest.mark.unit
    async def test_get_category_invalid_uuid(self, async_client):
        resp = await async_client.get("/categories/not-a-uuid")
        assert resp.status_code == 422


# ═══════════════════════════════════════════════════════════════════════════════
# POST /categories
# ═══════════════════════════════════════════════════════════════════════════════

class TestCreateCategory:

    @pytest.mark.unit
    async def test_create_category_success(self, async_client, category_payload):
        resp = await async_client.post("/categories", json=category_payload)
        assert resp.status_code == 201
        body = resp.json()
        assert body["name"] == category_payload["name"]
        assert body["slug"] == category_payload["slug"]
        assert "id" in body

    @pytest.mark.unit
    async def test_create_category_duplicate_slug(self, async_client, category_payload):
        await async_client.post("/categories", json=category_payload)
        resp = await async_client.post("/categories", json=category_payload)
        assert resp.status_code == 400
        assert "already exists" in resp.json()["detail"].lower()

    @pytest.mark.unit
    async def test_create_category_missing_name(self, async_client):
        resp = await async_client.post("/categories", json={"slug": "mi-slug"})
        assert resp.status_code == 422

    @pytest.mark.unit
    async def test_create_category_missing_slug(self, async_client):
        resp = await async_client.post("/categories", json={"name": "Mi Cat"})
        assert resp.status_code == 422

    @pytest.mark.unit
    async def test_create_category_empty_body(self, async_client):
        resp = await async_client.post("/categories", json={})
        assert resp.status_code == 422


# ═══════════════════════════════════════════════════════════════════════════════
# GET /products
# ═══════════════════════════════════════════════════════════════════════════════

class TestListProducts:

    @pytest.mark.unit
    async def test_list_products_empty(self, async_client):
        resp = await async_client.get("/products")
        assert resp.status_code == 200
        assert resp.json() == []

    @pytest.mark.unit
    async def test_list_products_with_data(self, async_client, sample_product):
        resp = await async_client.get("/products")
        assert resp.status_code == 200
        assert len(resp.json()) == 1

    @pytest.mark.unit
    async def test_list_products_pagination(self, async_client, db_session, sample_category):
        from src.infrastructure.models import Product
        for i in range(5):
            db_session.add(Product(sku=f"PAG-{i}", name=f"Producto {i}", price=100.0, stock=10, category_id=sample_category.id))
        await db_session.commit()

        resp = await async_client.get("/products", params={"skip": 0, "limit": 2})
        assert resp.status_code == 200
        assert len(resp.json()) == 2

    @pytest.mark.unit
    async def test_list_products_limit_too_large(self, async_client):
        resp = await async_client.get("/products", params={"limit": 999})
        assert resp.status_code == 422

    @pytest.mark.unit
    async def test_list_products_negative_skip(self, async_client):
        resp = await async_client.get("/products", params={"skip": -1})
        assert resp.status_code == 422


# ═══════════════════════════════════════════════════════════════════════════════
# GET /products/search
# ═══════════════════════════════════════════════════════════════════════════════

class TestSearchProducts:

    @pytest.mark.unit
    async def test_search_found(self, async_client, sample_product):
        resp = await async_client.get("/products/search", params={"q": "Lápiz"})
        assert resp.status_code == 200
        assert len(resp.json()) >= 1

    @pytest.mark.unit
    async def test_search_no_results(self, async_client, sample_product):
        resp = await async_client.get("/products/search", params={"q": "xyznotexist"})
        assert resp.status_code == 200
        assert resp.json() == []

    @pytest.mark.unit
    async def test_search_missing_query(self, async_client):
        resp = await async_client.get("/products/search")
        assert resp.status_code == 422

    @pytest.mark.unit
    async def test_search_empty_query(self, async_client):
        resp = await async_client.get("/products/search", params={"q": ""})
        assert resp.status_code == 422


# ═══════════════════════════════════════════════════════════════════════════════
# GET /products/{id}
# ═══════════════════════════════════════════════════════════════════════════════

class TestGetProduct:

    @pytest.mark.unit
    async def test_get_product_success(self, async_client, sample_product):
        resp = await async_client.get(f"/products/{sample_product.id}")
        assert resp.status_code == 200
        body = resp.json()
        assert body["id"] == str(sample_product.id)
        assert body["sku"] == sample_product.sku
        assert body["stock"] == sample_product.stock

    @pytest.mark.unit
    async def test_get_product_not_found(self, async_client):
        resp = await async_client.get(f"/products/{uuid4()}")
        assert resp.status_code == 404

    @pytest.mark.unit
    async def test_get_product_invalid_uuid(self, async_client):
        resp = await async_client.get("/products/not-a-uuid")
        assert resp.status_code == 422


# ═══════════════════════════════════════════════════════════════════════════════
# POST /products
# ═══════════════════════════════════════════════════════════════════════════════

class TestCreateProduct:

    @pytest.mark.unit
    async def test_create_product_success(self, async_client, product_payload):
        resp = await async_client.post("/products", json=product_payload)
        assert resp.status_code == 201
        body = resp.json()
        assert body["sku"] == product_payload["sku"]
        assert body["stock"] == product_payload["stock"]
        assert body["is_active"] is True

    @pytest.mark.unit
    async def test_create_product_duplicate_sku(self, async_client, product_payload):
        await async_client.post("/products", json=product_payload)
        resp = await async_client.post("/products", json=product_payload)
        assert resp.status_code == 400
        assert "already exists" in resp.json()["detail"].lower()

    @pytest.mark.unit
    async def test_create_product_invalid_category(self, async_client, product_payload):
        product_payload["category_id"] = str(uuid4())
        resp = await async_client.post("/products", json=product_payload)
        assert resp.status_code == 400
        assert "category" in resp.json()["detail"].lower()

    @pytest.mark.unit
    async def test_create_product_missing_price(self, async_client, product_payload):
        del product_payload["price"]
        resp = await async_client.post("/products", json=product_payload)
        assert resp.status_code == 422

    @pytest.mark.unit
    async def test_create_product_missing_sku(self, async_client, product_payload):
        del product_payload["sku"]
        resp = await async_client.post("/products", json=product_payload)
        assert resp.status_code == 422

    @pytest.mark.unit
    async def test_create_product_default_stock_zero(self, async_client, sample_category):
        resp = await async_client.post("/products", json={
            "sku": f"NO-STOCK-{uuid4().hex[:4]}",
            "name": "Sin stock",
            "price": 100.0,
            "category_id": str(sample_category.id),
        })
        assert resp.status_code == 201
        assert resp.json()["stock"] == 0


# ═══════════════════════════════════════════════════════════════════════════════
# PUT /products/{id}
# ═══════════════════════════════════════════════════════════════════════════════

class TestUpdateProduct:

    @pytest.mark.unit
    async def test_update_product_success(self, async_client, sample_product):
        resp = await async_client.put(
            f"/products/{sample_product.id}",
            json={"price": 999.0, "stock": 200},
        )
        assert resp.status_code == 200
        assert resp.json()["price"] == 999.0
        assert resp.json()["stock"] == 200

    @pytest.mark.unit
    async def test_update_product_partial(self, async_client, sample_product):
        """Solo se actualiza el campo enviado (exclude_unset=True)."""
        original_price = sample_product.price
        resp = await async_client.put(
            f"/products/{sample_product.id}",
            json={"stock": 5},
        )
        assert resp.status_code == 200
        assert resp.json()["stock"] == 5
        assert resp.json()["price"] == original_price

    @pytest.mark.unit
    async def test_update_product_not_found(self, async_client):
        resp = await async_client.put(f"/products/{uuid4()}", json={"stock": 10})
        assert resp.status_code == 404

    @pytest.mark.unit
    async def test_update_product_deactivate(self, async_client, sample_product):
        resp = await async_client.put(
            f"/products/{sample_product.id}",
            json={"is_active": False},
        )
        assert resp.status_code == 200
        assert resp.json()["is_active"] is False


# ═══════════════════════════════════════════════════════════════════════════════
# DELETE /products/{id}
# ═══════════════════════════════════════════════════════════════════════════════

class TestDeactivateProduct:

    @pytest.mark.unit
    async def test_deactivate_product_success(self, async_client, sample_product):
        resp = await async_client.delete(f"/products/{sample_product.id}")
        assert resp.status_code == 200
        assert "deactivated" in resp.json()["message"].lower()

    @pytest.mark.unit
    async def test_deactivate_product_not_found(self, async_client):
        resp = await async_client.delete(f"/products/{uuid4()}")
        assert resp.status_code == 404

    @pytest.mark.unit
    async def test_deactivated_product_not_listed(self, async_client, sample_product):
        """Un producto desactivado no aparece en el listado."""
        await async_client.delete(f"/products/{sample_product.id}")
        resp = await async_client.get("/products")
        products = [p for p in resp.json() if p["id"] == str(sample_product.id)]
        assert products == []


# ═══════════════════════════════════════════════════════════════════════════════
# GET /products/{id}/stock
# ═══════════════════════════════════════════════════════════════════════════════

class TestCheckStock:

    @pytest.mark.unit
    async def test_stock_available(self, async_client, sample_product):
        resp = await async_client.get(
            f"/products/{sample_product.id}/stock",
            params={"quantity": 50},
        )
        assert resp.status_code == 200
        assert resp.json()["available"] is True

    @pytest.mark.unit
    async def test_stock_insufficient(self, async_client, sample_product):
        resp = await async_client.get(
            f"/products/{sample_product.id}/stock",
            params={"quantity": 9999},
        )
        assert resp.status_code == 200
        assert resp.json()["available"] is False

    @pytest.mark.unit
    async def test_stock_product_not_found(self, async_client):
        resp = await async_client.get(
            f"/products/{uuid4()}/stock",
            params={"quantity": 1},
        )
        assert resp.status_code == 404

    @pytest.mark.unit
    async def test_stock_quantity_zero_rejected(self, async_client, sample_product):
        """quantity debe ser >= 1."""
        resp = await async_client.get(
            f"/products/{sample_product.id}/stock",
            params={"quantity": 0},
        )
        assert resp.status_code == 422
