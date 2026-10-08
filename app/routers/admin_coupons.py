from typing import List, Dict, Any
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.dependencies import get_current_admin
from app.models.admin_user import AdminUser
from app.schemas.coupon import CouponCreate, CouponUpdate, CouponResponse
from app.services.coupon_service import coupon_service

router = APIRouter(prefix="/admin/coupons", tags=["Admin Coupons"])


@router.get("", response_model=List[CouponResponse], summary="List All Coupons (Admin)")
def list_admin_coupons(
    current_admin: AdminUser = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    return coupon_service.list_coupons(db=db, active_only=False)


@router.post("", response_model=CouponResponse, status_code=status.HTTP_201_CREATED, summary="Create Coupon (Admin)")
def create_coupon(
    coupon_in: CouponCreate,
    current_admin: AdminUser = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    return coupon_service.create_coupon(db=db, coupon_in=coupon_in)


@router.put("/{coupon_id}", response_model=CouponResponse, summary="Update Coupon (Admin)")
def update_coupon(
    coupon_id: int,
    coupon_in: CouponUpdate,
    current_admin: AdminUser = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    return coupon_service.update_coupon(db=db, coupon_id=coupon_id, coupon_in=coupon_in)


@router.patch("/{coupon_id}/toggle", response_model=CouponResponse, summary="Toggle Coupon Active State (Admin)")
def toggle_coupon(
    coupon_id: int,
    current_admin: AdminUser = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    return coupon_service.toggle_active(db=db, coupon_id=coupon_id)


@router.delete("/{coupon_id}", response_model=Dict[str, Any], summary="Delete Coupon (Admin)")
def delete_coupon(
    coupon_id: int,
    current_admin: AdminUser = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    return coupon_service.delete_coupon(db=db, coupon_id=coupon_id)


@router.get("/{coupon_id}/orders", response_model=List[Dict[str, Any]], summary="Get Orders Placed Under Coupon (Admin)")
def get_coupon_orders(
    coupon_id: int,
    current_admin: AdminUser = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    return coupon_service.get_coupon_orders(db=db, coupon_id=coupon_id)
