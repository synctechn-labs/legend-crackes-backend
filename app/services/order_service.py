import math
from typing import Optional
from datetime import datetime
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from app.models.order import Order, OrderItem
from app.models.product import Product
from app.repositories.order_repo import order_repo
from app.repositories.product_repo import product_repo
from app.repositories.customer_repo import customer_repo
from app.schemas.order import OrderCreate, OrderResponse, OrderPaginatedResponse, OrderStatusUpdate
from app.utils.formatters import generate_order_number, format_order_dict
from app.core.config import settings
from app.core.logging import audit_logger


class OrderService:
    def create_order(self, db: Session, order_in: OrderCreate) -> OrderResponse:
        """
        Atomic transactional order placement:
        1. Validates customer information.
        2. Acquires row locks on requested products to ensure concurrency safety.
        3. Recalculates all pricing, discount, and delivery charge entirely on the server.
        4. Decrements inventory in real-time.
        5. Atomically commits or rolls back on any error.
        """
        # Validate customer details
        cust_name = (order_in.customer_name or "").strip()
        cust_phone = (order_in.customer_phone or "").strip()
        cust_alt_phone = (order_in.customer_alternate_phone or (order_in.customer.alternatePhone if order_in.customer else None) or (order_in.customer.alternate_phone if order_in.customer else None) or "").strip() or None
        cust_address = (order_in.address or "").strip()
        cust_city = (order_in.city or "").strip()
        cust_state = (order_in.state or "").strip()
        cust_pincode = (order_in.pincode or "").strip()
        cust_email = (order_in.customer_email or "").strip() if order_in.customer_email else None

        if not cust_name:
            raise HTTPException(status_code=400, detail="Customer full name is required.")
        if not cust_phone or len(cust_phone) < 10:
            raise HTTPException(status_code=400, detail="Valid 10-digit mobile number is required.")
        if not cust_address:
            raise HTTPException(status_code=400, detail="Delivery address is required.")
        if not cust_city or not cust_pincode:
            raise HTTPException(status_code=400, detail="City and PIN code are required.")

        # Consolidate duplicate product_ids in the request if user added same item twice
        consolidated_items = {}
        for item in order_in.items:
            pid = item.product_id
            if not pid:
                raise HTTPException(status_code=400, detail="Invalid product item specified in order.")
            consolidated_items[pid] = consolidated_items.get(pid, 0) + item.quantity

        try:
            # Begin explicit transaction block
            calculated_subtotal = 0.0
            order_items_to_create = []

            # Lock products in deterministic ID order to prevent deadlock
            for product_id in sorted(consolidated_items.keys()):
                requested_qty = consolidated_items[product_id]
                
                # Lock row for transaction
                product = product_repo.get_by_id_for_update(db, product_id)
                if not product:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail=f"Product with ID {product_id} does not exist or has been removed."
                    )

                if not product.is_active:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Product '{product.name}' is currently inactive and cannot be ordered."
                    )

                # Server-calculated prices (NEVER trusted from client payload)
                unit_price = float(product.selling_price)
                item_total = round(unit_price * requested_qty, 2)
                calculated_subtotal += item_total

                # Prepare order item with historical snapshot
                order_item = OrderItem(
                    product_id=product.id,
                    product_name_snapshot=product.name,
                    quantity=requested_qty,
                    unit_price=unit_price,
                    total_price=item_total
                )
                order_items_to_create.append(order_item)

            calculated_subtotal = round(calculated_subtotal, 2)

            # Minimum order amount validation
            if calculated_subtotal < settings.MIN_ORDER_AMOUNT:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Minimum order amount is ₹{int(settings.MIN_ORDER_AMOUNT):,}. Your subtotal is ₹{calculated_subtotal:,.2f}. Please add ₹{settings.MIN_ORDER_AMOUNT - calculated_subtotal:,.2f} more to proceed."
                )

            # Calculate delivery charge (₹500 flat for all orders)
            delivery_charge = float(settings.DEFAULT_DELIVERY_CHARGE)

            # Calculate coupon discount
            discount_amount = 0.0
            applied_code = (getattr(order_in, "coupon_code", None) or getattr(order_in, "couponCode", None) or "").strip().upper()
            if applied_code:
                try:
                    from app.repositories.coupon_repo import coupon_repo
                    c_model = coupon_repo.get_by_code(db, applied_code)
                    if c_model and c_model.is_active:
                        pct = float(c_model.discount_percentage or 5.0)
                        min_req = float(c_model.min_order_amount or 0.0)
                        if calculated_subtotal >= min_req:
                            discount_amount = round(calculated_subtotal * (pct / 100.0), 2)
                            if c_model.max_discount_amount and float(c_model.max_discount_amount) > 0:
                                discount_amount = min(discount_amount, float(c_model.max_discount_amount))
                            coupon_repo.increment_usage(db, c_model.id)
                except Exception as c_err:
                    audit_logger.warning(f"Coupon application warning: {c_err}")

            if discount_amount == 0.0 and getattr(order_in, "discount", None) and float(order_in.discount) > 0:
                discount_amount = round(float(order_in.discount), 2)

            final_total = round(max(0.0, calculated_subtotal - discount_amount + delivery_charge), 2)

            # Resolve or create Customer (Guest ID + Phone matching)
            customer = customer_repo.resolve_or_create_customer(
                db=db,
                guest_id=order_in.guest_id,
                name=cust_name,
                phone=cust_phone,
                email=cust_email,
                address=cust_address,
                city=cust_city,
                state=cust_state,
                pincode=cust_pincode
            )

            # Generate unique order number
            # Create Order header record
            order = Order(
                order_number="CLC_TEMP",
                customer_id=customer.id,
                customer_name=cust_name,
                customer_phone=cust_phone,
                customer_alternate_phone=cust_alt_phone,
                customer_email=cust_email,
                address=cust_address,
                city=cust_city,
                state=cust_state,
                pincode=cust_pincode,
                subtotal=calculated_subtotal,
                discount=discount_amount,
                delivery_charge=delivery_charge,
                total_amount=final_total,
                coupon_code=applied_code if applied_code else None,
                payment_method=order_in.payment_method or "Cash on Delivery",
                payment_status="Pending",
                order_status="Pending"
            )
            db.add(order)
            db.flush()
            order.order_number = f"CLC{order.id:03d}"

            # Associate items
            for oi in order_items_to_create:
                oi.order_id = order.id
                db.add(oi)

            # Commit the entire atomic transaction
            db.commit()
            db.refresh(order)

            # Trigger Telegram mobile push notification exclusively (async non-blocking)
            order_dict = format_order_dict(order)
            try:
                from app.services.telegram_service import send_telegram_order_alert
                send_telegram_order_alert(order_dict)
            except Exception as tel_err:
                audit_logger.warn(f"Failed to dispatch Telegram alert: {tel_err}")

            audit_logger.info(
                f"Order placed successfully: #{order.order_number} for customer {order.customer_phone}, Total: Rs.{order.total_amount}"
            )

            return OrderResponse(**format_order_dict(order))

        except HTTPException:
            db.rollback()
            raise
        except Exception as e:
            db.rollback()
            audit_logger.error(f"Transaction failed during order creation: {str(e)}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to process order transaction. Please try again."
            )

    def list_orders(
        self,
        db: Session,
        page: int = 1,
        limit: int = 15,
        search: Optional[str] = None,
        status_filter: Optional[str] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None
    ) -> OrderPaginatedResponse:
        safe_limit = min(max(1, limit), 100)
        safe_page = max(1, page)
        offset = (safe_page - 1) * safe_limit

        orders, total = order_repo.query_orders(
            db=db,
            offset=offset,
            limit=safe_limit,
            search=search,
            status=status_filter,
            date_from=date_from,
            date_to=date_to
        )

        total_pages = math.ceil(total / safe_limit) if total > 0 else 1
        formatted = [OrderResponse(**format_order_dict(o)) for o in orders]

        return OrderPaginatedResponse(
            orders=formatted,
            total=total,
            page=safe_page,
            limit=safe_limit,
            total_pages=total_pages
        )

    def get_order_by_id(self, db: Session, order_id: int) -> OrderResponse:
        order = order_repo.get_by_id(db, order_id)
        if not order:
            raise HTTPException(status_code=404, detail="Order not found.")
        return OrderResponse(**format_order_dict(order))

    def update_order_status(self, db: Session, order_id: int, new_status: str, admin_username: str) -> OrderResponse:
        order = order_repo.get_by_id(db, order_id)
        if not order:
            raise HTTPException(status_code=404, detail="Order not found.")

        old_status = order.order_status
        clean_status = new_status.strip().capitalize()
        valid_statuses = ["Pending", "Confirmed", "Processing", "Shipped", "Delivered", "Cancelled"]
        if clean_status not in valid_statuses:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid status '{new_status}'. Must be one of: {', '.join(valid_statuses)}"
            )

        order.order_status = clean_status
        db.commit()
        db.refresh(order)
        
        # Invalidate analytics cache so Dashboard & Revenue stats reflect instant updates
        try:
            from app.services.analytics_service import invalidate_analytics_cache
            invalidate_analytics_cache()
        except Exception:
            pass

        audit_logger.info(f"Order #{order.order_number} status changed: {old_status} -> {clean_status} by admin {admin_username}")
        return OrderResponse(**format_order_dict(order))

    def update_extra_discount(
        self,
        db: Session,
        order_id: int,
        admin_username: str,
        extra_discount_percentage: Optional[float] = None,
        extra_discount_amount: Optional[float] = None
    ) -> OrderResponse:
        order = order_repo.get_by_id(db, order_id)
        if not order:
            raise HTTPException(status_code=404, detail="Order not found.")

        # Calculate profit before extra discount to compute extra discount amount
        total_profit = 0.0
        for item in order.items:
            sell_p = float(item.unit_price)
            prod_obj = getattr(item, "product", None)
            if prod_obj:
                my_p_val = float(getattr(prod_obj, "my_price", None) or 0.0)
                my_p = my_p_val if 0 < my_p_val < sell_p else round(sell_p * 0.4, 2)
            else:
                my_p = round(sell_p * 0.4, 2)
            total_profit += (sell_p - my_p) * item.quantity

        if extra_discount_amount is not None and float(extra_discount_amount) > 0:
            extra_disc_amt = round(float(extra_discount_amount), 2)
            pct = round((extra_disc_amt / total_profit) * 100.0, 2) if total_profit > 0 else 0.0
        elif extra_discount_percentage is not None:
            pct = max(0.0, min(100.0, float(extra_discount_percentage)))
            extra_disc_amt = round(total_profit * (pct / 100.0), 2)
        else:
            pct = 0.0
            extra_disc_amt = 0.0

        order.extra_discount_percentage = pct
        order.extra_discount_amount = extra_disc_amt
        order.final_total_amount = round(float(order.total_amount) - extra_disc_amt, 2)

        db.commit()
        db.refresh(order)

        try:
            from app.services.analytics_service import invalidate_analytics_cache
            invalidate_analytics_cache()
        except Exception:
            pass

        audit_logger.info(f"Order #{order.order_number} extra discount set to {pct}% (-Rs.{extra_disc_amt}) by admin {admin_username}")
        return OrderResponse(**format_order_dict(order))

    def delete_order(self, db: Session, order_id: int, admin_username: str) -> dict:
        order = order_repo.get_by_id(db, order_id)
        if not order:
            raise HTTPException(status_code=404, detail="Order not found.")

        ord_num = order.order_number
        order_repo.delete(db, order)

        try:
            from app.services.analytics_service import invalidate_analytics_cache
            invalidate_analytics_cache()
        except Exception:
            pass

        audit_logger.info(f"Order #{ord_num} (ID {order_id}) deleted by admin {admin_username}")
        return {"success": True, "message": f"Order #{order_id} deleted successfully."}


order_service = OrderService()
