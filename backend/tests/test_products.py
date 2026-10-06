import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.database.session import SessionLocal
from app.models.product import Product

client = TestClient(app)

def test_product_crud_and_search():
    sku = "TEST-PROD-999"
    # Cleanup
    db = SessionLocal()
    db.query(Product).filter(Product.sku == sku).delete()
    db.commit()
    db.close()

    # 1. Create product
    create_res = client.post("/api/products", json={
        "name": "Precision Gaming Mouse",
        "category": "Gaming",
        "sku": sku,
        "description": "High DPI optical sensor",
        "current_stock": 25,
        "minimum_stock": 10,
        "maximum_stock": 100,
        "unit_price": 49.99,
        "supplier_name": "ProGamer Supply",
        "lead_time_days": 4
    })
    assert create_res.status_code == 201
    prod_id = create_res.json()["id"]

    # 2. Duplicate SKU rejection
    dup_res = client.post("/api/products", json={
        "name": "Another Mouse",
        "category": "Gaming",
        "sku": sku,
        "current_stock": 10,
        "minimum_stock": 5,
        "maximum_stock": 50,
        "unit_price": 20.0,
        "lead_time_days": 3
    })
    assert dup_res.status_code == 400

    # 3. Read product detail
    detail_res = client.get(f"/api/products/{prod_id}")
    assert detail_res.status_code == 200
    detail = detail_res.json()
    assert detail["name"] == "Precision Gaming Mouse"
    assert detail["current_stock"] == 25
    assert "prediction" in detail

    # 4. Search product
    search_res = client.get("/api/products?search=Gaming")
    assert search_res.status_code == 200
    items = search_res.json()
    assert any(i["sku"] == sku for i in items)

    # 5. Update product
    update_res = client.put(f"/api/products/{prod_id}", json={
        "name": "Precision Gaming Mouse V2",
        "unit_price": 54.99
    })
    assert update_res.status_code == 200
    refreshed = client.get(f"/api/products/{prod_id}").json()
    assert refreshed["name"] == "Precision Gaming Mouse V2"
    assert refreshed["unit_price"] == 54.99

    # 6. Delete product
    del_res = client.delete(f"/api/products/{prod_id}")
    assert del_res.status_code == 200

    # 7. Verify deletion
    assert client.get(f"/api/products/{prod_id}").status_code == 404
