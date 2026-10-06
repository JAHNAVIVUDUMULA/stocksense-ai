import numpy as np
import pandas as pd
from typing import Dict, Any, Tuple, Optional
from datetime import date, timedelta
from sklearn.linear_model import Ridge
from sklearn.ensemble import RandomForestRegressor
from app.ml.features import build_time_series_features, get_feature_matrix
from app.ml.evaluation import calculate_metrics

def forecast_product_demand(daily_df: pd.DataFrame, lead_time_days: int = 5) -> Dict[str, Any]:
    """
    Adaptive Demand Forecasting Engine:
    Selects the most appropriate model based on data quantity:
    - >= 14 days: Machine Learning Ridge Regressor with lag & calendar features
    - 5-13 days: Exponentially Weighted Moving Average (EWMA) with trend factor
    - < 5 days or empty: Baseline Moving Average with low confidence warning
    """
    total_days = len(daily_df)
    non_zero_days = int((daily_df["quantity"] > 0).sum()) if not daily_df.empty else 0
    total_sales = float(daily_df["quantity"].sum()) if not daily_df.empty else 0.0

    # Edge Case: No sales history at all
    if daily_df.empty or total_sales == 0:
        return {
            "predicted_daily_demand": 0.0,
            "model_name": "Zero-Demand Baseline",
            "confidence": 0.20,
            "confidence_label": "Low",
            "avg_daily_sales": 0.0,
            "demand_std_dev": 0.0,
            "trend_percentage": 0.0,
            "forecast_days": [0.0] * 14,
            "evaluation_metrics": {"mae": 0.0, "rmse": 0.0, "mape": 0.0},
            "status_note": "No sales history recorded for this product."
        }

    # Basic statistics
    avg_daily_sales = float(daily_df["quantity"].mean())
    demand_std_dev = float(daily_df["quantity"].std(ddof=0))
    
    # Calculate recent trend: last 7 days vs previous 14 days
    if total_days >= 14:
        recent_7 = daily_df["quantity"].tail(7).mean()
        prior_14 = daily_df["quantity"].iloc[-21:-7].mean() if total_days >= 21 else daily_df["quantity"].head(total_days - 7).mean()
        if prior_14 > 0:
            trend_percentage = round(((recent_7 - prior_14) / prior_14) * 100, 1)
        else:
            trend_percentage = 0.0
    else:
        trend_percentage = 0.0

    # CASE 1: Rich Data (>= 14 days) -> ML Supervised Regressor
    if total_days >= 14 and non_zero_days >= 4:
        feature_df = build_time_series_features(daily_df)
        if len(feature_df) >= 10:
            X, y, feature_cols = get_feature_matrix(feature_df)
            
            # Temporal train/test split: hold out last 20% (or min 3 days) for evaluation
            test_size = max(3, int(len(X) * 0.2))
            X_train, X_test = X[:-test_size], X[-test_size:]
            y_train, y_test = y[:-test_size], y[-test_size:]

            model = Ridge(alpha=1.0)
            model.fit(X_train, y_train)

            y_pred_test = model.predict(X_test)
            metrics = calculate_metrics(y_test, y_pred_test)

            # Refit on all data for future forecast
            model.fit(X, y)

            # Next-day prediction using the latest features
            latest_features = X[-1].reshape(1, -1)
            raw_prediction = float(model.predict(latest_features)[0])
            predicted_daily = max(0.0, round(raw_prediction, 2))

            # If ML output is completely flat or negative, fall back to weighted 7-day average
            if predicted_daily <= 0 and avg_daily_sales > 0:
                predicted_daily = round(daily_df["quantity"].tail(7).mean(), 2)

            # Generate 14-day future forecast curve
            forecast_curve = []
            curr_val = predicted_daily
            for day_idx in range(14):
                # Apply slight day-of-week factor and decay
                dow = (date.today().weekday() + day_idx + 1) % 7
                dow_mult = 1.15 if dow in [4, 5] else (0.90 if dow == 6 else 1.0)
                forecast_curve.append(round(max(0.0, curr_val * dow_mult), 2))

            # Confidence based on error metrics and data points
            confidence_score = min(0.95, max(0.55, 1.0 - (metrics["mae"] / (avg_daily_sales + 1.0))))
            confidence_label = "High" if confidence_score >= 0.75 else "Medium"

            return {
                "predicted_daily_demand": predicted_daily,
                "model_name": "Machine Learning (Ridge Lag Regressor)",
                "confidence": round(confidence_score, 2),
                "confidence_label": confidence_label,
                "avg_daily_sales": round(avg_daily_sales, 2),
                "demand_std_dev": round(demand_std_dev, 2),
                "trend_percentage": trend_percentage,
                "forecast_days": forecast_curve,
                "evaluation_metrics": metrics,
                "status_note": f"Trained on {total_days} days of sales transactions."
            }

    # CASE 2: Moderate Data (5 to 13 days) -> Exponentially Weighted Moving Average (EWMA)
    if total_days >= 5:
        # EWMA with alpha = 0.3
        ewma_series = daily_df["quantity"].ewm(alpha=0.3, adjust=False).mean()
        latest_ewma = float(ewma_series.iloc[-1])
        # Apply recent trend adjustment
        recent_3 = daily_df["quantity"].tail(3).mean()
        overall = daily_df["quantity"].mean()
        adj_factor = max(0.8, min(1.3, (recent_3 / (overall + 1e-5))))
        predicted_daily = max(0.0, round(latest_ewma * adj_factor, 2))

        # Evaluation on last 2 days
        y_test = daily_df["quantity"].tail(2).values
        y_pred = ewma_series.tail(2).values
        metrics = calculate_metrics(y_test, y_pred)

        forecast_curve = [predicted_daily] * 14
        confidence_score = 0.65
        return {
            "predicted_daily_demand": predicted_daily,
            "model_name": "Exponentially Weighted Moving Average (EWMA)",
            "confidence": confidence_score,
            "confidence_label": "Medium",
            "avg_daily_sales": round(avg_daily_sales, 2),
            "demand_std_dev": round(demand_std_dev, 2),
            "trend_percentage": trend_percentage,
            "forecast_days": forecast_curve,
            "evaluation_metrics": metrics,
            "status_note": f"Moderate sales history ({total_days} days). Uses EWMA forecasting."
        }

    # CASE 3: Limited Data (< 5 days) -> Baseline Demand Estimate
    predicted_daily = max(0.0, round(avg_daily_sales, 2))
    forecast_curve = [predicted_daily] * 14
    return {
        "predicted_daily_demand": predicted_daily,
        "model_name": "Baseline Moving Average",
        "confidence": 0.40,
        "confidence_label": "Low",
        "avg_daily_sales": round(avg_daily_sales, 2),
        "demand_std_dev": round(demand_std_dev, 2),
        "trend_percentage": 0.0,
        "forecast_days": forecast_curve,
        "evaluation_metrics": {"mae": round(demand_std_dev, 2), "rmse": round(demand_std_dev, 2), "mape": 0.0},
        "status_note": "Limited historical data (< 5 days) — prediction confidence is low."
    }
