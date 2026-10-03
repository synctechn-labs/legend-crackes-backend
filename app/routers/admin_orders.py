from typing import Optional
from datetime import datetime
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.dependencies import get_current_admin
from app.models.admin_user import AdminUser
from app.schemas.order import OrderResponse, OrderPaginatedResponse, OrderStatusUpdate, OrderExtraDiscountUpdate
from app.services.order_service import order_service

router = APIRouter(prefix="/admin/orders", tags=["Admin Orders"])


@router.get(
    "",
    response_model=OrderPaginatedResponse,
    summary="List Customer Orders (Admin)",
    description="Retrieve paginated customer orders with search (order number, customer name, phone) and status filter."
)
def get_admin_orders(
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=15, ge=1, le=100),
    search: Optional[str] = Query(default=None, description="Search by order number, customer name, or phone"),
    status: Optional[str] = Query(default=None, description="Filter by status (pending, confirmed, processing, shipped, delivered, cancelled)"),
    date_from: Optional[datetime] = Query(default=None),
    date_to: Optional[datetime] = Query(default=None),
    current_admin: AdminUser = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    return order_service.list_orders(
        db=db,
        page=page,
        limit=limit,
        search=search,
        status_filter=status,
        date_from=date_from,
        date_to=date_to
    )


@router.get(
    "/{id}",
    response_model=OrderResponse,
    summary="Get Order Details (Admin)",
    description="Retrieve detailed breakdown for an order including items and customer snapshot."
)
def get_admin_order_by_id(
    id: int,
    current_admin: AdminUser = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    return order_service.get_order_by_id(db=db, order_id=id)


@router.patch(
    "/{id}/status",
    response_model=OrderResponse,
    summary="Update Order Status (Admin)",
    description="Transition order status (e.g. pending -> confirmed -> processing -> shipped -> delivered, or cancelled)."
)
def update_order_status(
    id: int,
    status_payload: OrderStatusUpdate,
    current_admin: AdminUser = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    return order_service.update_order_status(
        db=db,
        order_id=id,
        new_status=status_payload.status,
        admin_username=current_admin.username
    )


@router.patch(
    "/{id}/extra-discount",
    response_model=OrderResponse,
    summary="Apply Admin Extra Discount from Profit (Admin)",
    description="Apply an extra discount % on the order deducted directly from the profit."
)
def apply_extra_discount(
    id: int,
    payload: OrderExtraDiscountUpdate,
    current_admin: AdminUser = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    return order_service.update_extra_discount(
        db=db,
        order_id=id,
        extra_discount_percentage=payload.extra_discount_percentage,
        admin_username=current_admin.username
    )


@router.delete(
    "/{id}",
    summary="Delete Order (Admin)",
    description="Permanently delete an order and its associated order items."
)
def delete_order(
    id: int,
    current_admin: AdminUser = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    return order_service.delete_order(
        db=db,
        order_id=id,
        admin_username=current_admin.username
    )
