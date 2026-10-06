from datetime import datetime, date
from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List

class SaleCreate(BaseModel):
    product_id: int = Field(..., gt=0)
    quantity: int = Field(..., gt=0)
    sale_date: Optional[date] = None
    price: Optional[float] = Field(None, ge=0.0)

class SaleResponse(BaseModel):
    id: int
    product_id: int
    product_name: Optional[str] = None
    product_sku: Optional[str] = None
    quantity: int
    price: float
    sale_date: date
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

class CSVImportResult(BaseModel):
    total_processed: int
    successful: int
    failed: int
    errors: List[str] = []
