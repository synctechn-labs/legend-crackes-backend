from typing import Dict, Any, List
from datetime import datetime, time, timedelta
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, desc, case, and_
from app.models.order import Order, OrderItem
from app.models.product import Product
from app.models.category import Category
from app.models.customer import Customer


class AnalyticsRepository:
    def get_dashboard_metrics(self, db: Session) -> Dict[str, Any]:
        today_start = datetime.combine(datetime.now().date(), time.min)
        week_start = datetime.now() - timedelta(days=7)

        # 1. Product Stats (1 pass)
        prod_res = db.query(
            func.count(Product.id).label("total"),
            func.sum(case((Product.is_active.is_(True), 1), else_=0)).label("active")
        ).first()
        total_products = prod_res[0] or 0 if prod_res else 0
        active_products = int(prod_res[1] or 0) if prod_res else 0

        # 2. Order & Revenue Stats (1 pass) - EXCLUDING CANCELLED ORDERS
        order_res = db.query(
            func.sum(case((func.lower(Order.order_status) != "cancelled", 1), else_=0)).label("total_orders"),
            func.sum(case((func.lower(Order.order_status) == "pending", 1), else_=0)).label("pending_orders"),
            func.sum(case((func.lower(Order.order_status) == "delivered", 1), else_=0)).label("completed_orders"),
            func.sum(case((func.lower(Order.order_status) != "cancelled", Order.total_amount), else_=0)).label("total_revenue"),
            func.sum(case((and_(func.lower(Order.order_status) != "cancelled", Order.created_at >= today_start), Order.total_amount), else_=0)).label("today_revenue"),
            func.sum(case((and_(func.lower(Order.order_status) != "cancelled", Order.created_at >= week_start), Order.total_amount), else_=0)).label("weekly_revenue")
        ).first()

        total_orders = int(order_res[0] or 0) if order_res else 0
        pending_orders = int(order_res[1] or 0) if order_res else 0
        completed_orders = int(order_res[2] or 0) if order_res else 0
        total_revenue = float(order_res[3] or 0.0) if order_res else 0.0
        today_revenue = float(order_res[4] or 0.0) if order_res else 0.0
        weekly_revenue = float(order_res[5] or 0.0) if order_res else 0.0

        # 3. Profit calculation (EXCLUDING CANCELLED ORDERS)
        profit_query = db.query(
            func.sum((OrderItem.unit_price - func.coalesce(Product.my_price, 0.0)) * OrderItem.quantity)
        ).join(Product, Product.id == OrderItem.product_id)\
         .join(Order, Order.id == OrderItem.order_id)\
         .filter(func.lower(Order.order_status) != "cancelled").scalar()

        extra_discount_query = db.query(
            func.sum(func.coalesce(Order.extra_discount_amount, 0.0))
        ).filter(func.lower(Order.order_status) != "cancelled").scalar() or 0.0

        raw_profit = float(profit_query) if profit_query is not None else 0.0
        total_profit = round(max(0.0, raw_profit - float(extra_discount_query)), 2)
        total_cost = round(max(0.0, total_revenue - total_profit), 2)

        # 4. Customer statistics
        total_customers = db.query(Customer).count()
        subq = db.query(
            Order.customer_id,
            func.count(Order.id).label("cnt")
        ).group_by(Order.customer_id).subquery()
        returning_customers = db.query(func.count(subq.c.customer_id)).filter(subq.c.cnt > 1).scalar() or 0
        new_customers = max(0, total_customers - returning_customers)
        repeat_customer_rate = round((returning_customers / total_customers) * 100, 1) if total_customers > 0 else 0.0

        # 5. Recent orders with preloaded items
        recent_orders = db.query(Order).options(
            joinedload(Order.items).joinedload(OrderItem.product)
        ).order_by(desc(Order.created_at)).limit(5).all()

        return {
            "total_products": total_products,
            "active_products": active_products,
            "total_orders": total_orders,
            "pending_orders": pending_orders,
            "completed_orders": completed_orders,
            "total_revenue": total_revenue,
            "today_revenue": today_revenue,
            "weekly_revenue": weekly_revenue,
            "total_profit": total_profit,
            "total_cost": total_cost,
            "low_stock_count": 0,
            "total_customers": total_customers,
            "new_customers": new_customers,
            "returning_customers": returning_customers,
            "repeat_customer_rate": repeat_customer_rate,
            "low_stock_products": [],
            "recent_orders": recent_orders
        }

    def get_category_sales(self, db: Session) -> List[Dict[str, Any]]:
        results = db.query(
            Category.name,
            func.sum(OrderItem.total_price).label("sales_sum"),
            func.count(OrderItem.id).label("item_count")
        ).join(Product, Product.id == OrderItem.product_id)\
         .join(Category, Category.id == Product.category_id)\
         .join(Order, Order.id == OrderItem.order_id)\
         .filter(func.lower(Order.order_status) != "cancelled")\
         .group_by(Category.name)\
         .order_by(desc("sales_sum")).all()

        palette = ["#DC2626", "#F59E0B", "#10B981", "#6366F1", "#EC4899", "#8B5CF6", "#14B8A6"]
        total_sales = sum([float(r[1] or 0) for r in results]) or 1.0

        data = []
        for idx, r in enumerate(results):
            amount = float(r[1] or 0)
            share = round((amount / total_sales) * 100, 1)
            data.append({
                "category": r[0],
                "name": r[0],
                "amount": amount,
                "sales": amount,
                "percentage": share,
                "share": share,
                "color": palette[idx % len(palette)]
            })

        return data

    def get_top_products(self, db: Session, limit: int = 10) -> List[Dict[str, Any]]:
        results = db.query(
            Product.id,
            Product.name,
            Product.product_code,
            Category.name.label("category_name"),
            func.sum(OrderItem.quantity).label("units_sold"),
            Product.selling_price,
            func.sum(OrderItem.total_price).label("product_revenue")
        ).join(OrderItem, OrderItem.product_id == Product.id)\
         .join(Order, Order.id == OrderItem.order_id)\
         .filter(func.lower(Order.order_status) != "cancelled")\
         .outerjoin(Category, Category.id == Product.category_id)\
         .group_by(Product.id, Product.name, Product.product_code, Category.name, Product.selling_price)\
         .order_by(desc("units_sold"))\
         .limit(limit).all()

        data = []
        for r in results:
            data.append({
                "id": r[0],
                "name": r[1],
                "code": r[2],
                "category": r[3] or "General",
                "units_sold": int(r[4] or 0),
                "unitsSold": int(r[4] or 0),
                "selling_price": float(r[5]),
                "sellingPrice": float(r[5]),
                "total_revenue": float(r[6] or 0),
                "totalRevenue": float(r[6] or 0)
            })

        return data

    def get_revenue_trend(self, db: Session, time_range: str = "monthly") -> List[Dict[str, Any]]:
        try:
            orders = db.query(Order).filter(
                func.lower(Order.order_status) != "cancelled"
            ).order_by(Order.created_at).all()

            if not orders:
                return []

            grouped: Dict[str, Dict[str, Any]] = {}
            for order in orders:
                created = order.created_at or datetime.now()
                if time_range == "daily":
                    key = created.strftime("%b %d, %Y")
                elif time_range == "weekly":
                    key = f"Week {created.strftime('%U, %Y')}"
                else:  # monthly
                    key = created.strftime("%b %Y")

                if key not in grouped:
                    grouped[key] = {"period": key, "revenue": 0.0, "orders": 0}

                grouped[key]["revenue"] += float(order.total_amount or 0.0)
                grouped[key]["orders"] += 1

            trend = []
            for key, val in grouped.items():
                rev = round(val["revenue"], 2)
                cnt = val["orders"]
                trend.append({
                    "period": key,
                    "month": key,
                    "date": key,
                    "day": key,
                    "revenue": rev,
                    "sales": rev,
                    "orders": cnt,
                    "orderCount": cnt
                })

            return trend
        except Exception as e:
            print(f"Error computing revenue trend: {e}")
            return []


analytics_repo = AnalyticsRepository()
