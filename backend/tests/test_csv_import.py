import pytest
import io
from fastapi.testclient import TestClient
from app.main import app
from app.database.session import SessionLocal
from app.models.product import Product

client = TestClient(app)

def test_csv_sales_import():
    db = SessionLocal()
    sku = "TEST-CSV-ITEM"
    db.query(Product).filter(Product.sku == sku).delete()
    db.commit()

    product = Product(
        name="USB Card Reader",
        category="Accessories",
        sku=sku,
        current_stock=50,
        minimum_stock=10,
        maximum_stock=100,
        unit_price=12.0,
        lead_time_days=3
    )
    db.add(product)
    db.commit()
    db.refresh(product)
    db.close()

    # 1. Valid CSV import
    valid_csv = (
        "sku,date,quantity,price\n"
        f"{sku},2026-10-01,5,12.00\n"
        f"{sku},2026-10-02,3,12.00\n"
    )
    res = client.post(
        "/api/sales/import",
        files={"file": ("sales.csv", io.BytesIO(valid_csv.encode("utf-8")), "text/csv")}
    )
    assert res.status_code == 200
    data = res.json()
    assert data["successful"] == 2
    assert data["failed"] == 0

    # 2. Missing columns CSV import
    bad_csv = "random_col1,random_col2\nfoo,bar\n"
    res_bad = client.post(
        "/api/sales/import",
        files={"file": ("bad.csv", io.BytesIO(bad_csv.encode("utf-8")), "text/csv")}
    )
    assert res_bad.status_code == 200
    bad_data = res_bad.json()
    assert len(bad_data["errors"]) > 0
    assert "missing required columns" in bad_data["errors"][0].lower()

    # 3. CSV with invalid row data
    invalid_rows_csv = (
        "sku,date,quantity,price\n"
        f"UNKNOWN_SKU,2026-10-01,5,12.00\n"
        f"{sku},invalid_date,5,12.00\n"
        f"{sku},2026-10-02,-10,12.00\n"
    )
    res_inv = client.post(
        "/api/sales/import",
        files={"file": ("invalid.csv", io.BytesIO(invalid_rows_csv.encode("utf-8")), "text/csv")}
    )
    assert res_inv.status_code == 200
    inv_data = res_inv.json()
    assert inv_data["failed"] == 3
    assert len(inv_data["errors"]) == 3
