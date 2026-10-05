import time
from typing import Dict, Any, List
from sqlalchemy.orm import Session
from app.repositories.analytics_repo import analytics_repo
from app.schemas.dashboard import DashboardStatsResponse
from app.schemas.revenue import RevenueAnalyticsResponse
from app.utils.formatters import format_product_dict, format_order_dict
from app.schemas.product import ProductResponse
from app.schemas.order import OrderResponse


# High-performance 15-second in-memory TTL cache for serverless latency reduction
_CACHE_TTL_SECONDS = 15
_dashboard_cache: Dict[str, Any] = {"timestamp": 0, "data": None}
_revenue_cache: Dict[str, Any] = {}


def invalidate_analytics_cache():
    global _dashboard_cache, _revenue_cache
    _dashboard_cache = {"timestamp": 0, "data": None}
    _revenue_cache.clear()


class AnalyticsService:
    def get_dashboard(self, db: Session) -> DashboardStatsResponse:
        now = time.time()
        if _dashboard_cache["data"] and (now - _dashboard_cache["timestamp"]) < _CACHE_TTL_SECONDS:
            return _dashboard_cache["data"]

        metrics = analytics_repo.get_dashboard_metrics(db)
        
        # Format recent orders and low stock products
        low_stock_formatted = [ProductResponse(**format_product_dict(p)) for p in metrics["low_stock_products"]]
        recent_orders_formatted = [OrderResponse(**format_order_dict(o)) for o in metrics["recent_orders"]]
        category_sales = analytics_repo.get_category_sales(db)

        daily_trend = analytics_repo.get_revenue_trend(db, time_range="daily")
        revenue_over_time = [
            {
                "day": d.get("period") or d.get("month") or "Day",
                "period": d.get("period") or d.get("month") or "Day",
                "revenue": float(d.get("revenue", 0.0)),
                "orders": int(d.get("orders", 0))
            }
            for d in daily_trend
        ]

        if not revenue_over_time:
            days = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
            revenue_over_time = [{"day": d, "period": d, "revenue": 0.0, "orders": 0} for d in days]

        total_rev = metrics["total_revenue"]
        today_rev = metrics["today_revenue"]
        total_profit = metrics.get("total_profit", 0.0)
        total_cost = metrics.get("total_cost", 0.0)

        response = DashboardStatsResponse(
            total_products=metrics["total_products"],
            active_products=metrics["active_products"],
            total_orders=metrics["total_orders"],
            pending_orders=metrics["pending_orders"],
            completed_orders=metrics["completed_orders"],
            total_revenue=total_rev,
            today_revenue=today_rev,
            total_profit=total_profit,
            total_cost=total_cost,
            low_stock_count=metrics["low_stock_count"],
            low_stock_products=low_stock_formatted,
            recent_orders=recent_orders_formatted,
            revenue_over_time=revenue_over_time,
            category_wise_sales=category_sales,
            # React camelCase fields
            totalProducts=metrics["total_products"],
            totalOrders=metrics["total_orders"],
            pendingOrders=metrics["pending_orders"],
            completedOrders=metrics["completed_orders"],
            totalRevenue=total_rev,
            todayRevenue=today_rev,
            totalProfit=total_profit,
            totalCost=total_cost,
            lowStockCount=metrics["low_stock_count"],
            lowStockProducts=low_stock_formatted,
            recentOrders=recent_orders_formatted,
            revenueOverTime=revenue_over_time,
            categoryWiseSales=category_sales,
        )

        _dashboard_cache["timestamp"] = now
        _dashboard_cache["data"] = response
        return response

    def get_revenue_analytics(self, db: Session, time_range: str = "monthly") -> RevenueAnalyticsResponse:
        now = time.time()
        cache_entry = _revenue_cache.get(time_range)
        if cache_entry and (now - cache_entry["timestamp"]) < _CACHE_TTL_SECONDS:
            return cache_entry["data"]

        metrics = analytics_repo.get_dashboard_metrics(db)
        total_rev = metrics["total_revenue"]
        order_cnt = metrics["total_orders"]
        aov = round(total_rev / order_cnt, 2) if order_cnt > 0 else 0.0
        total_profit = metrics.get("total_profit", 0.0)
        total_cost = metrics.get("total_cost", 0.0)

        monthly_trend = analytics_repo.get_revenue_trend(db, time_range=time_range)
        cat_sales = analytics_repo.get_category_sales(db)
        top_prods = analytics_repo.get_top_products(db)

        weekly_rev = metrics.get("weekly_revenue", 0.0)

        response = RevenueAnalyticsResponse(
            revenue=total_rev,
            order_count=order_cnt,
            average_order_value=aov,
            time_range=time_range,
            total_profit=total_profit,
            total_cost=total_cost,
            daily_revenue=metrics["today_revenue"],
            weekly_revenue=weekly_rev,
            monthly_revenue=total_rev,
            revenue_growth="Live Real-time Metrics",
            monthly_trend=monthly_trend,
            sales_by_category=cat_sales,
            top_selling_products=top_prods,
            # Frontend compatibility
            totalRevenue=total_rev,
            totalProfit=total_profit,
            totalCost=total_cost,
            orderCount=order_cnt,
            averageOrderValue=aov,
            dailyRevenue=metrics["today_revenue"],
            weeklyRevenue=weekly_rev,
            monthlyRevenue=total_rev,
            revenueGrowth="Live Real-time Metrics",
            monthlyTrend=monthly_trend,
            salesByCategory=cat_sales,
            topSellingProducts=top_prods,
        )

        _revenue_cache[time_range] = {"timestamp": now, "data": response}
        return response

    def get_category_sales(self, db: Session) -> List[Dict[str, Any]]:
        return analytics_repo.get_category_sales(db)

    def get_top_products(self, db: Session, limit: int = 10) -> List[Dict[str, Any]]:
        return analytics_repo.get_top_products(db, limit=limit)


analytics_service = AnalyticsService()
