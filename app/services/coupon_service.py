from typing import List, Dict, Any, Optional
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from app.repositories.coupon_repo import coupon_repo
from app.schemas.coupon import CouponCreate, CouponUpdate, CouponResponse, CouponValidateResponse
from app.models.coupon import Coupon


def format_coupon_response(c: Coupon) -> CouponResponse:
    pct = float(c.discount_percentage or 0.0)
    min_amt = float(c.min_order_amount or 0.0)
    max_amt = float(c.max_discount_amount) if c.max_discount_amount is not None else None
    uses = int(c.usage_count or 0)
    active = bool(c.is_active)

    return CouponResponse(
        id=c.id,
        code=c.code,
        discount_percentage=pct,
        description=c.description,
        min_order_amount=min_amt,
        max_discount_amount=max_amt,
        is_active=active,
        usage_count=uses,
        created_at=c.created_at,
        updated_at=c.updated_at,
        discountPercentage=pct,
        minOrderAmount=min_amt,
        maxDiscountAmount=max_amt,
        isActive=active,
        usageCount=uses,
    )


class CouponService:
    def list_coupons(self, db: Session, active_only: bool = False) -> List[CouponResponse]:
        coupons = coupon_repo.list_coupons(db, active_only=active_only)
        return [format_coupon_response(c) for c in coupons]

    def create_coupon(self, db: Session, coupon_in: CouponCreate) -> CouponResponse:
        clean_code = coupon_in.code.strip().upper()
        existing = coupon_repo.get_by_code(db, clean_code)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Coupon code '{clean_code}' already exists. Please use a unique code."
            )
        c = coupon_repo.create_coupon(db, coupon_in)
        return format_coupon_response(c)

    def update_coupon(self, db: Session, coupon_id: int, coupon_in: CouponUpdate) -> CouponResponse:
        coupon = coupon_repo.get_by_id(db, coupon_id)
        if not coupon:
            raise HTTPException(status_code=404, detail="Coupon not found")

        if coupon_in.code:
            clean_code = coupon_in.code.strip().upper()
            existing = coupon_repo.get_by_code(db, clean_code)
            if existing and existing.id != coupon_id:
                raise HTTPException(status_code=400, detail=f"Coupon code '{clean_code}' is already used by another coupon.")

        c = coupon_repo.update_coupon(db, coupon, coupon_in)
        return format_coupon_response(c)

    def toggle_active(self, db: Session, coupon_id: int) -> CouponResponse:
        coupon = coupon_repo.get_by_id(db, coupon_id)
        if not coupon:
            raise HTTPException(status_code=404, detail="Coupon not found")
        c = coupon_repo.toggle_active(db, coupon)
        return format_coupon_response(c)

    def delete_coupon(self, db: Session, coupon_id: int) -> Dict[str, Any]:
        coupon = coupon_repo.get_by_id(db, coupon_id)
        if not coupon:
            raise HTTPException(status_code=404, detail="Coupon not found")
        coupon_repo.delete_coupon(db, coupon)
        return {"success": True, "message": f"Coupon #{coupon_id} deleted successfully."}

    def validate_coupon(self, db: Session, code: str, subtotal: float) -> CouponValidateResponse:
        clean_code = (code or "").strip().upper()
        if not clean_code:
            return CouponValidateResponse(
                valid=False,
                code=clean_code,
                discount_percentage=0.0,
                discount_amount=0.0,
                message="Please enter a valid coupon code."
            )

        coupon = coupon_repo.get_by_code(db, clean_code)
        if not coupon:
            return CouponValidateResponse(
                valid=False,
                code=clean_code,
                discount_percentage=0.0,
                discount_amount=0.0,
                message=f"Coupon code '{clean_code}' is invalid or expired."
            )

        if not coupon.is_active:
            return CouponValidateResponse(
                valid=False,
                code=clean_code,
                discount_percentage=0.0,
                discount_amount=0.0,
                message=f"Coupon code '{clean_code}' is currently inactive."
            )

        min_amt = float(coupon.min_order_amount or 0.0)
        if subtotal < min_amt:
            return CouponValidateResponse(
                valid=False,
                code=clean_code,
                discount_percentage=float(coupon.discount_percentage),
                discount_amount=0.0,
                message=f"Coupon '{clean_code}' requires a minimum cart subtotal of ₹{int(min_amt):,}."
            )

        pct = float(coupon.discount_percentage or 5.0)
        discount_amount = round(subtotal * (pct / 100.0), 2)
        if coupon.max_discount_amount and float(coupon.max_discount_amount) > 0:
            max_disc = float(coupon.max_discount_amount)
            discount_amount = min(discount_amount, max_disc)

        return CouponValidateResponse(
            valid=True,
            code=clean_code,
            discount_percentage=pct,
            discount_amount=discount_amount,
            message=f"Success! {pct}% discount coupon '{clean_code}' applied (Saved ₹{discount_amount:,.2f}).",
            discountPercentage=pct,
            discountAmount=discount_amount
        )

    def get_coupon_orders(self, db: Session, coupon_id: int) -> List[Dict[str, Any]]:
        from app.utils.formatters import format_order_dict
        orders = coupon_repo.get_coupon_orders(db, coupon_id)
        return [format_order_dict(o) for o in orders]


coupon_service = CouponService()
