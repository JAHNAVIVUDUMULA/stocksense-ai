import io
import csv
from datetime import datetime, timezone, date
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from fastapi import HTTPException, status, UploadFile
from app.models.product import Product
from app.models.sale import Sale
from app.models.inventory_log import InventoryLog
from app.schemas.sale import SaleCreate, CSVImportResult
from app.services.prediction_service import update_single_product_prediction

def record_sale(db: Session, sale_in: SaleCreate) -> Sale:
    """
    Records a sale, decreases product stock, logs inventory movement,
    and updates prediction and risk automatically.
    """
    product = db.query(Product).filter(Product.id == sale_in.product_id).first()
    if not product:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")

    if sale_in.quantity <= 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Sale quantity must be greater than 0")

    if product.current_stock < sale_in.quantity:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Insufficient inventory. Available: {product.current_stock}, Requested sale: {sale_in.quantity}"
        )

    sale_price = sale_in.price if sale_in.price is not None else product.unit_price
    sale_dt = sale_in.sale_date or date.today()

    prev_stock = product.current_stock
    new_stock = prev_stock - sale_in.quantity

    # 1. Update product inventory
    product.current_stock = new_stock
    product.updated_at = datetime.now(timezone.utc)

    # 2. Add Sale record
    sale = Sale(
        product_id=product.id,
        quantity=sale_in.quantity,
        price=sale_price,
        sale_date=sale_dt,
        created_at=datetime.now(timezone.utc)
    )
    db.add(sale)

    # 3. Add Inventory log
    log = InventoryLog(
        product_id=product.id,
        change_type="SALE",
        quantity_changed=-sale_in.quantity,
        previous_stock=prev_stock,
        new_stock=new_stock,
        notes=f"Recorded sale of {sale_in.quantity} units",
        created_at=datetime.now(timezone.utc)
    )
    db.add(log)

    db.commit()
    db.refresh(sale)
    db.refresh(product)

    # 4. Trigger Prediction & Alert recalculation
    update_single_product_prediction(db, product)

    return sale

def import_sales_csv(db: Session, file_content: str) -> CSVImportResult:
    """
    Parses, validates, and imports sales records from a CSV file.
    Supports columns: product_id (or sku or product_name), date (or sale_date), quantity (or quantity_sold), price.
    """
    result = CSVImportResult(total_processed=0, successful=0, failed=0, errors=[])
    
    try:
        reader = csv.DictReader(io.StringIO(file_content))
    except Exception as e:
        result.errors.append(f"Failed to parse CSV file: {str(e)}")
        return result

    if not reader.fieldnames:
        result.errors.append("CSV file is empty or missing headers.")
        return result

    # Normalize header column names
    field_map = {}
    for col in reader.fieldnames:
        clean_col = col.strip().lower().replace(" ", "_")
        field_map[clean_col] = col

    # Check for required identifiers
    has_id = "product_id" in field_map or "sku" in field_map or "product_name" in field_map
    has_date = "date" in field_map or "sale_date" in field_map
    has_qty = "quantity" in field_map or "quantity_sold" in field_map

    if not (has_id and has_date and has_qty):
        missing = []
        if not has_id: missing.append("product_id (or sku, product_name)")
        if not has_date: missing.append("date (or sale_date)")
        if not has_qty: missing.append("quantity (or quantity_sold)")
        result.errors.append(f"CSV is missing required columns: {', '.join(missing)}")
        return result

    products_cache = {p.id: p for p in db.query(Product).all()}
    sku_cache = {p.sku.lower(): p for p in products_cache.values()}
    name_cache = {p.name.lower(): p for p in products_cache.values()}

    affected_product_ids = set()

    row_num = 1
    for row in reader:
        row_num += 1
        result.total_processed += 1

        # 1. Resolve product
        product = None
        if "product_id" in field_map and row.get(field_map["product_id"]):
            try:
                pid = int(row[field_map["product_id"]].strip())
                product = products_cache.get(pid)
            except ValueError:
                pass
        if not product and "sku" in field_map and row.get(field_map["sku"]):
            product = sku_cache.get(row[field_map["sku"]].strip().lower())
        if not product and "product_name" in field_map and row.get(field_map["product_name"]):
            product = name_cache.get(row[field_map["product_name"]].strip().lower())

        if not product:
            result.failed += 1
            result.errors.append(f"Row {row_num}: Product not found.")
            continue

        # 2. Parse quantity
        qty_key = "quantity" if "quantity" in field_map else "quantity_sold"
        raw_qty = row.get(field_map[qty_key], "").strip()
        try:
            quantity = int(raw_qty)
            if quantity <= 0:
                result.failed += 1
                result.errors.append(f"Row {row_num}: Quantity must be positive, got '{raw_qty}'.")
                continue
        except ValueError:
            result.failed += 1
            result.errors.append(f"Row {row_num}: Invalid quantity format '{raw_qty}'.")
            continue

        # 3. Parse date
        date_key = "date" if "date" in field_map else "sale_date"
        raw_date = row.get(field_map[date_key], "").strip()
        parsed_date = None
        for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%m/%d/%Y", "%Y/%m/%d", "%d/%m/%Y"):
            try:
                parsed_date = datetime.strptime(raw_date, fmt).date()
                break
            except ValueError:
                continue

        if not parsed_date:
            result.failed += 1
            result.errors.append(f"Row {row_num}: Invalid date format '{raw_date}'. Expected YYYY-MM-DD.")
            continue

        # 4. Parse price
        price = product.unit_price
        if "price" in field_map and row.get(field_map["price"]):
            try:
                price = float(row[field_map["price"]].strip().replace("$", "").replace(",", ""))
            except ValueError:
                price = product.unit_price

        # Record Sale
        sale = Sale(
            product_id=product.id,
            quantity=quantity,
            price=price,
            sale_date=parsed_date,
            created_at=datetime.now(timezone.utc)
        )
        db.add(sale)

        # Update product stock safely (clip at 0)
        prev_stock = product.current_stock
        new_stock = max(0, prev_stock - quantity)
        product.current_stock = new_stock

        log = InventoryLog(
            product_id=product.id,
            change_type="SALE",
            quantity_changed=-quantity,
            previous_stock=prev_stock,
            new_stock=new_stock,
            notes=f"CSV import sale on {parsed_date}",
            created_at=datetime.now(timezone.utc)
        )
        db.add(log)

        affected_product_ids.add(product.id)
        result.successful += 1

    db.commit()

    # Refresh predictions for affected products
    for pid in affected_product_ids:
        prod = products_cache.get(pid)
        if prod:
            update_single_product_prediction(db, prod)

    return result
