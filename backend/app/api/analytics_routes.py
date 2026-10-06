import json
from typing import List, Dict, Any
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database.session import get_db
from app.models.prediction import Prediction
from app.models.product import Product
from app.services.analytics_service import get_analytics_dashboard

router = APIRouter(prefix="/analytics", tags=["Analytics"])

@router.get("", response_model=dict)
def get_analytics(db: Session = Depends(get_db)):
    """Returns aggregated KPIs, urgent product rankings, and trend charts."""
    dashboard = get_analytics_dashboard(db)
    return dashboard.model_dump()

@router.get("/model-performance", response_model=List[dict])
def get_model_performance(db: Session = Depends(get_db)):
    """
    Returns model evaluation metrics (MAE, RMSE, MAPE) across products
    specifically for college faculty project demonstration.
    """
    predictions = db.query(Prediction).join(Product).all()
    metrics_list = []

    for pred in predictions:
        if pred.explainability_json:
            try:
                expl = json.loads(pred.explainability_json)
                eval_metrics = expl.get("evaluation_metrics", {})
                metrics_list.append({
                    "product_id": pred.product_id,
                    "product_name": pred.product.name if pred.product else None,
                    "model_used": pred.model_used,
                    "confidence": pred.confidence,
                    "confidence_label": pred.confidence_label,
                    "mae": eval_metrics.get("mae", 0.0),
                    "rmse": eval_metrics.get("rmse", 0.0),
                    "mape": eval_metrics.get("mape", 0.0),
                    "note": expl.get("status_note", "")
                })
            except Exception:
                pass

    return metrics_list
