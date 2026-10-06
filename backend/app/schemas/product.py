from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List

class ProductBase(BaseModel):
    name: str = Field(..., min_length=2, max_length=150)
    category: str = Field(..., min_length=2, max_length=100)
    sku: str = Field(..., min_length=2, max_length=50)
    description: Optional[str] = None
    current_stock: int = Field(default=0, ge=0)
    minimum_stock: int = Field(default=10, ge=0)
    maximum_stock: int = Field(default=100, ge=1)
    unit_price: float = Field(default=0.0, ge=0.0)
    supplier_name: Optional[str] = None
    supplier_contact: Optional[str] = None
    lead_time_days: int = Field(default=5, ge=1)

class ProductCreate(ProductBase):
    pass

class ProductUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=150)
    category: Optional[str] = Field(None, min_length=2, max_length=100)
    sku: Optional[str] = Field(None, min_length=2, max_length=50)
    description: Optional[str] = None
    current_stock: Optional[int] = Field(None, ge=0)
    minimum_stock: Optional[int] = Field(None, ge=0)
    maximum_stock: Optional[int] = Field(None, ge=1)
    unit_price: Optional[float] = Field(None, ge=0.0)
    supplier_name: Optional[str] = None
    supplier_contact: Optional[str] = None
    lead_time_days: Optional[int] = Field(None, ge=1)
    status: Optional[str] = None

class RestockRequest(BaseModel):
    quantity: int = Field(..., gt=0, description="Quantity to add to inventory")
    notes: Optional[str] = "Manual restock"

class AdjustmentRequest(BaseModel):
    new_stock: int = Field(..., ge=0, description="New absolute stock count")
    reason: Optional[str] = "Physical inventory count adjustment"

class ProductResponse(ProductBase):
    id: int
    status: str
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)

class ProductDetailResponse(ProductResponse):
    prediction: Optional[dict] = None
    recent_sales_count: int = 0
    total_revenue: float = 0.0
