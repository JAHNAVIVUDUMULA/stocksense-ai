from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc
from app.database.session import get_db
from app.models.alert import Alert
from app.models.product import Product

router = APIRouter(prefix="/alerts", tags=["Alerts"])

@router.get("", response_model=List[dict])
def list_alerts(
    unread_only: bool = False,
    severity: Optional[str] = None,
    alert_type: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """List inventory alerts sorted with unread and most severe first."""
    query = db.query(Alert).join(Product)

    if unread_only:
        query = query.filter(Alert.is_read == False)
    if severity and severity.upper() != "ALL":
        query = query.filter(Alert.severity == severity.upper())
    if alert_type and alert_type.upper() != "ALL":
        query = query.filter(Alert.alert_type == alert_type.upper())

    alerts = query.order_by(Alert.is_read.asc(), desc(Alert.created_at)).all()

    return [
        {
            "id": a.id,
            "product_id": a.product_id,
            "product_name": a.product.name if a.product else None,
            "product_sku": a.product.sku if a.product else None,
            "alert_type": a.alert_type,
            "severity": a.severity,
            "message": a.message,
            "recommended_action": a.recommended_action,
            "is_read": a.is_read,
            "created_at": a.created_at.isoformat()
        }
        for a in alerts
    ]

@router.get("/count", response_model=dict)
def get_unread_counts(db: Session = Depends(get_db)):
    """Returns unread alert badge counts grouped by severity."""
    unread_alerts = db.query(Alert).filter(Alert.is_read == False).all()
    
    counts = {
        "total_unread": len(unread_alerts),
        "critical": sum(1 for a in unread_alerts if a.severity == "CRITICAL"),
        "high": sum(1 for a in unread_alerts if a.severity == "HIGH"),
        "medium": sum(1 for a in unread_alerts if a.severity == "MEDIUM"),
        "low": sum(1 for a in unread_alerts if a.severity == "LOW")
    }
    return counts

@router.put("/{alert_id}/read", response_model=dict)
def mark_alert_read(alert_id: int, db: Session = Depends(get_db)):
    """Mark a specific alert as read."""
    alert = db.query(Alert).filter(Alert.id == alert_id).first()
    if not alert:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Alert not found")
    
    alert.is_read = True
    db.commit()
    return {"status": "success", "message": "Alert marked as read."}

@router.put("/mark-all-read", response_model=dict)
def mark_all_read(db: Session = Depends(get_db)):
    """Mark all unread alerts as read."""
    updated = db.query(Alert).filter(Alert.is_read == False).update({"is_read": True})
    db.commit()
    return {"status": "success", "message": f"{updated} alerts marked as read."}

@router.delete("/{alert_id}", response_model=dict)
def delete_alert(alert_id: int, db: Session = Depends(get_db)):
    """Remove an alert."""
    alert = db.query(Alert).filter(Alert.id == alert_id).first()
    if not alert:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Alert not found")
    
    db.delete(alert)
    db.commit()
    return {"status": "success", "message": "Alert deleted."}
