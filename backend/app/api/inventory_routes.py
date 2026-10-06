from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc
from app.database.session import get_db
from app.models.inventory_log import InventoryLog
from app.models.product import Product
from app.schemas.product import RestockRequest, AdjustmentRequest
from app.services.inventory_service import record_restock, adjust_stock

router = APIRouter(prefix="/inventory", tags=["Inventory"])

@router.post("/{product_id}/restock", response_model=dict)
def restock_product(product_id: int, req: RestockRequest, db: Session = Depends(get_db)):
    """Add received stock shipment to product inventory."""
    product = record_restock(db, product_id, req.quantity, req.notes or "Shipment received")
    return {
        "status": "success",
        "message": f"Successfully restocked {req.quantity} units. Current stock is now {product.current_stock}.",
        "current_stock": product.current_stock
    }

@router.post("/{product_id}/adjust", response_model=dict)
def adjust_product_stock(product_id: int, req: AdjustmentRequest, db: Session = Depends(get_db)):
    """Adjust current inventory count based on physical warehouse audit."""
    product = adjust_stock(db, product_id, req.new_stock, req.reason or "Inventory audit")
    return {
        "status": "success",
        "message": f"Stock adjusted to {product.current_stock} units.",
        "current_stock": product.current_stock
    }

@router.get("/logs", response_model=List[dict])
def list_inventory_logs(
    product_id: Optional[int] = None,
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db)
):
    """List inventory movement logs (sales, restocks, adjustments)."""
    query = db.query(InventoryLog).join(Product)
    if product_id:
        query = query.filter(InventoryLog.product_id == product_id)
    
    logs = query.order_by(desc(InventoryLog.created_at)).offset(offset).limit(limit).all()
    
    return [
        {
            "id": l.id,
            "product_id": l.product_id,
            "product_name": l.product.name if l.product else None,
            "product_sku": l.product.sku if l.product else None,
            "change_type": l.change_type,
            "quantity_changed": l.quantity_changed,
            "previous_stock": l.previous_stock,
            "new_stock": l.new_stock,
            "notes": l.notes,
            "created_at": l.created_at.isoformat()
        }
        for l in logs
    ]
