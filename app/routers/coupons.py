from typing import List
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.schemas.coupon import CouponResponse, CouponValidateRequest, CouponValidateResponse
from app.services.coupon_service import coupon_service

router = APIRouter(prefix="/coupons", tags=["Coupons"])


@router.post("/validate", response_model=CouponValidateResponse, summary="Validate Coupon Code")
def validate_coupon(req: CouponValidateRequest, db: Session = Depends(get_db)):
    return coupon_service.validate_coupon(db=db, code=req.code, subtotal=req.subtotal)


@router.get("/active", response_model=List[CouponResponse], summary="List Active Public Coupons")
def list_active_coupons(db: Session = Depends(get_db)):
    return coupon_service.list_coupons(db=db, active_only=True)
