from typing import List, Dict, Any, Optional
from pydantic import BaseModel, ConfigDict
from app.schemas.order import OrderResponse
from app.schemas.product import ProductResponse


class DashboardStatsResponse(BaseModel):
    total_products: int
    active_products: int
    total_orders: int
    pending_orders: int
    completed_orders: int
    total_revenue: float
    today_revenue: float
    total_profit: Optional[float] = 0.0
    total_cost: Optional[float] = 0.0
    low_stock_count: int = 0
    total_customers: Optional[int] = 0
    new_customers: Optional[int] = 0
    returning_customers: Optional[int] = 0
    repeat_customer_rate: Optional[float] = 0.0
    low_stock_products: List[ProductResponse] = []
    recent_orders: List[OrderResponse] = []
    revenue_over_time: List[Dict[str, Any]] = []
    category_wise_sales: List[Dict[str, Any]] = []

    # Frontend camelCase aliases
    totalProducts: Optional[int] = None
    totalOrders: Optional[int] = None
    pendingOrders: Optional[int] = None
    completedOrders: Optional[int] = None
    totalRevenue: Optional[float] = None
    todayRevenue: Optional[float] = None
    totalProfit: Optional[float] = None
    totalCost: Optional[float] = None
    lowStockCount: Optional[int] = 0
    totalCustomers: Optional[int] = 0
    newCustomers: Optional[int] = 0
    returningCustomers: Optional[int] = 0
    repeatCustomerRate: Optional[float] = 0.0
    lowStockProducts: Optional[List[ProductResponse]] = None
    recentOrders: Optional[List[OrderResponse]] = None
    revenueOverTime: Optional[List[Dict[str, Any]]] = None
    categoryWiseSales: Optional[List[Dict[str, Any]]] = None

    model_config = ConfigDict(from_attributes=True)
