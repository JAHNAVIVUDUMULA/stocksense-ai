import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.database.session import SessionLocal
from app.models.product import Product
from app.models.alert import Alert
from app.services.alert_service import create_alert_if_not_exists, evaluate_and_generate_product_alerts

client = TestClient(app)

def test_alerts_and_duplicate_prevention():
    db = SessionLocal()
    sku = "TEST-ALERT-001"
    db.query(Product).filter(Product.sku == sku).delete()
    db.commit()

    # Create product with 2 units (below min of 10)
    product = Product(
        name="Emergency Test Flashlight",
        category="Safety",
        sku=sku,
        current_stock=2,
        minimum_stock=10,
        maximum_stock=50,
        unit_price=15.0,
        lead_time_days=4,
        status="LOW_STOCK"
    )
    db.add(product)
    db.commit()
    db.refresh(product)

    # 1. First alert generation
    a1 = create_alert_if_not_exists(
        db=db,
        product_id=product.id,
        alert_type="LOW_STOCK",
        severity="HIGH",
        message="Stock is low."
    )
    assert a1 is not None

    # 2. Second attempt: duplicate unread alert should NOT be created
    a2 = create_alert_if_not_exists(
        db=db,
        product_id=product.id,
        alert_type="LOW_STOCK",
        severity="HIGH",
        message="Stock is low."
    )
    assert a2 is None, "Duplicate unread alert was incorrectly generated!"

    # 3. Mark alert as read via API
    read_res = client.put(f"/api/alerts/{a1.id}/read")
    assert read_res.status_code == 200

    # Verify is_read is True
    db.refresh(a1)
    assert a1.is_read is True

    # 4. Mark all read
    all_read_res = client.put("/api/alerts/mark-all-read")
    assert all_read_res.status_code == 200

    # Cleanup
    db.delete(a1)
    db.delete(product)
    db.commit()
    db.close()
