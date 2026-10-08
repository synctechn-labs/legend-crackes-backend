from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.models.coupon import Coupon
from app.schemas.coupon import CouponCreate, CouponUpdate


class CouponRepository:
    def get_by_id(self, db: Session, coupon_id: int) -> Optional[Coupon]:
        return db.query(Coupon).filter(Coupon.id == coupon_id).first()

    def get_by_code(self, db: Session, code: str) -> Optional[Coupon]:
        clean_code = (code or "").strip().upper()
        return db.query(Coupon).filter(func.upper(Coupon.code) == clean_code).first()

    def list_coupons(self, db: Session, active_only: bool = False) -> List[Coupon]:
        query = db.query(Coupon)
        if active_only:
            query = query.filter(Coupon.is_active.is_(True))
        return query.order_by(Coupon.id.desc()).all()

    def create_coupon(self, db: Session, coupon_in: CouponCreate) -> Coupon:
        clean_code = coupon_in.code.strip().upper()
        coupon = Coupon(
            code=clean_code,
            discount_percentage=float(coupon_in.discount_percentage),
            description=coupon_in.description,
            min_order_amount=float(coupon_in.min_order_amount or 0.0),
            max_discount_amount=float(coupon_in.max_discount_amount) if coupon_in.max_discount_amount else None,
            is_active=coupon_in.is_active
        )
        db.add(coupon)
        db.commit()
        db.refresh(coupon)
        return coupon

    def update_coupon(self, db: Session, coupon: Coupon, update_data: CouponUpdate) -> Coupon:
        data = update_data.model_dump(exclude_unset=True)
        if "code" in data and data["code"]:
            data["code"] = data["code"].strip().upper()
        for key, value in data.items():
            setattr(coupon, key, value)
        db.commit()
        db.refresh(coupon)
        return coupon

    def toggle_active(self, db: Session, coupon: Coupon) -> Coupon:
        coupon.is_active = not coupon.is_active
        db.commit()
        db.refresh(coupon)
        return coupon

    def delete_coupon(self, db: Session, coupon: Coupon) -> bool:
        db.delete(coupon)
        db.commit()
        return True

    def increment_usage(self, db: Session, coupon_id: int):
        coupon = self.get_by_id(db, coupon_id)
        if coupon:
            coupon.usage_count = (coupon.usage_count or 0) + 1
            db.commit()

    def get_coupon_orders(self, db: Session, coupon_id: int) -> List[Any]:
        from app.models.order import Order
        coupon = self.get_by_id(db, coupon_id)
        if not coupon:
            return []
        clean_code = coupon.code.strip().upper()
        return db.query(Order).filter(
            func.upper(Order.coupon_code) == clean_code
        ).order_by(Order.created_at.desc()).all()


coupon_repo = CouponRepository()
