from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.dependencies import get_current_admin
from app.models.admin_user import AdminUser
from app.schemas.customer import (
    CustomerPaginatedResponse,
    CustomerDetailResponse,
    CustomerMetricsResponse
)
from app.services.customer_service import customer_service

router = APIRouter(prefix="/admin/customers", tags=["Admin Customer Management"])


@router.get(
    "",
    response_model=CustomerPaginatedResponse,
    summary="List Customers (Admin Only)",
    description="Retrieve paginated list of guest & repeat customers with search by customer code, name, phone, email, and city."
)
def list_customers(
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
    search: Optional[str] = Query(default=None, description="Search term for code, name, phone, email, city"),
    phone: Optional[str] = Query(default=None, description="Filter by phone number"),
    sort_by: str = Query(default="recent", description="Sort order: recent, oldest, name"),
    current_admin: AdminUser = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    return customer_service.list_customers(
        db=db,
        page=page,
        limit=limit,
        search=search,
        phone=phone,
        sort_by=sort_by
    )


@router.get(
    "/metrics",
    response_model=CustomerMetricsResponse,
    summary="Customer Analytics Metrics (Admin Only)",
    description="Retrieve total customers, new customers, returning customers, repeat customer rate, and average spend."
)
def get_customer_metrics(
    current_admin: AdminUser = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    return customer_service.get_customer_metrics(db=db)


@router.get(
    "/{customer_id}",
    response_model=CustomerDetailResponse,
    summary="Get Customer Details (Admin Only)",
    description="Retrieve detailed customer profile, aggregate financial metrics, and order history."
)
def get_customer_detail(
    customer_id: int,
    current_admin: AdminUser = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    return customer_service.get_customer_detail(db=db, customer_id=customer_id)


@router.get(
    "/{customer_id}/orders",
    summary="Get Customer Orders (Admin Only)",
    description="Retrieve all historical orders associated with a specific customer."
)
def get_customer_orders(
    customer_id: int,
    current_admin: AdminUser = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    return customer_service.get_customer_orders(db=db, customer_id=customer_id)
