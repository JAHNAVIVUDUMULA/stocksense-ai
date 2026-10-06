import random
import math
from typing import Dict, Any
from datetime import date, timedelta, datetime, timezone
from sqlalchemy.orm import Session
from app.models.user import User
from app.models.product import Product
from app.models.sale import Sale
from app.models.inventory_log import InventoryLog
from app.models.prediction import Prediction
from app.models.alert import Alert
from app.auth.security import hash_password
from app.services.prediction_service import update_all_predictions

SAMPLE_PRODUCTS = [
    {
        "name": "Wireless Ergonomic Mouse",
        "category": "Peripherals",
        "sku": "MOU-WL-001",
        "description": "Ergonomic 2.4GHz wireless optical mouse with silent clicks and high precision.",
        "current_stock": 12,
        "minimum_stock": 15,
        "maximum_stock": 100,
        "unit_price": 29.99,
        "supplier_name": "LogiTech Solutions Inc.",
        "supplier_contact": "orders@logitech-supplies.com",
        "lead_time_days": 4,
        "base_daily_sales": 4.5,
        "trend_factor": 1.25 # Recent demand surge
    },
    {
        "name": "RGB Mechanical Keyboard",
        "category": "Keyboards",
        "sku": "KB-RGB-002",
        "description": "Custom mechanical keyboard with tactile brown switches and RGB backlighting.",
        "current_stock": 7,
        "minimum_stock": 12,
        "maximum_stock": 80,
        "unit_price": 89.99,
        "supplier_name": "KeyCraft Manufacturing",
        "supplier_contact": "sales@keycraftmfg.com",
        "lead_time_days": 7,
        "base_daily_sales": 2.2,
        "trend_factor": 1.10
    },
    {
        "name": "Braided USB-C Cable (2m)",
        "category": "Cables & Adapters",
        "sku": "CAB-USBC-003",
        "description": "Heavy-duty nylon braided 100W fast charging USB Type-C cable.",
        "current_stock": 95,
        "minimum_stock": 20,
        "maximum_stock": 200,
        "unit_price": 12.99,
        "supplier_name": "AnkerSupply Global",
        "supplier_contact": "support@ankersupply.net",
        "lead_time_days": 3,
        "base_daily_sales": 5.0,
        "trend_factor": 1.00
    },
    {
        "name": "Ergonomic Aluminum Laptop Stand",
        "category": "Accessories",
        "sku": "ACC-LST-004",
        "description": "Adjustable ventilated aluminum desktop riser for laptops up to 17 inches.",
        "current_stock": 18,
        "minimum_stock": 12,
        "maximum_stock": 60,
        "unit_price": 44.99,
        "supplier_name": "WorkSpace Dynamics",
        "supplier_contact": "contact@workspacedyn.com",
        "lead_time_days": 6,
        "base_daily_sales": 3.0,
        "trend_factor": 1.30 # Surging demand
    },
    {
        "name": "1080p HD Streaming Webcam",
        "category": "Peripherals",
        "sku": "CAM-1080P-005",
        "description": "Full HD 1080p video webcam with dual stereo noise-canceling microphones.",
        "current_stock": 3,
        "minimum_stock": 10,
        "maximum_stock": 50,
        "unit_price": 64.99,
        "supplier_name": "VisionTech Electronics",
        "supplier_contact": "b2b@visiontechelec.com",
        "lead_time_days": 5,
        "base_daily_sales": 2.8,
        "trend_factor": 1.20 # Imminent stockout!
    },
    {
        "name": "Fast-Charge Power Bank 20,000mAh",
        "category": "Power & Charging",
        "sku": "PWR-20K-006",
        "description": "High-capacity external battery pack with 65W PD fast charging output.",
        "current_stock": 68,
        "minimum_stock": 15,
        "maximum_stock": 120,
        "unit_price": 49.99,
        "supplier_name": "VoltTech Energy",
        "supplier_contact": "sales@volttech.io",
        "lead_time_days": 5,
        "base_daily_sales": 2.0,
        "trend_factor": 1.05
    },
    {
        "name": "Waterproof Bluetooth Speaker",
        "category": "Audio",
        "sku": "SPK-BT-007",
        "description": "Rugged IPX7 waterproof portable Bluetooth speaker with deep bass.",
        "current_stock": 0, # Out of stock
        "minimum_stock": 8,
        "maximum_stock": 50,
        "unit_price": 54.99,
        "supplier_name": "SoundWave Labs",
        "supplier_contact": "supply@soundwavelabs.com",
        "lead_time_days": 6,
        "base_daily_sales": 2.4,
        "trend_factor": 1.15
    },
    {
        "name": "7-Port Powered USB 3.0 Hub",
        "category": "Accessories",
        "sku": "HUB-USB7-008",
        "description": "High-speed 5Gbps USB hub with individual power switches and 36W adapter.",
        "current_stock": 11,
        "minimum_stock": 15,
        "maximum_stock": 75,
        "unit_price": 27.50,
        "supplier_name": "ConnectPlus Hardware",
        "supplier_contact": "support@connectplus.com",
        "lead_time_days": 5,
        "base_daily_sales": 3.8,
        "trend_factor": 1.18
    }
]

def load_demo_data(db: Session) -> Dict[str, Any]:
    """
    Safely seeds the database with realistic demo products, 60 days of historical sales,
    and runs the AI prediction engine to immediately generate alerts, explainability, and analytics.
    """
    # 1. Ensure Demo User exists
    demo_user = db.query(User).filter(User.email == "vendor@stocksense.ai").first()
    if not demo_user:
        demo_user = User(
            name="Demo Store Manager",
            email="vendor@stocksense.ai",
            password_hash=hash_password("password123"),
            role="vendor",
            created_at=datetime.now(timezone.utc)
        )
        db.add(demo_user)
        db.commit()

    # Clear existing demo data cleanly if re-triggering
    existing_skus = [p["sku"] for p in SAMPLE_PRODUCTS]
    db.query(Product).filter(Product.sku.in_(existing_skus)).delete(synchronize_session=False)
    db.commit()

    created_products = []
    total_sales_count = 0

    random.seed(42) # Consistent realistic patterns for demonstration

    today = date.today()
    days_history = 60

    for prod_meta in SAMPLE_PRODUCTS:
        product = Product(
            name=prod_meta["name"],
            category=prod_meta["category"],
            sku=prod_meta["sku"],
            description=prod_meta["description"],
            current_stock=prod_meta["current_stock"],
            minimum_stock=prod_meta["minimum_stock"],
            maximum_stock=prod_meta["maximum_stock"],
            unit_price=prod_meta["unit_price"],
            supplier_name=prod_meta["supplier_name"],
            supplier_contact=prod_meta["supplier_contact"],
            lead_time_days=prod_meta["lead_time_days"],
            status="IN_STOCK",
            created_at=datetime.now(timezone.utc) - timedelta(days=days_history),
            updated_at=datetime.now(timezone.utc)
        )
        db.add(product)
        db.commit()
        db.refresh(product)
        created_products.append(product)

        # Initial stock log
        init_log = InventoryLog(
            product_id=product.id,
            change_type="RESTOCK",
            quantity_changed=product.maximum_stock,
            previous_stock=0,
            new_stock=product.maximum_stock,
            notes="Initial bulk stock allocation (Demo Data)",
            created_at=datetime.now(timezone.utc) - timedelta(days=days_history)
        )
        db.add(init_log)

        # Generate 60 days of sales
        base_demand = prod_meta["base_daily_sales"]
        trend = prod_meta["trend_factor"]

        for day_offset in range(days_history, 0, -1):
            sale_date = today - timedelta(days=day_offset)
            dow = sale_date.weekday()

            # Weekly seasonality (weekend spike on Fri/Sat)
            weekend_multiplier = 1.35 if dow in [4, 5] else (0.85 if dow == 6 else 1.0)
            
            # Trend ramp over last 14 days
            recent_ramp = trend if day_offset <= 14 else 1.0
            
            # Noise & Poisson-like variation
            expected = base_demand * weekend_multiplier * recent_ramp
            actual_qty = max(0, int(round(random.gauss(expected, max(0.8, expected * 0.25)))))

            # Don't create zero sales every single time, but allow occasional 0
            if actual_qty > 0:
                sale = Sale(
                    product_id=product.id,
                    quantity=actual_qty,
                    price=product.unit_price,
                    sale_date=sale_date,
                    created_at=datetime.now(timezone.utc) - timedelta(days=day_offset)
                )
                db.add(sale)
                total_sales_count += 1

    db.commit()

    # Run AI Prediction Engine across all products
    predictions = update_all_predictions(db)

    return {
        "status": "success",
        "message": "Demo data loaded successfully.",
        "products_created": len(created_products),
        "sales_recorded": total_sales_count,
        "predictions_generated": len(predictions),
        "demo_account": {
            "email": "vendor@stocksense.ai",
            "password": "password123"
        }
    }
