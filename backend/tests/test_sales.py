import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.database.session import SessionLocal
from app.models.product import Product

client = TestClient(app)

def test_record_sales_and_inventory_decrement():
    sku = "TEST-SALE-101"
    db = SessionLocal()
    db.query(Product).filter(Product.sku == sku).delete()
    db.commit()
    db.close()

    # Create product with 20 units
    create_res = client.post("/api/products", json={
        "name": "Wireless Charging Pad",
        "category": "Charging",
        "sku": sku,
        "current_stock": 20,
        "minimum_stock": 5,
        "maximum_stock": 50,
        "unit_price": 25.0,
        "lead_time_days": 3
    })
    prod_id = create_res.json()["id"]

    # 1. Record valid sale of 5 units
    sale_res = client.post("/api/sales", json={
        "product_id": prod_id,
        "quantity": 5,
        "price": 25.0
    })
    assert sale_res.status_code == 201

    # Check inventory decremented to 15
    detail = client.get(f"/api/products/{prod_id}").json()
    assert detail["current_stock"] == 15

    # 2. Prevent invalid negative / excessive sale
    excessive_res = client.post("/api/sales", json={
        "product_id": prod_id,
        "quantity": 25 # only 15 in stock!
    })
    assert excessive_res.status_code == 400
    assert "Insufficient inventory" in excessive_res.json()["detail"]

    # 3. Check inventory movement logs
    logs_res = client.get(f"/api/inventory/logs?product_id={prod_id}")
    assert logs_res.status_code == 200
    logs = logs_res.json()
    assert any(l["change_type"] == "SALE" and l["quantity_changed"] == -5 for l in logs)

    # 4. Restock product
    restock_res = client.post(f"/api/inventory/{prod_id}/restock", json={
        "quantity": 10,
        "notes": "Weekly supplier shipment"
    })
    assert restock_res.status_code == 200
    assert restock_res.json()["current_stock"] == 25

    # Cleanup
    client.delete(f"/api/products/{prod_id}")
