from typing import Optional, List, Tuple
from datetime import datetime
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import or_, desc
from app.models.order import Order, OrderItem
from app.repositories.base import BaseRepository


class OrderRepository(BaseRepository[Order]):
    def __init__(self):
        super().__init__(Order)

    def get_by_id(self, db: Session, order_id: int) -> Optional[Order]:
        return db.query(Order).options(
            joinedload(Order.items)
        ).filter(Order.id == order_id).first()

    def get_by_order_number(self, db: Session, order_number: str) -> Optional[Order]:
        return db.query(Order).options(
            joinedload(Order.items)
        ).filter(Order.order_number == order_number.strip()).first()

    def query_orders(
        self,
        db: Session,
        offset: int = 0,
        limit: int = 20,
        search: Optional[str] = None,
        status: Optional[str] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None
    ) -> Tuple[List[Order], int]:
        from sqlalchemy import func
        base_query = db.query(Order)

        # Status filter
        if status and status.strip() and status.strip().lower() != "all":
            base_query = base_query.filter(Order.order_status.ilike(status.strip()))

        # Search filter (order number, customer phone, customer name)
        if search and search.strip():
            term = f"%{search.strip()}%"
            base_query = base_query.filter(
                or_(
                    Order.order_number.ilike(term),
                    Order.customer_phone.ilike(term),
                    Order.customer_name.ilike(term)
                )
            )

        # Date filtering
        if date_from:
            base_query = base_query.filter(Order.created_at >= date_from)
        if date_to:
            base_query = base_query.filter(Order.created_at <= date_to)

        # Fast total count
        total = base_query.with_entities(func.count(Order.id)).scalar() or 0

        # Items query with preloaded items and products to eliminate N+1 latency
        items_query = base_query.options(
            joinedload(Order.items).joinedload(OrderItem.product)
        )
        orders = items_query.order_by(desc(Order.created_at)).offset(offset).limit(limit).all()
        return orders, total

    def delete(self, db: Session, order: Order) -> bool:
        db.query(OrderItem).filter(OrderItem.order_id == order.id).delete(synchronize_session=False)
        db.delete(order)
        db.commit()
        return True


order_repo = OrderRepository()
