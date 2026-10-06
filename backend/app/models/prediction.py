from datetime import datetime, timezone, date
from sqlalchemy import Column, Integer, Float, String, Date, DateTime, Text, ForeignKey
from sqlalchemy.orm import relationship
from app.database.base import Base

class Prediction(Base):
    __tablename__ = "predictions"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id", ondelete="CASCADE"), unique=True, nullable=False, index=True)
    predicted_daily_demand = Column(Float, default=0.0, nullable=False)
    predicted_stockout_date = Column(Date, nullable=True)
    days_until_stockout = Column(Float, nullable=True)
    risk_level = Column(String(50), default="LOW", nullable=False)  # LOW, MEDIUM, HIGH, CRITICAL
    confidence = Column(Float, default=0.5, nullable=False)  # 0.0 to 1.0
    confidence_label = Column(String(50), default="Medium", nullable=False)  # High, Medium, Low
    recommended_restock = Column(Integer, default=0, nullable=False)
    lead_time_demand = Column(Float, default=0.0, nullable=False)
    safety_stock = Column(Integer, default=0, nullable=False)
    reorder_point = Column(Integer, default=0, nullable=False)
    model_used = Column(String(100), default="Baseline", nullable=False)
    explainability_json = Column(Text, nullable=True)  # JSON serialized list of explanations & metrics
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    product = relationship("Product", back_populates="prediction")
