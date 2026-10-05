from sqlalchemy import Column, Integer, String, Text, DateTime, Index
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.core.database import Base


class Customer(Base):
    __tablename__ = "customers"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    customer_code = Column(String(64), unique=True, nullable=False, index=True)
    guest_id = Column(String(100), nullable=True, index=True)
    name = Column(String(150), nullable=False)
    phone = Column(String(20), nullable=False, index=True)
    email = Column(String(120), nullable=True)
    address = Column(Text, nullable=True)
    city = Column(String(100), nullable=True)
    state = Column(String(100), nullable=True)
    pincode = Column(String(10), nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    last_order_at = Column(DateTime(timezone=True), nullable=True, index=True)

    # Relationships
    orders = relationship("Order", back_populates="customer", order_by="desc(Order.created_at)")

    def __repr__(self):
        return f"<Customer id={self.id} code='{self.customer_code}' name='{self.name}' phone='{self.phone}'>"
