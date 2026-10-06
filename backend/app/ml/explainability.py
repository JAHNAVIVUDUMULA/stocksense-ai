import math
from datetime import date, timedelta
from typing import Dict, Any, Optional, List

def calculate_inventory_insights(
    current_stock: int,
    minimum_stock: int,
    maximum_stock: int,
    lead_time_days: int,
    predicted_daily_demand: float,
    demand_std_dev: float,
    trend_percentage: float,
    avg_daily_sales: float,
    model_name: str,
    confidence_label: str
) -> Dict[str, Any]:
    """
    Computes Safety Stock, Reorder Point, Days until Stockout, Risk Level,
    Recommended Restock Quantity, and generates AI Explainability reasoning.
    """
    # 1. Lead Time Demand (LTD)
    lead_time_demand = round(predicted_daily_demand * lead_time_days, 1)

    # 2. Safety Stock: Z * std_dev * sqrt(lead_time)
    # Z = 1.65 (95% service level) for retail standard
    z_factor = 1.65
    calculated_safety_stock = int(math.ceil(z_factor * demand_std_dev * math.sqrt(max(1, lead_time_days))))
    # Fallback to at least minimum_stock if calculated safety stock is trivial
    safety_stock = max(minimum_stock, min(calculated_safety_stock, maximum_stock // 3))

    # 3. Reorder Point (ROP) = Lead Time Demand + Safety Stock
    reorder_point = int(math.ceil(lead_time_demand + safety_stock))

    # 4. Expected Days until Depletion / Stockout
    if current_stock <= 0:
        days_until_stockout = 0.0
        predicted_stockout_date = date.today().isoformat()
    elif predicted_daily_demand > 0:
        days_until_stockout = round(current_stock / predicted_daily_demand, 1)
        stockout_dt = date.today() + timedelta(days=int(math.ceil(days_until_stockout)))
        predicted_stockout_date = stockout_dt.isoformat()
    else:
        days_until_stockout = None
        predicted_stockout_date = None

    # 5. Stockout Risk Classification
    # Prioritizes whether stock will run out before supplier restock can arrive!
    reasons: List[str] = []

    if current_stock == 0:
        risk_level = "CRITICAL"
        reasons.append("Inventory is completely depleted (0 units on hand). Immediate restock required.")
    elif days_until_stockout is not None and days_until_stockout <= (lead_time_days * 0.8):
        risk_level = "CRITICAL"
        reasons.append(
            f"Stockout will occur in ~{days_until_stockout} days, which is SHORTER than supplier lead time ({lead_time_days} days). "
            f"A stockout is imminent before reorders can arrive!"
        )
    elif (days_until_stockout is not None and days_until_stockout <= (lead_time_days * 1.5)) or current_stock <= minimum_stock:
        risk_level = "HIGH"
        if current_stock <= minimum_stock:
            reasons.append(f"Current stock ({current_stock} units) has fallen below minimum safety threshold ({minimum_stock} units).")
        if days_until_stockout is not None:
            reasons.append(f"Inventory will deplete in {days_until_stockout} days vs {lead_time_days} days supplier lead time.")
    elif (days_until_stockout is not None and days_until_stockout <= (lead_time_days * 3.0)) or trend_percentage >= 20.0:
        risk_level = "MEDIUM"
        if trend_percentage >= 20.0:
            reasons.append(f"Demand is surging (+{trend_percentage}% over the past 7 days).")
        reasons.append(f"Inventory coverage is moderate (~{days_until_stockout} days remaining).")
    else:
        risk_level = "LOW"
        reasons.append(f"Inventory is healthy ({current_stock} units). Coverage exceeds {days_until_stockout if days_until_stockout else '30+'} days.")

    if trend_percentage != 0:
        direction = "surged" if trend_percentage > 0 else "decreased"
        reasons.append(f"Sales velocity has {direction} by {abs(trend_percentage)}% recently.")

    # 6. Recommended Restock Quantity Calculation
    # If current stock is below reorder point or close to stockout, recommend replenishing up to comfortable buffer
    if current_stock <= reorder_point or risk_level in ["CRITICAL", "HIGH"]:
        # Target stock = Reorder Point + 14 days of cycle buffer
        cycle_buffer = int(math.ceil(predicted_daily_demand * 14))
        target_stock = min(maximum_stock, reorder_point + cycle_buffer)
        needed = target_stock - current_stock
        # Ensure we don't exceed max capacity and order at least 1 unit if low
        recommended_restock = max(0, min(needed, maximum_stock - current_stock))
        if recommended_restock == 0 and current_stock <= minimum_stock and maximum_stock > current_stock:
            recommended_restock = min(maximum_stock - current_stock, minimum_stock * 2)
    else:
        recommended_restock = 0

    # Human-readable explanation summary for UI cards
    explanation_summary = " | ".join(reasons[:2])

    explainability_payload = {
        "risk_level": risk_level,
        "reasons": reasons,
        "summary": explanation_summary,
        "factors": {
            "current_stock": current_stock,
            "minimum_stock": minimum_stock,
            "maximum_stock": maximum_stock,
            "supplier_lead_time_days": lead_time_days,
            "avg_daily_sales": avg_daily_sales,
            "predicted_daily_demand": predicted_daily_demand,
            "lead_time_demand": lead_time_demand,
            "calculated_safety_stock": safety_stock,
            "reorder_point": reorder_point,
            "trend_percentage": trend_percentage,
            "model_used": model_name,
            "confidence_label": confidence_label
        }
    }

    return {
        "risk_level": risk_level,
        "days_until_stockout": days_until_stockout,
        "predicted_stockout_date": predicted_stockout_date,
        "safety_stock": safety_stock,
        "lead_time_demand": lead_time_demand,
        "reorder_point": reorder_point,
        "recommended_restock": recommended_restock,
        "explainability": explainability_payload
    }
