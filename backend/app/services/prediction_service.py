import json
from datetime import datetime, timezone, date
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from app.models.product import Product
from app.models.sale import Sale
from app.models.prediction import Prediction
from app.ml.preprocessor import prepare_daily_sales_series
from app.ml.models import forecast_product_demand
from app.ml.explainability import calculate_inventory_insights
from app.services.alert_service import evaluate_and_generate_product_alerts

def update_single_product_prediction(db: Session, product: Product) -> Prediction:
    """
    Fetches historical sales for a product, runs ML/statistical forecasting,
    computes stockout timing and risk, writes prediction to DB, updates product status,
    and creates alerts if thresholds are breached.
    """
    sales = db.query(Sale).filter(Sale.product_id == product.id).order_by(Sale.sale_date.asc()).all()
    sales_data = [
        {"sale_date": s.sale_date, "quantity": s.quantity, "price": s.price}
        for s in sales
    ]

    daily_df = prepare_daily_sales_series(sales_data)

    # 1. AI Forecasting
    forecast_result = forecast_product_demand(daily_df, lead_time_days=product.lead_time_days)

    # 2. Inventory Decision Intelligence & Explainability
    insights = calculate_inventory_insights(
        current_stock=product.current_stock,
        minimum_stock=product.minimum_stock,
        maximum_stock=product.maximum_stock,
        lead_time_days=product.lead_time_days,
        predicted_daily_demand=forecast_result["predicted_daily_demand"],
        demand_std_dev=forecast_result["demand_std_dev"],
        trend_percentage=forecast_result["trend_percentage"],
        avg_daily_sales=forecast_result["avg_daily_sales"],
        model_name=forecast_result["model_name"],
        confidence_label=forecast_result["confidence_label"]
    )

    # Attach evaluation metrics and forecast series to explainability JSON
    explainability_data = insights["explainability"]
    explainability_data["evaluation_metrics"] = forecast_result["evaluation_metrics"]
    explainability_data["forecast_days"] = forecast_result["forecast_days"]
    explainability_data["status_note"] = forecast_result.get("status_note", "")

    # Parse predicted stockout date
    stockout_date_val = None
    if insights["predicted_stockout_date"]:
        try:
            stockout_date_val = datetime.strptime(insights["predicted_stockout_date"], "%Y-%m-%d").date()
        except Exception:
            stockout_date_val = None

    # Upsert prediction record
    prediction = db.query(Prediction).filter(Prediction.product_id == product.id).first()
    if not prediction:
        prediction = Prediction(product_id=product.id)
        db.add(prediction)

    prediction.predicted_daily_demand = forecast_result["predicted_daily_demand"]
    prediction.predicted_stockout_date = stockout_date_val
    prediction.days_until_stockout = insights["days_until_stockout"]
    prediction.risk_level = insights["risk_level"]
    prediction.confidence = forecast_result["confidence"]
    prediction.confidence_label = forecast_result["confidence_label"]
    prediction.recommended_restock = insights["recommended_restock"]
    prediction.lead_time_demand = insights["lead_time_demand"]
    prediction.safety_stock = insights["safety_stock"]
    prediction.reorder_point = insights["reorder_point"]
    prediction.model_used = forecast_result["model_name"]
    prediction.explainability_json = json.dumps(explainability_data)
    prediction.updated_at = datetime.now(timezone.utc)

    # 3. Update Product status
    if product.current_stock == 0:
        product.status = "OUT_OF_STOCK"
    elif insights["risk_level"] == "CRITICAL":
        product.status = "CRITICAL"
    elif insights["risk_level"] == "HIGH":
        product.status = "HIGH_RISK"
    elif product.current_stock <= product.minimum_stock:
        product.status = "LOW_STOCK"
    else:
        product.status = "IN_STOCK"

    db.commit()
    db.refresh(prediction)
    db.refresh(product)

    # 4. Generate alerts
    evaluate_and_generate_product_alerts(db, product, prediction)

    return prediction

def update_all_predictions(db: Session) -> List[Prediction]:
    """
    Refreshes predictions for all products in the database.
    """
    products = db.query(Product).all()
    results = []
    for prod in products:
        pred = update_single_product_prediction(db, prod)
        results.append(pred)
    return results
