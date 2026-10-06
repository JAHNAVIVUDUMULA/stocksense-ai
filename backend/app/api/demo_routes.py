from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database.session import get_db
from app.services.demo_service import load_demo_data

router = APIRouter(prefix="/demo", tags=["Demo"])

@router.post("/load", response_model=dict)
def populate_demo_data(db: Session = Depends(get_db)):
    """
    Populates sample products, realistic 60-day historical sales,
    and calculates AI demand predictions and alerts for immediate presentation.
    """
    result = load_demo_data(db)
    return result
