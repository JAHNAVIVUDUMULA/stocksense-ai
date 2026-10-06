import pytest
import pandas as pd
from datetime import date, timedelta
from app.ml.preprocessor import prepare_daily_sales_series
from app.ml.models import forecast_product_demand
from app.ml.explainability import calculate_inventory_insights

def test_ml_prediction_rich_data():
    """Tests ML forecasting when sufficient sales data (30 days) is available."""
    today = date.today()
    sales_records = []
    for i in range(30, 0, -1):
        d = today - timedelta(days=i)
        # Consistent daily sales around 5 units
        sales_records.append({"sale_date": d, "quantity": 5 + (i % 3), "price": 20.0})

    daily_df = prepare_daily_sales_series(sales_records)
    forecast = forecast_product_demand(daily_df, lead_time_days=4)

    assert "Machine Learning" in forecast["model_name"]
    assert forecast["predicted_daily_demand"] > 0
    assert forecast["confidence"] >= 0.50
    assert len(forecast["forecast_days"]) == 14
    assert "mae" in forecast["evaluation_metrics"]

def test_ewma_moderate_data():
    """Tests EWMA forecaster with 8 days of sales data."""
    today = date.today()
    sales_records = [
        {"sale_date": today - timedelta(days=i), "quantity": 4, "price": 15.0}
        for i in range(8, 0, -1)
    ]
    daily_df = prepare_daily_sales_series(sales_records)
    forecast = forecast_product_demand(daily_df, lead_time_days=3)

    assert "EWMA" in forecast["model_name"]
    assert forecast["predicted_daily_demand"] > 0
    assert forecast["confidence_label"] == "Medium"

def test_baseline_limited_data():
    """Tests baseline moving average when fewer than 5 days are present."""
    today = date.today()
    sales_records = [
        {"sale_date": today - timedelta(days=2), "quantity": 3, "price": 10.0},
        {"sale_date": today - timedelta(days=1), "quantity": 5, "price": 10.0}
    ]
    daily_df = prepare_daily_sales_series(sales_records)
    forecast = forecast_product_demand(daily_df, lead_time_days=5)

    assert "Baseline" in forecast["model_name"]
    assert forecast["confidence_label"] == "Low"
    assert "Limited historical data" in forecast["status_note"]

def test_zero_sales_edge_case():
    """Tests safe handling of zero sales without divide-by-zero errors."""
    daily_df = pd.DataFrame(columns=["date", "quantity", "revenue"])
    forecast = forecast_product_demand(daily_df, lead_time_days=5)

    assert forecast["predicted_daily_demand"] == 0.0
    assert forecast["confidence_label"] == "Low"

    # Test inventory insights on zero demand
    insights = calculate_inventory_insights(
        current_stock=10,
        minimum_stock=5,
        maximum_stock=50,
        lead_time_days=4,
        predicted_daily_demand=0.0,
        demand_std_dev=0.0,
        trend_percentage=0.0,
        avg_daily_sales=0.0,
        model_name="Zero-Demand Baseline",
        confidence_label="Low"
    )
    assert insights["days_until_stockout"] is None
    assert insights["risk_level"] == "LOW"

def test_critical_risk_stockout_before_lead_time():
    """Verify CRITICAL risk when stockout occurs before supplier shipment can arrive."""
    insights = calculate_inventory_insights(
        current_stock=6,
        minimum_stock=10,
        maximum_stock=50,
        lead_time_days=5, # Lead time 5 days
        predicted_daily_demand=3.0, # Will deplete in 2 days (2 < 5!)
        demand_std_dev=1.0,
        trend_percentage=15.0,
        avg_daily_sales=3.0,
        model_name="Machine Learning",
        confidence_label="High"
    )
    assert insights["risk_level"] == "CRITICAL"
    assert insights["days_until_stockout"] == 2.0
    assert insights["recommended_restock"] > 0
    assert "explainability" in insights
    assert len(insights["explainability"]["reasons"]) > 0
