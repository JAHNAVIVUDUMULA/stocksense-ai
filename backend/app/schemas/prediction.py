from datetime import datetime, date
from pydantic import BaseModel, ConfigDict
from typing import Optional, List, Any, Dict

class PredictionResponse(BaseModel):
    id: int
    product_id: int
    product_name: Optional[str] = None
    product_sku: Optional[str] = None
    current_stock: Optional[int] = None
    lead_time_days: Optional[int] = None
    predicted_daily_demand: float
    predicted_stockout_date: Optional[date] = None
    days_until_stockout: Optional[float] = None
    risk_level: str
    confidence: float
    confidence_label: str
    recommended_restock: int
    lead_time_demand: float
    safety_stock: int
    reorder_point: int
    model_used: str
    explainability: Optional[Dict[str, Any]] = None
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)

class ModelEvaluationMetrics(BaseModel):
    model_name: str
    mae: float
    rmse: float
    mape: Optional[float] = None
    data_points: int
    evaluation_period: str
