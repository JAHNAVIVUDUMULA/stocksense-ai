from fastapi import APIRouter
from app.api.auth_routes import router as auth_router
from app.api.product_routes import router as product_router
from app.api.sales_routes import router as sales_router
from app.api.inventory_routes import router as inventory_router
from app.api.prediction_routes import router as prediction_router
from app.api.alert_routes import router as alert_router
from app.api.analytics_routes import router as analytics_router
from app.api.demo_routes import router as demo_router

api_router = APIRouter(prefix="/api")

api_router.include_router(auth_router)
api_router.include_router(product_router)
api_router.include_router(sales_router)
api_router.include_router(inventory_router)
api_router.include_router(prediction_router)
api_router.include_router(alert_router)
api_router.include_router(analytics_router)
api_router.include_router(demo_router)
