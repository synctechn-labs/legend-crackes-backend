from sqlalchemy import Column, Integer, String, Text, Numeric, DateTime, ForeignKey, Index
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.core.database import Base


class Order(Base):
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    order_number = Column(String(64), unique=True, nullable=False, index=True)
    customer_name = Column(String(150), nullable=False)
    customer_phone = Column(String(20), nullable=False, index=True)
    customer_alternate_phone = Column(String(20), nullable=True)
    customer_email = Column(String(120), nullable=True)
    address = Column(Text, nullable=False)
    city = Column(String(100), nullable=False)
    state = Column(String(100), nullable=False)
    pincode = Column(String(10), nullable=False)
    
    # Financial breakdown
    subtotal = Column(Numeric(10, 2), nullable=False)
    discount = Column(Numeric(10, 2), default=0.00, nullable=False)
    delivery_charge = Column(Numeric(10, 2), default=0.00, nullable=False)
    total_amount = Column(Numeric(10, 2), nullable=False)
    
    # Statuses
    payment_method = Column(String(50), default="Cash on Delivery", nullable=False)
    payment_status = Column(String(50), default="Pending", nullable=False)
    order_status = Column(String(50), default="Pending", nullable=False, index=True)
    
    # Extra admin discount deducted from profit
    extra_discount_percentage = Column(Numeric(5, 2), default=0.00, nullable=False)
    extra_discount_amount = Column(Numeric(10, 2), default=0.00, nullable=False)
    final_total_amount = Column(Numeric(10, 2), nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    items = relationship("OrderItem", back_populates="order", cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_orders_status_created", "order_status", "created_at"),
        Index("ix_orders_phone_number", "customer_phone", "order_number"),
    )

    def __repr__(self):
        return f"<Order id={self.id} number='{self.order_number}' status='{self.order_status}' total={self.total_amount}>"


class OrderItem(Base):
    __tablename__ = "order_items"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    order_id = Column(Integer, ForeignKey("orders.id", ondelete="CASCADE"), nullable=False, index=True)
    product_id = Column(Integer, ForeignKey("products.id", ondelete="SET NULL"), nullable=True, index=True)
    product_name_snapshot = Column(String(255), nullable=False)
    quantity = Column(Integer, nullable=False)
    unit_price = Column(Numeric(10, 2), nullable=False)
    total_price = Column(Numeric(10, 2), nullable=False)

    # Relationships
    order = relationship("Order", back_populates="items")
    product = relationship("Product", back_populates="order_items")

    def __repr__(self):
        return f"<OrderItem id={self.id} order_id={self.order_id} product='{self.product_name_snapshot}' qty={self.quantity}>"
