import json
from datetime import date, timedelta
from typing import List, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.models.product import Product
from app.models.sale import Sale
from app.models.prediction import Prediction
from app.models.alert import Alert
from app.schemas.analytics import (
    SummaryCards, UrgentProduct, CategoryDistribution,
    RiskDistribution, TrendPoint, AnalyticsDashboard
)

def get_analytics_dashboard(db: Session) -> AnalyticsDashboard:
    """
    Assembles comprehensive analytics and urgency metrics for the vendor dashboard.
    """
    products = db.query(Product).all()
    predictions = {p.product_id: p for p in db.query(Prediction).all()}

    total_products = len(products)
    low_stock_products = sum(1 for p in products if p.current_stock <= p.minimum_stock)
    
    high_risk_products = 0
    critical_risk_products = 0
    stockout_soon_products = 0
    pending_restock_recommendations = 0

    urgent_list: List[UrgentProduct] = []

    for p in products:
        pred = predictions.get(p.id)
        risk = pred.risk_level if pred else "LOW"
        days_left = pred.days_until_stockout if pred else None
        recommended_restock = pred.recommended_restock if pred else 0

        if risk == "CRITICAL":
            critical_risk_products += 1
        elif risk == "HIGH":
            high_risk_products += 1

        if days_left is not None and days_left <= 7.0:
            stockout_soon_products += 1

        if recommended_restock > 0:
            pending_restock_recommendations += 1

        # Check urgency
        if risk in ["CRITICAL", "HIGH"] or p.current_stock <= p.minimum_stock or (days_left is not None and days_left <= 5.0):
            expl_summary = "Stock below safe threshold"
            avg_daily = 0.0
            if pred and pred.explainability_json:
                try:
                    expl = json.loads(pred.explainability_json)
                    expl_summary = expl.get("summary", expl_summary)
                    avg_daily = expl.get("factors", {}).get("avg_daily_sales", pred.predicted_daily_demand)
                except Exception:
                    pass

            urgent_list.append(UrgentProduct(
                id=p.id,
                name=p.name,
                category=p.category,
                sku=p.sku,
                current_stock=p.current_stock,
                lead_time_days=p.lead_time_days,
                average_daily_sales=round(avg_daily, 1),
                predicted_stockout_days=days_left,
                predicted_stockout_date=pred.predicted_stockout_date.isoformat() if pred and pred.predicted_stockout_date else None,
                risk_level=risk,
                recommended_restock=recommended_restock,
                explanation_summary=expl_summary
            ))

    # Sort urgent products by days until stockout (nulls last)
    urgent_list.sort(key=lambda u: (u.predicted_stockout_days if u.predicted_stockout_days is not None else 9999))

    # Sales aggregation
    total_sales_stats = db.query(
        func.sum(Sale.quantity),
        func.sum(Sale.quantity * Sale.price)
    ).first()
    total_units_sold = int(total_sales_stats[0] or 0)
    total_revenue = round(float(total_sales_stats[1] or 0.0), 2)

    summary = SummaryCards(
        total_products=total_products,
        low_stock_products=low_stock_products,
        high_risk_products=high_risk_products,
        critical_risk_products=critical_risk_products,
        stockout_soon_products=stockout_soon_products,
        pending_restock_recommendations=pending_restock_recommendations,
        total_revenue=total_revenue,
        total_units_sold=total_units_sold
    )

    # Category distribution
    cat_counts: Dict[str, Dict[str, int]] = {}
    for p in products:
        if p.category not in cat_counts:
            cat_counts[p.category] = {"count": 0, "total_stock": 0}
        cat_counts[p.category]["count"] += 1
        cat_counts[p.category]["total_stock"] += p.current_stock

    category_distribution = [
        CategoryDistribution(category=cat, count=vals["count"], total_stock=vals["total_stock"])
        for cat, vals in sorted(cat_counts.items(), key=lambda x: x[1]["count"], reverse=True)
    ]

    # Risk distribution
    risk_counts = {"LOW": 0, "MEDIUM": 0, "HIGH": 0, "CRITICAL": 0}
    for p in products:
        pred = predictions.get(p.id)
        r = pred.risk_level if pred else "LOW"
        risk_counts[r] = risk_counts.get(r, 0) + 1

    risk_distribution = [
        RiskDistribution(risk_level=k, count=v)
        for k, v in risk_counts.items()
    ]

    # 30-day sales trend
    start_date = date.today() - timedelta(days=29)
    sales_30d = db.query(
        Sale.sale_date,
        func.sum(Sale.quantity).label("units"),
        func.sum(Sale.quantity * Sale.price).label("rev")
    ).filter(Sale.sale_date >= start_date).group_by(Sale.sale_date).all()

    sales_map = {s.sale_date: (int(s.units or 0), float(s.rev or 0.0)) for s in sales_30d}

    recent_sales_trend: List[TrendPoint] = []
    for day_offset in range(30):
        cur_d = start_date + timedelta(days=day_offset)
        units, rev = sales_map.get(cur_d, (0, 0.0))
        recent_sales_trend.append(TrendPoint(
            date=cur_d.isoformat(),
            sales_units=units,
            revenue=round(rev, 2)
        ))

    return AnalyticsDashboard(
        summary=summary,
        urgent_products=urgent_list,
        category_distribution=category_distribution,
        risk_distribution=risk_distribution,
        recent_sales_trend=recent_sales_trend
    )
