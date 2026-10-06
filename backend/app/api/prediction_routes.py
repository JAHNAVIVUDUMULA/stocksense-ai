import json
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database.session import get_db
from app.models.prediction import Prediction
from app.models.product import Product
from app.services.prediction_service import update_single_product_prediction, update_all_predictions

router = APIRouter(prefix="/predictions", tags=["Predictions"])

@router.get("", response_model=List[dict])
def list_predictions(db: Session = Depends(get_db)):
    """List AI demand predictions and risk calculations for all products."""
    predictions = db.query(Prediction).join(Product).all()
    results = []

    for pred in predictions:
        expl_data = {}
        if pred.explainability_json:
            try:
                expl_data = json.loads(pred.explainability_json)
            except Exception:
                pass

        results.append({
            "id": pred.id,
            "product_id": pred.product_id,
            "product_name": pred.product.name if pred.product else None,
            "product_sku": pred.product.sku if pred.product else None,
            "current_stock": pred.product.current_stock if pred.product else 0,
            "lead_time_days": pred.product.lead_time_days if pred.product else 5,
            "predicted_daily_demand": pred.predicted_daily_demand,
            "predicted_stockout_date": pred.predicted_stockout_date.isoformat() if pred.predicted_stockout_date else None,
            "days_until_stockout": pred.days_until_stockout,
            "risk_level": pred.risk_level,
            "confidence": pred.confidence,
            "confidence_label": pred.confidence_label,
            "recommended_restock": pred.recommended_restock,
            "lead_time_demand": pred.lead_time_demand,
            "safety_stock": pred.safety_stock,
            "reorder_point": pred.reorder_point,
            "model_used": pred.model_used,
            "explainability": expl_data,
            "updated_at": pred.updated_at.isoformat()
        })

    # Sort by urgency (critical first, then lowest days left)
    risk_rank = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}
    results.sort(key=lambda x: (risk_rank.get(x["risk_level"], 4), x["days_until_stockout"] if x["days_until_stockout"] is not None else 9999))
    return results

@router.get("/{product_id}", response_model=dict)
def get_prediction_detail(product_id: int, db: Session = Depends(get_db)):
    """Returns granular forecast numbers, 14-day future trend, and explainability breakdown."""
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")

    pred = db.query(Prediction).filter(Prediction.product_id == product_id).first()
    if not pred:
        # Generate on the fly if missing
        pred = update_single_product_prediction(db, product)

    expl_data = {}
    if pred.explainability_json:
        try:
            expl_data = json.loads(pred.explainability_json)
        except Exception:
            pass

    return {
        "id": pred.id,
        "product_id": pred.product_id,
        "product_name": product.name,
        "product_sku": product.sku,
        "current_stock": product.current_stock,
        "minimum_stock": product.minimum_stock,
        "maximum_stock": product.maximum_stock,
        "lead_time_days": product.lead_time_days,
        "unit_price": product.unit_price,
        "predicted_daily_demand": pred.predicted_daily_demand,
        "predicted_stockout_date": pred.predicted_stockout_date.isoformat() if pred.predicted_stockout_date else None,
        "days_until_stockout": pred.days_until_stockout,
        "risk_level": pred.risk_level,
        "confidence": pred.confidence,
        "confidence_label": pred.confidence_label,
        "recommended_restock": pred.recommended_restock,
        "lead_time_demand": pred.lead_time_demand,
        "safety_stock": pred.safety_stock,
        "reorder_point": pred.reorder_point,
        "model_used": pred.model_used,
        "explainability": expl_data,
        "updated_at": pred.updated_at.isoformat()
    }

@router.post("/refresh", response_model=dict)
def refresh_predictions(db: Session = Depends(get_db)):
    """
    Retrains/evaluates models across all products using latest sales and stock data.
    Generates fresh stockout calculations and alerts.
    """
    predictions = update_all_predictions(db)
    return {
        "status": "success",
        "message": f"Successfully updated predictions and inventory risk for {len(predictions)} products.",
        "count": len(predictions)
    }
