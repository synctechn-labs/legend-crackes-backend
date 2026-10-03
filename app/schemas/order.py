from datetime import datetime
from typing import Optional, List, Any, Dict
from pydantic import BaseModel, ConfigDict, Field, model_validator


class OrderItemInput(BaseModel):
    product_id: Optional[int] = None
    quantity: int = Field(gt=0, description="Quantity must be greater than 0")
    # For frontend compatibility if object is passed
    product: Optional[Dict[str, Any]] = None
    id: Optional[int] = None

    @model_validator(mode="before")
    @classmethod
    def resolve_product_id(cls, data: Any) -> Any:
        if isinstance(data, dict):
            if "product_id" not in data or data.get("product_id") is None:
                if "product" in data and isinstance(data["product"], dict) and "id" in data["product"]:
                    data["product_id"] = data["product"]["id"]
                elif "id" in data:
                    data["product_id"] = data["id"]
        return data


class CustomerDetails(BaseModel):
    name: str
    phone: str
    email: Optional[str] = None
    address: str
    city: str
    state: str
    pincode: str


class OrderCreate(BaseModel):
    # Support both flat and nested customer object
    customer_name: Optional[str] = None
    customer_phone: Optional[str] = None
    customer_email: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    pincode: Optional[str] = None
    
    customer: Optional[CustomerDetails] = None
    
    items: List[OrderItemInput] = Field(min_length=1, description="Order must contain at least 1 item")
    payment_method: str = "Cash on Delivery"

    @model_validator(mode="before")
    @classmethod
    def normalize_customer_fields(cls, data: Any) -> Any:
        if isinstance(data, dict):
            cust = data.get("customer")
            if isinstance(cust, dict):
                data.setdefault("customer_name", cust.get("name") or cust.get("customer_name"))
                data.setdefault("customer_phone", cust.get("phone") or cust.get("customer_phone"))
                data.setdefault("customer_email", cust.get("email") or cust.get("customer_email"))
                data.setdefault("address", cust.get("address"))
                data.setdefault("city", cust.get("city"))
                data.setdefault("state", cust.get("state"))
                data.setdefault("pincode", cust.get("pincode"))
        return data


class OrderItemResponse(BaseModel):
    id: int
    product_id: Optional[int]
    product_name_snapshot: str
    quantity: int
    unit_price: float
    total_price: float

    # Aliases
    name: Optional[str] = None
    productName: Optional[str] = None
    code: Optional[str] = None
    price: Optional[float] = None
    total: Optional[float] = None

    model_config = ConfigDict(from_attributes=True)


class OrderResponse(BaseModel):
    id: Any
    order_number: str
    customer_name: str
    customer_phone: str
    customer_email: Optional[str] = None
    address: str
    city: str
    state: str
    pincode: str
    subtotal: float
    discount: float
    delivery_charge: float
    total_amount: float
    extra_discount_percentage: float = 0.0
    extra_discount_amount: float = 0.0
    final_total_amount: Optional[float] = None
    profit: Optional[float] = 0.0
    payment_method: str
    payment_status: str
    order_status: str
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    items: List[OrderItemResponse] = []

    # Frontend convenience aliases
    orderNumber: Optional[str] = None
    status: Optional[str] = None
    total: Optional[float] = None
    extraDiscountPercentage: Optional[float] = 0.0
    extraDiscountAmount: Optional[float] = 0.0
    finalTotal: Optional[float] = None
    createdAt: Optional[str] = None
    customer: Optional[Dict[str, Any]] = None

    model_config = ConfigDict(from_attributes=True)


class OrderStatusUpdate(BaseModel):
    status: str = Field(description="New status: pending, confirmed, processing, shipped, delivered, cancelled")


class OrderExtraDiscountUpdate(BaseModel):
    extra_discount_percentage: float = Field(default=0.0, ge=0, le=100, description="Extra discount percentage (0-100%) deducted from profit")


class OrderPaginatedResponse(BaseModel):
    orders: List[OrderResponse]
    total: int
    page: int
    limit: int
    total_pages: int
