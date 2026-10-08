from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, Field


class CouponBase(BaseModel):
    code: str = Field(..., min_length=2, max_length=50, description="Coupon code string e.g. DIWALI5")
    discount_percentage: float = Field(default=5.0, ge=0.1, le=100.0, description="Discount percentage e.g. 5.0")
    description: Optional[str] = Field(default=None, description="Coupon description")
    min_order_amount: float = Field(default=0.0, ge=0.0, description="Minimum order amount required")
    max_discount_amount: Optional[float] = Field(default=None, description="Maximum discount cap")
    is_active: bool = Field(default=True, description="Whether coupon is active")


class CouponCreate(CouponBase):
    pass


class CouponUpdate(BaseModel):
    code: Optional[str] = None
    discount_percentage: Optional[float] = None
    description: Optional[str] = None
    min_order_amount: Optional[float] = None
    max_discount_amount: Optional[float] = None
    is_active: Optional[bool] = None


class CouponResponse(CouponBase):
    id: int
    usage_count: int = 0
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    # Frontend camelCase aliases
    discountPercentage: Optional[float] = None
    minOrderAmount: Optional[float] = None
    maxDiscountAmount: Optional[float] = None
    isActive: Optional[bool] = None
    usageCount: Optional[int] = None

    class Config:
        from_attributes = True


class CouponValidateRequest(BaseModel):
    code: str = Field(..., description="Coupon code to validate")
    subtotal: float = Field(default=0.0, ge=0.0, description="Cart subtotal amount")


class CouponValidateResponse(BaseModel):
    valid: bool
    code: str
    discount_percentage: float = 0.0
    discount_amount: float = 0.0
    message: str
    discountPercentage: float = 0.0
    discountAmount: float = 0.0
