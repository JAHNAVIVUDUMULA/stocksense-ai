from datetime import datetime, date
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query, UploadFile, File
from fastapi.responses import PlainTextResponse
from sqlalchemy.orm import Session
from sqlalchemy import desc
from app.database.session import get_db
from app.models.sale import Sale
from app.models.product import Product
from app.schemas.sale import SaleCreate, SaleResponse, CSVImportResult
from app.services.sales_service import record_sale, import_sales_csv

router = APIRouter(prefix="/sales", tags=["Sales"])

@router.get("", response_model=List[dict])
def list_sales(
    product_id: Optional[int] = None,
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db)
):
    """List sales transactions with product names and details."""
    query = db.query(Sale).join(Product)
    if product_id:
        query = query.filter(Sale.product_id == product_id)
    
    sales = query.order_by(desc(Sale.sale_date), desc(Sale.id)).offset(offset).limit(limit).all()
    
    return [
        {
            "id": s.id,
            "product_id": s.product_id,
            "product_name": s.product.name if s.product else None,
            "product_sku": s.product.sku if s.product else None,
            "quantity": s.quantity,
            "price": s.price,
            "total_revenue": round(s.quantity * s.price, 2),
            "sale_date": s.sale_date.isoformat(),
            "created_at": s.created_at.isoformat()
        }
        for s in sales
    ]

@router.post("", response_model=dict, status_code=status.HTTP_201_CREATED)
def create_sale(sale_in: SaleCreate, db: Session = Depends(get_db)):
    """
    Manually records a sale transaction:
    Validates stock availability, deducts inventory, and updates AI predictions automatically.
    """
    sale = record_sale(db, sale_in)
    return {
        "status": "success",
        "message": f"Recorded sale of {sale.quantity} units.",
        "sale_id": sale.id
    }

@router.post("/import", response_model=CSVImportResult)
async def import_sales(file: UploadFile = File(...), db: Session = Depends(get_db)):
    """
    Upload and parse a CSV file of sales transactions.
    Supports columns: product_id (or sku, product_name), date, quantity, price.
    """
    if not file.filename.endswith(".csv"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file must be a valid CSV file (.csv)"
        )

    content_bytes = await file.read()
    try:
        content_str = content_bytes.decode("utf-8")
    except UnicodeDecodeError:
        content_str = content_bytes.decode("latin-1")

    return import_sales_csv(db, content_str)

@router.get("/sample-csv", response_class=PlainTextResponse)
def get_sample_csv():
    """Returns sample CSV template content."""
    sample = (
        "sku,product_name,date,quantity,price\n"
        "MOU-WL-001,Wireless Ergonomic Mouse,2026-10-01,5,29.99\n"
        "KB-RGB-002,RGB Mechanical Keyboard,2026-10-01,2,89.99\n"
        "CAB-USBC-003,Braided USB-C Cable (2m),2026-10-02,6,12.99\n"
        "ACC-LST-004,Ergonomic Aluminum Laptop Stand,2026-10-02,3,44.99\n"
    )
    return sample
