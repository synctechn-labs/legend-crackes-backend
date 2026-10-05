from datetime import datetime
from typing import Optional, List, Any, Dict
from pydantic import BaseModel, ConfigDict


class CustomerBase(BaseModel):
    name: str
    phone: str
    email: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    pincode: Optional[str] = None


class CustomerResponse(BaseModel):
    id: int
    customer_code: str
    guest_id: Optional[str] = None
    name: str
    phone: str
    email: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    pincode: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    last_order_at: Optional[datetime] = None
    
    # Aggregated metrics for display
    total_orders: int = 0
    total_spent: float = 0.0

    model_config = ConfigDict(from_attributes=True)


class CustomerSummaryMetrics(BaseModel):
    total_orders: int = 0
    total_spent: float = 0.0
    average_order_value: float = 0.0
    first_order_date: Optional[datetime] = None
    last_order_date: Optional[datetime] = None


class CustomerDetailResponse(BaseModel):
    customer: CustomerResponse
    summary: CustomerSummaryMetrics
    orders: List[Dict[str, Any]] = []

    model_config = ConfigDict(from_attributes=True)


class CustomerPaginatedResponse(BaseModel):
    customers: List[CustomerResponse]
    total: int
    page: int
    limit: int
    total_pages: int


class CustomerMetricsResponse(BaseModel):
    total_customers: int = 0
    new_customers: int = 0
    returning_customers: int = 0
    repeat_customer_rate: float = 0.0
    avg_orders_per_customer: float = 0.0
    avg_customer_spend: float = 0.0
