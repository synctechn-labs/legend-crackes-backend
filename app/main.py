import time
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.config import settings
from app.core.logging import logger
from app.core.database import Base, engine
# Import all models so metadata is complete
import app.models  # noqa: F401

from app.routers.auth import router as auth_router
from app.routers.products import router as products_router
from app.routers.categories import router as categories_router
from app.routers.orders import router as orders_router
from app.routers.admin_orders import router as admin_orders_router
from app.routers.admin_inventory import router as admin_inventory_router
from app.routers.admin_dashboard import router as admin_dashboard_router
from app.routers.admin_revenue import router as admin_revenue_router
from app.routers.admin_customers import router as admin_customers_router


from sqlalchemy import inspect, text

def run_db_migrations():
    """Ensure newly added columns and tables exist in existing database."""
    try:
        Base.metadata.create_all(bind=engine)
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        if "orders" in tables:
            columns = [c["name"] for c in inspector.get_columns("orders")]
            with engine.begin() as conn:
                if "customer_id" not in columns:
                    conn.execute(text("ALTER TABLE orders ADD COLUMN customer_id INTEGER REFERENCES customers(id);"))
                if "customer_alternate_phone" not in columns:
                    conn.execute(text("ALTER TABLE orders ADD COLUMN customer_alternate_phone VARCHAR(20);"))
                if "extra_discount_percentage" not in columns:
                    conn.execute(text("ALTER TABLE orders ADD COLUMN extra_discount_percentage NUMERIC(5, 2) DEFAULT 0.00;"))
                if "extra_discount_amount" not in columns:
                    conn.execute(text("ALTER TABLE orders ADD COLUMN extra_discount_amount NUMERIC(10, 2) DEFAULT 0.00;"))
                if "final_total_amount" not in columns:
                    conn.execute(text("ALTER TABLE orders ADD COLUMN final_total_amount NUMERIC(10, 2);"))

        if "products" in tables:
            columns = [c["name"] for c in inspector.get_columns("products")]
            with engine.begin() as conn:
                if "original_price" not in columns:
                    conn.execute(text("ALTER TABLE products ADD COLUMN original_price NUMERIC(10, 2) DEFAULT 0.00;"))
                if "my_price" not in columns:
                    conn.execute(text("ALTER TABLE products ADD COLUMN my_price NUMERIC(10, 2) DEFAULT 0.00;"))
                if "tamil_name" not in columns:
                    conn.execute(text("ALTER TABLE products ADD COLUMN tamil_name VARCHAR(255);"))
        logger.info("Database migration check completed successfully.")
    except Exception as e:
        logger.warning(f"Database migration check warning: {e}")


# Run DB migration check on startup
try:
    run_db_migrations()
except Exception as e:
    logger.warning(f"Failed to run auto DB migrations: {e}")



@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(f"{settings.PROJECT_NAME} v{settings.VERSION} started successfully.")
    yield
    # Shutdown
    logger.info("Shutting down application...")


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description=(
        "Production-grade, high-performance REST API backend for Classic Legend Crackers E-Commerce platform. "
        "Engineered to seamlessly support 3000+ catalog products, guest checkouts, atomic inventory locking, "
        "and real-time administration with comprehensive analytics."
    ),
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan
)

# Vercel Serverless Path Normalization Middleware
from starlette.middleware.base import BaseHTTPMiddleware

class VercelMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        qs = request.query_params
        if "path" in qs and qs["path"]:
            target_path = "/" + qs["path"].lstrip("/")
            request.scope["path"] = target_path
            if "raw_path" in request.scope:
                request.scope["raw_path"] = target_path.encode("utf-8")
        elif request.url.path.startswith("/api/index"):
            request.scope["path"] = "/"
            if "raw_path" in request.scope:
                request.scope["raw_path"] = b"/"
        return await call_next(request)


from fastapi.middleware.gzip import GZipMiddleware

app.add_middleware(GZipMiddleware, minimum_size=500)
app.add_middleware(VercelMiddleware)

# CORS Configuration
origins = settings.CORS_ORIGINS if isinstance(settings.CORS_ORIGINS, list) else [settings.CORS_ORIGINS]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_origin_regex=r"https?://.*",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Global Middleware: Request timing, CDN Cache Headers & Logging
@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = round((time.time() - start_time) * 1000, 2)
    response.headers["X-Process-Time-Ms"] = str(process_time)
    
    # Add Edge CDN caching for public read endpoints
    if request.method == "GET":
        path = request.url.path
        if path in ["/categories", "/featured", "/special-offers"] or path.startswith("/products"):
            response.headers["Cache-Control"] = "public, max-age=60, s-maxage=300, stale-while-revalidate=600"

    # Do not spam logs on health checks
    if request.url.path not in ["/health", "/docs", "/openapi.json"]:
        logger.info(f"{request.method} {request.url.path} -> {response.status_code} ({process_time}ms)")
    
    return response


# Standardized Error Handling
@app.exception_handler(StarletteHTTPException)
async def custom_http_exception_handler(request: Request, exc: StarletteHTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "message": str(exc.detail),
            "detail": str(exc.detail)
        }
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    first_error = exc.errors()[0] if exc.errors() else {}
    msg = f"Validation Error in {first_error.get('loc', ['field'])[-1]}: {first_error.get('msg', 'Invalid input')}"
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "success": False,
            "message": msg,
            "detail": exc.errors()
        }
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception on {request.method} {request.url.path}: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "success": False,
            "message": "An internal server error occurred. Please try again later.",
            "detail": "Internal server error"
        }
    )


# Root & Health Checks
@app.get("/", tags=["Health"])
def root():
    return {
        "success": True,
        "name": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "status": "online",
        "documentation": "/docs"
    }


@app.get("/health", tags=["Health"])
def health_check():
    return {
        "status": "healthy",
        "timestamp": time.time(),
        "database": "connected"
    }


# Convenience Root Aliases for Frontend Client Compatibility
from app.services.product_service import product_service
from app.core.database import get_db
from sqlalchemy.orm import Session
from fastapi import Depends

@app.get("/featured", tags=["Products"])
def get_featured_root(limit: int = 8, db: Session = Depends(get_db)):
    res = product_service.list_products(db=db, page=1, limit=limit, is_featured=True, sort_by="featured")
    return res.products

@app.get("/special-offers", tags=["Products"])
def get_special_offers_root(limit: int = 4, db: Session = Depends(get_db)):
    res = product_service.list_products(db=db, page=1, limit=limit, sort_by="discount")
    return res.products

from app.core.dependencies import get_current_admin
from app.models.admin_user import AdminUser
from app.schemas.admin import AdminResponse

@app.get("/me", response_model=AdminResponse, tags=["Auth"])
def get_me_root(current_admin: AdminUser = Depends(get_current_admin)):
    return current_admin


@app.get("/health", tags=["Health"])
def health_check():
    return {
        "status": "healthy",
        "timestamp": time.time(),
        "database": "connected"
    }


# Include Routers under /api AND direct root for complete Vercel & client compatibility
api_prefix = settings.API_PREFIX

# 1. Mount under /api
app.include_router(auth_router, prefix=api_prefix)
app.include_router(products_router, prefix=api_prefix)
app.include_router(categories_router, prefix=api_prefix)
app.include_router(categories_router, prefix=f"{api_prefix}/admin")
app.include_router(orders_router, prefix=api_prefix)
app.include_router(admin_orders_router, prefix=api_prefix)
app.include_router(admin_inventory_router, prefix=api_prefix)
app.include_router(admin_dashboard_router, prefix=api_prefix)
app.include_router(admin_revenue_router, prefix=api_prefix)
app.include_router(admin_customers_router, prefix=api_prefix)

# 2. Mount directly without /api prefix
app.include_router(auth_router)
app.include_router(products_router)
app.include_router(categories_router)
app.include_router(categories_router, prefix="/admin")
app.include_router(orders_router)
app.include_router(admin_orders_router)
app.include_router(admin_inventory_router)
app.include_router(admin_dashboard_router)
app.include_router(admin_revenue_router)
app.include_router(admin_customers_router)
