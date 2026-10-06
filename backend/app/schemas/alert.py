from datetime import datetime
from pydantic import BaseModel, ConfigDict
from typing import Optional

class AlertResponse(BaseModel):
    id: int
    product_id: int
    product_name: Optional[str] = None
    product_sku: Optional[str] = None
    alert_type: str
    severity: str
    message: str
    recommended_action: Optional[str] = None
    is_read: bool
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

class AlertCountResponse(BaseModel):
    total_unread: int
    critical_count: int
    high_count: int
    medium_count: int
    low_count: int
