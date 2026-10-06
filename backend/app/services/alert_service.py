from datetime import datetime, timezone
from sqlalchemy.orm import Session
from app.models.alert import Alert
from app.models.product import Product
from app.models.prediction import Prediction
from typing import Optional, List

def create_alert_if_not_exists(
    db: Session,
    product_id: int,
    alert_type: str,
    severity: str,
    message: str,
    recommended_action: Optional[str] = None
) -> Optional[Alert]:
    """
    Creates an alert only if an unread alert of the same type does NOT already exist for this product.
    This fulfills Rule #19: Automatic alert generation with duplicate prevention.
    """
    existing_unread = db.query(Alert).filter(
        Alert.product_id == product_id,
        Alert.alert_type == alert_type,
        Alert.is_read == False
    ).first()

    if existing_unread:
        return None  # Prevent duplicate alert spam

    new_alert = Alert(
        product_id=product_id,
        alert_type=alert_type,
        severity=severity,
        message=message,
        recommended_action=recommended_action,
        is_read=False,
        created_at=datetime.now(timezone.utc)
    )
    db.add(new_alert)
    db.commit()
    db.refresh(new_alert)
    return new_alert

def evaluate_and_generate_product_alerts(db: Session, product: Product, prediction: Optional[Prediction] = None) -> List[Alert]:
    """
    Evaluates a product and its prediction, generating appropriate alerts.
    """
    generated = []

    # 1. Out of stock or Critical Risk
    if product.current_stock == 0:
        a = create_alert_if_not_exists(
            db=db,
            product_id=product.id,
            alert_type="CRITICAL_RISK",
            severity="CRITICAL",
            message=f"{product.name} is completely OUT OF STOCK! Immediate supplier order required.",
            recommended_action=f"Order restock immediately (Supplier: {product.supplier_name or 'Default'})."
        )
        if a: generated.append(a)

    elif product.current_stock <= product.minimum_stock:
        # 2. Low stock alert
        a = create_alert_if_not_exists(
            db=db,
            product_id=product.id,
            alert_type="LOW_STOCK",
            severity="HIGH",
            message=f"{product.name} inventory ({product.current_stock}) has fallen below minimum safety threshold ({product.minimum_stock}).",
            recommended_action="Place a purchase order with supplier before stock runs out."
        )
        if a: generated.append(a)

    # 3. AI Predicted Stockout alert
    if prediction:
        if prediction.days_until_stockout is not None:
            if prediction.days_until_stockout <= product.lead_time_days:
                a = create_alert_if_not_exists(
                    db=db,
                    product_id=product.id,
                    alert_type="PREDICTED_STOCKOUT",
                    severity="CRITICAL",
                    message=f"{product.name} is predicted to stock out in {prediction.days_until_stockout} days, which is earlier than supplier lead time ({product.lead_time_days} days)!",
                    recommended_action=f"Expedite restock order of {prediction.recommended_restock} units immediately to avoid stockout."
                )
                if a: generated.append(a)
            elif prediction.days_until_stockout <= (product.lead_time_days * 1.5):
                a = create_alert_if_not_exists(
                    db=db,
                    product_id=product.id,
                    alert_type="PREDICTED_STOCKOUT",
                    severity="HIGH",
                    message=f"{product.name} is predicted to deplete in approximately {prediction.days_until_stockout} days.",
                    recommended_action=f"Prepare restock order of {prediction.recommended_restock} units."
                )
                if a: generated.append(a)

        # 4. Restock Recommendation alert
        if prediction.recommended_restock > 0 and prediction.risk_level in ["CRITICAL", "HIGH"]:
            a = create_alert_if_not_exists(
                db=db,
                product_id=product.id,
                alert_type="RESTOCK_RECOMMENDED",
                severity="HIGH" if prediction.risk_level == "CRITICAL" else "MEDIUM",
                message=f"StockSense AI recommends ordering {prediction.recommended_restock} units of {product.name}.",
                recommended_action=f"Order {prediction.recommended_restock} units (Reorder Point: {prediction.reorder_point}, Safety Stock: {prediction.safety_stock})."
            )
            if a: generated.append(a)

    return generated
