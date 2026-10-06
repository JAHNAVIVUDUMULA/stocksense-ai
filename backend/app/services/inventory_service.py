from datetime import datetime, timezone
from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from app.models.product import Product
from app.models.inventory_log import InventoryLog
from app.services.prediction_service import update_single_product_prediction

def record_restock(db: Session, product_id: int, quantity: int, notes: str = "Vendor Restock") -> Product:
    """
    Increases product stock by quantity, records inventory log,
    and refreshes predictions/alerts immediately.
    """
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")

    if quantity <= 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Restock quantity must be positive")

    prev_stock = product.current_stock
    new_stock = prev_stock + quantity

    product.current_stock = new_stock
    product.updated_at = datetime.now(timezone.utc)

    # Log inventory change
    log = InventoryLog(
        product_id=product.id,
        change_type="RESTOCK",
        quantity_changed=quantity,
        previous_stock=prev_stock,
        new_stock=new_stock,
        notes=notes,
        created_at=datetime.now(timezone.utc)
    )
    db.add(log)
    db.commit()
    db.refresh(product)

    # Refresh AI prediction & status
    update_single_product_prediction(db, product)

    return product

def adjust_stock(db: Session, product_id: int, new_stock: int, reason: str = "Physical Count Adjustment") -> Product:
    """
    Manually adjusts current inventory count to new_stock, logs the diff,
    and refreshes prediction & alerts.
    """
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")

    if new_stock < 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Stock count cannot be negative")

    prev_stock = product.current_stock
    qty_changed = new_stock - prev_stock

    product.current_stock = new_stock
    product.updated_at = datetime.now(timezone.utc)

    log = InventoryLog(
        product_id=product.id,
        change_type="ADJUSTMENT",
        quantity_changed=qty_changed,
        previous_stock=prev_stock,
        new_stock=new_stock,
        notes=reason,
        created_at=datetime.now(timezone.utc)
    )
    db.add(log)
    db.commit()
    db.refresh(product)

    update_single_product_prediction(db, product)

    return product
