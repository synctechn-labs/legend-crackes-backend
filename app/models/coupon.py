from sqlalchemy import Column, Integer, String, Text, Numeric, Boolean, DateTime
from sqlalchemy.sql import func
from app.core.database import Base


class Coupon(Base):
    __tablename__ = "coupons"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    code = Column(String(50), unique=True, nullable=False, index=True)
    discount_percentage = Column(Numeric(5, 2), nullable=False, default=5.00)
    description = Column(Text, nullable=True)
    min_order_amount = Column(Numeric(10, 2), nullable=False, default=0.00)
    max_discount_amount = Column(Numeric(10, 2), nullable=True)
    is_active = Column(Boolean, nullable=False, default=True, index=True)
    usage_count = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    def __repr__(self):
        return f"<Coupon id={self.id} code='{self.code}' discount={self.discount_percentage}%>"
