from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Float, DateTime
from sqlalchemy.orm import relationship
from app.database.base import Base

class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(150), nullable=False, index=True)
    category = Column(String(100), nullable=False, index=True)
    sku = Column(String(50), unique=True, index=True, nullable=False)
    description = Column(String(500), nullable=True)
    current_stock = Column(Integer, default=0, nullable=False)
    minimum_stock = Column(Integer, default=10, nullable=False)
    maximum_stock = Column(Integer, default=100, nullable=False)
    unit_price = Column(Float, default=0.0, nullable=False)
    supplier_name = Column(String(150), nullable=True)
    supplier_contact = Column(String(100), nullable=True)
    lead_time_days = Column(Integer, default=5, nullable=False)
    status = Column(String(50), default="IN_STOCK", nullable=False)  # IN_STOCK, LOW_STOCK, HIGH_RISK, CRITICAL, OUT_OF_STOCK
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    sales = relationship("Sale", back_populates="product", cascade="all, delete-orphan")
    inventory_logs = relationship("InventoryLog", back_populates="product", cascade="all, delete-orphan")
    prediction = relationship("Prediction", back_populates="product", uselist=False, cascade="all, delete-orphan")
    alerts = relationship("Alert", back_populates="product", cascade="all, delete-orphan")
