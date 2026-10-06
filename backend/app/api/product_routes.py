import json
from datetime import datetime, timezone
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_, desc, asc
from app.database.session import get_db
from app.models.product import Product
from app.models.sale import Sale
from app.models.inventory_log import InventoryLog
from app.models.prediction import Prediction
from app.schemas.product import ProductCreate, ProductUpdate, ProductResponse
from app.services.prediction_service import update_single_product_prediction

router = APIRouter(prefix="/products", tags=["Products"])

@router.get("", response_model=List[dict])
def list_products(
    search: Optional[str] = None,
    filter_by: Optional[str] = Query("all", description="all, in_stock, low_stock, high_risk, critical, out_of_stock"),
    sort_by: Optional[str] = Query("risk", description="risk, stock_asc, stock_desc, demand, soonest, name"),
    category: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Lists products with flexible search, category filtering, status filtering, and sorting.
    Returns combined product, prediction, and stockout information.
    """
    query = db.query(Product)

    # Search filter
    if search:
        s = f"%{search.strip()}%"
        query = query.filter(
            or_(
                Product.name.ilike(s),
                Product.sku.ilike(s),
                Product.category.ilike(s),
                Product.supplier_name.ilike(s)
            )
        )

    # Category filter
    if category and category.lower() != "all":
        query = query.filter(Product.category == category)

    # Status / Risk filter
    if filter_by and filter_by.lower() != "all":
        f = filter_by.upper()
        if f == "LOW_STOCK":
            query = query.filter(Product.current_stock <= Product.minimum_stock, Product.current_stock > 0)
        elif f == "OUT_OF_STOCK":
            query = query.filter(Product.current_stock == 0)
        elif f in ["HIGH_RISK", "CRITICAL"]:
            query = query.join(Prediction).filter(Prediction.risk_level == f)
        elif f == "IN_STOCK":
            query = query.filter(Product.current_stock > Product.minimum_stock)

    products = query.all()

    # Pre-fetch predictions map
    predictions_map = {p.product_id: p for p in db.query(Prediction).all()}

    # Format output items
    results = []
    for p in products:
        pred = predictions_map.get(p.id)
        expl_summary = ""
        if pred and pred.explainability_json:
            try:
                expl = json.loads(pred.explainability_json)
                expl_summary = expl.get("summary", "")
            except Exception:
                pass

        results.append({
            "id": p.id,
            "name": p.name,
            "category": p.category,
            "sku": p.sku,
            "description": p.description,
            "current_stock": p.current_stock,
            "minimum_stock": p.minimum_stock,
            "maximum_stock": p.maximum_stock,
            "unit_price": p.unit_price,
            "supplier_name": p.supplier_name,
            "supplier_contact": p.supplier_contact,
            "lead_time_days": p.lead_time_days,
            "status": p.status,
            "created_at": p.created_at.isoformat() if p.created_at else None,
            "updated_at": p.updated_at.isoformat() if p.updated_at else None,
            "prediction": {
                "predicted_daily_demand": pred.predicted_daily_demand if pred else 0.0,
                "predicted_stockout_date": pred.predicted_stockout_date.isoformat() if (pred and pred.predicted_stockout_date) else None,
                "days_until_stockout": pred.days_until_stockout if pred else None,
                "risk_level": pred.risk_level if pred else "LOW",
                "confidence": pred.confidence if pred else 0.5,
                "confidence_label": pred.confidence_label if pred else "Medium",
                "recommended_restock": pred.recommended_restock if pred else 0,
                "lead_time_demand": pred.lead_time_demand if pred else 0.0,
                "safety_stock": pred.safety_stock if pred else 0,
                "reorder_point": pred.reorder_point if pred else 0,
                "model_used": pred.model_used if pred else "Baseline",
                "explanation_summary": expl_summary
            } if pred else None
        })

    # Sort results
    risk_rank = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}
    if sort_by == "risk":
        results.sort(key=lambda x: (risk_rank.get(x["prediction"]["risk_level"] if x["prediction"] else "LOW", 4), x["current_stock"]))
    elif sort_by == "stock_asc":
        results.sort(key=lambda x: x["current_stock"])
    elif sort_by == "stock_desc":
        results.sort(key=lambda x: x["current_stock"], reverse=True)
    elif sort_by == "demand":
        results.sort(key=lambda x: (x["prediction"]["predicted_daily_demand"] if x["prediction"] else 0), reverse=True)
    elif sort_by == "soonest":
        results.sort(key=lambda x: (x["prediction"]["days_until_stockout"] if (x["prediction"] and x["prediction"]["days_until_stockout"] is not None) else 9999))
    elif sort_by == "name":
        results.sort(key=lambda x: x["name"].lower())

    return results

@router.post("", response_model=dict, status_code=status.HTTP_201_CREATED)
def create_product(product_in: ProductCreate, db: Session = Depends(get_db)):
    """Create a new product, log initial inventory, and initialize AI prediction."""
    existing_sku = db.query(Product).filter(Product.sku == product_in.sku.strip()).first()
    if existing_sku:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Product with SKU '{product_in.sku}' already exists."
        )

    product = Product(
        name=product_in.name.strip(),
        category=product_in.category.strip(),
        sku=product_in.sku.strip(),
        description=product_in.description.strip() if product_in.description else None,
        current_stock=product_in.current_stock,
        minimum_stock=product_in.minimum_stock,
        maximum_stock=product_in.maximum_stock,
        unit_price=product_in.unit_price,
        supplier_name=product_in.supplier_name.strip() if product_in.supplier_name else None,
        supplier_contact=product_in.supplier_contact.strip() if product_in.supplier_contact else None,
        lead_time_days=product_in.lead_time_days,
        status="IN_STOCK" if product_in.current_stock > product_in.minimum_stock else "LOW_STOCK"
    )
    db.add(product)
    db.commit()
    db.refresh(product)

    # Initial inventory log
    if product.current_stock > 0:
        log = InventoryLog(
            product_id=product.id,
            change_type="ADJUSTMENT",
            quantity_changed=product.current_stock,
            previous_stock=0,
            new_stock=product.current_stock,
            notes="Initial stock at product creation"
        )
        db.add(log)
        db.commit()

    # Generate initial prediction
    update_single_product_prediction(db, product)

    return {"status": "success", "message": f"Product '{product.name}' created.", "id": product.id}

@router.get("/{product_id}", response_model=dict)
def get_product(product_id: int, db: Session = Depends(get_db)):
    """
    Returns full details for a product including its AI prediction breakdown,
    explainability details, 30-day sales history, and inventory logs.
    """
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")

    pred = db.query(Prediction).filter(Prediction.product_id == product.id).first()
    expl_data = {}
    if pred and pred.explainability_json:
        try:
            expl_data = json.loads(pred.explainability_json)
        except Exception:
            pass

    # Sales history
    sales = db.query(Sale).filter(Sale.product_id == product.id).order_by(desc(Sale.sale_date)).limit(60).all()
    sales_list = [
        {
            "id": s.id,
            "sale_date": s.sale_date.isoformat(),
            "quantity": s.quantity,
            "price": s.price,
            "revenue": round(s.quantity * s.price, 2)
        }
        for s in sales
    ]

    # Inventory movement logs
    logs = db.query(InventoryLog).filter(InventoryLog.product_id == product.id).order_by(desc(InventoryLog.created_at)).limit(20).all()
    logs_list = [
        {
            "id": l.id,
            "change_type": l.change_type,
            "quantity_changed": l.quantity_changed,
            "previous_stock": l.previous_stock,
            "new_stock": l.new_stock,
            "notes": l.notes,
            "created_at": l.created_at.isoformat()
        }
        for l in logs
    ]

    return {
        "id": product.id,
        "name": product.name,
        "category": product.category,
        "sku": product.sku,
        "description": product.description,
        "current_stock": product.current_stock,
        "minimum_stock": product.minimum_stock,
        "maximum_stock": product.maximum_stock,
        "unit_price": product.unit_price,
        "supplier_name": product.supplier_name,
        "supplier_contact": product.supplier_contact,
        "lead_time_days": product.lead_time_days,
        "status": product.status,
        "created_at": product.created_at.isoformat(),
        "updated_at": product.updated_at.isoformat(),
        "prediction": {
            "predicted_daily_demand": pred.predicted_daily_demand if pred else 0.0,
            "predicted_stockout_date": pred.predicted_stockout_date.isoformat() if (pred and pred.predicted_stockout_date) else None,
            "days_until_stockout": pred.days_until_stockout if pred else None,
            "risk_level": pred.risk_level if pred else "LOW",
            "confidence": pred.confidence if pred else 0.5,
            "confidence_label": pred.confidence_label if pred else "Medium",
            "recommended_restock": pred.recommended_restock if pred else 0,
            "lead_time_demand": pred.lead_time_demand if pred else 0.0,
            "safety_stock": pred.safety_stock if pred else 0,
            "reorder_point": pred.reorder_point if pred else 0,
            "model_used": pred.model_used if pred else "Baseline",
            "explainability": expl_data
        } if pred else None,
        "recent_sales": sales_list,
        "inventory_logs": logs_list
    }

@router.put("/{product_id}", response_model=dict)
def update_product(product_id: int, product_in: ProductUpdate, db: Session = Depends(get_db)):
    """Update product information."""
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")

    if product_in.sku and product_in.sku.strip() != product.sku:
        existing = db.query(Product).filter(Product.sku == product_in.sku.strip(), Product.id != product_id).first()
        if existing:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="SKU already in use by another product")
        product.sku = product_in.sku.strip()

    if product_in.name is not None: product.name = product_in.name.strip()
    if product_in.category is not None: product.category = product_in.category.strip()
    if product_in.description is not None: product.description = product_in.description.strip()
    if product_in.minimum_stock is not None: product.minimum_stock = product_in.minimum_stock
    if product_in.maximum_stock is not None: product.maximum_stock = product_in.maximum_stock
    if product_in.unit_price is not None: product.unit_price = product_in.unit_price
    if product_in.supplier_name is not None: product.supplier_name = product_in.supplier_name.strip()
    if product_in.supplier_contact is not None: product.supplier_contact = product_in.supplier_contact.strip()
    if product_in.lead_time_days is not None: product.lead_time_days = product_in.lead_time_days
    
    if product_in.current_stock is not None and product_in.current_stock != product.current_stock:
        prev = product.current_stock
        product.current_stock = product_in.current_stock
        log = InventoryLog(
            product_id=product.id,
            change_type="ADJUSTMENT",
            quantity_changed=product.current_stock - prev,
            previous_stock=prev,
            new_stock=product.current_stock,
            notes="Updated via Product Edit"
        )
        db.add(log)

    product.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(product)

    # Re-evaluate predictions with updated parameters
    update_single_product_prediction(db, product)

    return {"status": "success", "message": f"Product '{product.name}' updated successfully."}

@router.delete("/{product_id}", response_model=dict)
def delete_product(product_id: int, db: Session = Depends(get_db)):
    """Deletes product and its related records."""
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")

    prod_name = product.name
    db.delete(product)
    db.commit()
    return {"status": "success", "message": f"Product '{prod_name}' deleted."}
