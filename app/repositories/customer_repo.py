import math
from typing import Optional, List, Tuple, Dict, Any
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import func, or_, desc, asc
from app.models.customer import Customer
from app.models.order import Order


class CustomerRepository:
    def get_by_id(self, db: Session, customer_id: int) -> Optional[Customer]:
        return db.query(Customer).filter(Customer.id == customer_id).first()

    def get_by_guest_id(self, db: Session, guest_id: str) -> Optional[Customer]:
        if not guest_id:
            return None
        return db.query(Customer).filter(Customer.guest_id == guest_id.strip()).first()

    def get_by_phone(self, db: Session, phone: str) -> Optional[Customer]:
        if not phone:
            return None
        clean_phone = "".join(filter(str.isdigit, phone))
        if not clean_phone:
            return None
        # Match exact clean phone or exact phone string
        return db.query(Customer).filter(
            or_(
                Customer.phone == phone.strip(),
                Customer.phone == clean_phone
            )
        ).first()

    def get_by_code(self, db: Session, code: str) -> Optional[Customer]:
        if not code:
            return None
        return db.query(Customer).filter(Customer.customer_code == code.strip().upper()).first()

    def generate_customer_code(self, db: Session) -> str:
        max_id = db.query(func.max(Customer.id)).scalar() or 0
        next_id = max_id + 1
        return f"CUS-{next_id:06d}"

    def resolve_or_create_customer(
        self,
        db: Session,
        guest_id: Optional[str],
        name: str,
        phone: str,
        email: Optional[str] = None,
        address: Optional[str] = None,
        city: Optional[str] = None,
        state: Optional[str] = None,
        pincode: Optional[str] = None
    ) -> Customer:
        """
        Customer Identification Logic:
        1. Check guest_id match.
        2. Check phone match if guest_id fails.
        3. Create new customer if neither matches.
        """
        clean_guest_id = (guest_id or "").strip() or None
        clean_phone = (phone or "").strip()
        customer = None

        # Step 1: Check guest_id
        if clean_guest_id:
            customer = self.get_by_guest_id(db, clean_guest_id)

        # Step 2: Check phone number
        if not customer and clean_phone:
            customer = self.get_by_phone(db, clean_phone)
            # Update guest_id on existing customer if missing or updated
            if customer and clean_guest_id and not customer.guest_id:
                customer.guest_id = clean_guest_id

        now = datetime.now()

        # Step 3: Create customer if not found
        if not customer:
            code = self.generate_customer_code(db)
            customer = Customer(
                customer_code=code,
                guest_id=clean_guest_id,
                name=name.strip(),
                phone=clean_phone,
                email=(email or "").strip() or None,
                address=(address or "").strip() or None,
                city=(city or "").strip() or None,
                state=(state or "").strip() or None,
                pincode=(pincode or "").strip() or None,
                last_order_at=now
            )
            db.add(customer)
            db.flush()
        else:
            # Update existing customer details with latest checkout information
            if name: customer.name = name.strip()
            if clean_phone: customer.phone = clean_phone
            if email: customer.email = email.strip()
            if address: customer.address = address.strip()
            if city: customer.city = city.strip()
            if state: customer.state = state.strip()
            if pincode: customer.pincode = pincode.strip()
            customer.last_order_at = now
            db.flush()

        return customer

    def list_customers(
        self,
        db: Session,
        page: int = 1,
        limit: int = 20,
        search: Optional[str] = None,
        phone: Optional[str] = None,
        sort_by: str = "recent"
    ) -> Tuple[List[Dict[str, Any]], int]:
        query = db.query(Customer)

        if search:
            term = f"%{search.strip()}%"
            query = query.filter(
                or_(
                    Customer.customer_code.ilike(term),
                    Customer.name.ilike(term),
                    Customer.phone.ilike(term),
                    Customer.email.ilike(term),
                    Customer.city.ilike(term)
                )
            )

        if phone:
            query = query.filter(Customer.phone.contains(phone.strip()))

        if sort_by == "oldest":
            query = query.order_by(asc(Customer.created_at))
        elif sort_by == "name":
            query = query.order_by(asc(Customer.name))
        else:
            query = query.order_by(desc(Customer.created_at))

        total = query.count()
        offset = (page - 1) * limit
        customers = query.offset(offset).limit(limit).all()

        results = []
        for c in customers:
            # Aggregate order metrics for each customer
            order_stats = db.query(
                func.count(Order.id).label("total_orders"),
                func.coalesce(func.sum(Order.total_amount), 0.0).label("total_spent")
            ).filter(Order.customer_id == c.id).first()

            total_orders = order_stats.total_orders if order_stats else 0
            total_spent = float(order_stats.total_spent) if order_stats else 0.0

            results.append({
                "id": c.id,
                "customer_code": c.customer_code,
                "guest_id": c.guest_id,
                "name": c.name,
                "phone": c.phone,
                "email": c.email,
                "address": c.address,
                "city": c.city,
                "state": c.state,
                "pincode": c.pincode,
                "created_at": c.created_at,
                "updated_at": c.updated_at,
                "last_order_at": c.last_order_at,
                "total_orders": total_orders,
                "total_spent": total_spent
            })

        return results, total

    def get_customer_detail(self, db: Session, customer_id: int) -> Optional[Dict[str, Any]]:
        customer = self.get_by_id(db, customer_id)
        if not customer:
            return None

        # Calculate metrics
        orders = db.query(Order).filter(Order.customer_id == customer.id).order_by(desc(Order.created_at)).all()
        total_orders = len(orders)
        total_spent = sum(float(o.total_amount or 0.0) for o in orders)
        avg_order_value = round(total_spent / total_orders, 2) if total_orders > 0 else 0.0

        first_order_date = orders[-1].created_at if orders else None
        last_order_date = orders[0].created_at if orders else None

        formatted_orders = [
            {
                "id": o.id,
                "order_number": o.order_number,
                "total_amount": float(o.total_amount),
                "order_status": o.order_status,
                "payment_status": o.payment_status,
                "payment_method": o.payment_method,
                "created_at": o.created_at,
                "item_count": len(o.items)
            }
            for o in orders
        ]

        return {
            "customer": {
                "id": customer.id,
                "customer_code": customer.customer_code,
                "guest_id": customer.guest_id,
                "name": customer.name,
                "phone": customer.phone,
                "email": customer.email,
                "address": customer.address,
                "city": customer.city,
                "state": customer.state,
                "pincode": customer.pincode,
                "created_at": customer.created_at,
                "updated_at": customer.updated_at,
                "last_order_at": customer.last_order_at,
                "total_orders": total_orders,
                "total_spent": total_spent
            },
            "summary": {
                "total_orders": total_orders,
                "total_spent": total_spent,
                "average_order_value": avg_order_value,
                "first_order_date": first_order_date,
                "last_order_date": last_order_date
            },
            "orders": formatted_orders
        }

    def get_customer_metrics(self, db: Session) -> Dict[str, Any]:
        total_customers = db.query(Customer).count()
        if total_customers == 0:
            return {
                "total_customers": 0,
                "new_customers": 0,
                "returning_customers": 0,
                "repeat_customer_rate": 0.0,
                "avg_orders_per_customer": 0.0,
                "avg_customer_spend": 0.0
            }

        # Subquery for order count per customer
        subq = db.query(
            Order.customer_id,
            func.count(Order.id).label("order_count"),
            func.sum(Order.total_amount).label("customer_spent")
        ).group_by(Order.customer_id).subquery()

        returning_count = db.query(func.count(subq.c.customer_id)).filter(subq.c.order_count > 1).scalar() or 0
        total_orders_all = db.query(func.count(Order.id)).scalar() or 0
        total_revenue_all = float(db.query(func.coalesce(func.sum(Order.total_amount), 0.0)).scalar() or 0.0)

        repeat_rate = round((returning_count / total_customers) * 100, 1)
        avg_orders = round(total_orders_all / total_customers, 2)
        avg_spend = round(total_revenue_all / total_customers, 2)

        return {
            "total_customers": total_customers,
            "new_customers": total_customers - returning_count,
            "returning_customers": returning_count,
            "repeat_customer_rate": repeat_rate,
            "avg_orders_per_customer": avg_orders,
            "avg_customer_spend": avg_spend
        }


customer_repo = CustomerRepository()
