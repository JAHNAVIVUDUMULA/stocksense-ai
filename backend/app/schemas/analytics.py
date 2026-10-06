from typing import List, Dict, Any, Optional
from pydantic import BaseModel

class SummaryCards(BaseModel):
    total_products: int
    low_stock_products: int
    high_risk_products: int
    critical_risk_products: int
    stockout_soon_products: int
    pending_restock_recommendations: int
    total_revenue: float
    total_units_sold: int

class UrgentProduct(BaseModel):
    id: int
    name: str
    category: str
    sku: str
    current_stock: int
    lead_time_days: int
    average_daily_sales: float
    predicted_stockout_days: Optional[float]
    predicted_stockout_date: Optional[str]
    risk_level: str
    recommended_restock: int
    explanation_summary: str

class CategoryDistribution(BaseModel):
    category: str
    count: int
    total_stock: int

class RiskDistribution(BaseModel):
    risk_level: str
    count: int

class TrendPoint(BaseModel):
    date: str
    sales_units: int
    revenue: float

class AnalyticsDashboard(BaseModel):
    summary: SummaryCards
    urgent_products: List[UrgentProduct]
    category_distribution: List[CategoryDistribution]
    risk_distribution: List[RiskDistribution]
    recent_sales_trend: List[TrendPoint]
