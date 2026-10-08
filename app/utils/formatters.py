import re
import random
from datetime import datetime


def slugify(text: str) -> str:
    """Convert text into url-safe slug."""
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_-]+", "-", text)
    return text.strip("-")


def generate_order_number(order_id: int = None) -> str:
    """Generate order number e.g. CLC001, CLC011."""
    if order_id is not None:
        return f"CLC{int(order_id):03d}"
    today = datetime.now().strftime("%Y%m%d")
    random_digits = random.randint(100, 999)
    return f"CLC{random_digits:03d}"



def format_product_dict(prod) -> dict:
    """Helper to convert product model to dictionary populated with both naming styles."""
    category_name = prod.category.name if prod.category else "General"
    cat_slug = prod.category.slug if prod.category else "general"
    
    orig_p = float(prod.original_price or 0.0)
    sell_p = float(prod.selling_price or 0.0)
    my_p = float(getattr(prod, "my_price", None) or 0.0)
    stock_qty = prod.stock_quantity if prod.stock_quantity is not None else 99999

    discount = prod.discount_percentage or 0
    if orig_p > sell_p and orig_p > 0:
        discount = round(((orig_p - sell_p) / orig_p) * 100)
    elif discount > 0 and sell_p > 0:
        if discount < 100 and orig_p <= sell_p:
            orig_p = round(sell_p / (1 - (discount / 100.0)), 2)
    elif sell_p > 0:
        discount = 60
        orig_p = round(sell_p * 2.5, 2)

    my_p = my_p if 0 < my_p < sell_p else round(sell_p * 0.4, 2)
    profit = round(sell_p - my_p, 2)
    unit_val = prod.unit or "Classic Legend Pack"

    return {
        "id": prod.id,
        "product_code": prod.product_code,
        "name": prod.name,
        "tamil_name": getattr(prod, "tamil_name", None),
        "slug": prod.slug,
        "category_id": prod.category_id,
        "category_name": category_name,
        "description": prod.description,
        "image_url": prod.image_url,
        "original_price": orig_p,
        "selling_price": sell_p,
        "my_price": my_p,
        "profit": profit,
        "discount_percentage": discount,
        "stock_quantity": stock_qty,
        "unit": unit_val,
        "is_featured": prod.is_featured,
        "is_active": prod.is_active,
        "created_at": prod.created_at,
        "updated_at": prod.updated_at,
        # React camelCase & alias fields
        "code": prod.product_code,
        "price": sell_p,
        "sellingPrice": sell_p,
        "originalPrice": orig_p,
        "myPrice": my_p,
        "discount": discount,
        "stock": stock_qty,
        "isFeatured": prod.is_featured,
        "isActive": prod.is_active,
        "category": cat_slug,
        "categoryName": category_name,
        "piecesPerBox": unit_val,
        "pieces_per_box": unit_val,
        "image": prod.image_url,
        "tamilName": getattr(prod, "tamil_name", None),
    }


def format_order_dict(order) -> dict:
    """Helper to convert order model to dictionary with nested items and camelCase aliases."""
    items = []
    order_profit_before_extra = 0.0

    for item in order.items:
        sell_p = float(item.unit_price)
        prod_obj = getattr(item, "product", None)
        if prod_obj:
            my_p_val = float(getattr(prod_obj, "my_price", None) or 0.0)
            my_p = my_p_val if my_p_val > 0 else round(sell_p * 0.4, 2)
            item_code = prod_obj.product_code
            item_img = prod_obj.image_url
        else:
            my_p = round(sell_p * 0.4, 2)
            item_code = f"SKF-{item.id}"
            item_img = None

        item_profit = (sell_p - my_p) * item.quantity
        order_profit_before_extra += item_profit

        items.append({
            "id": item.id,
            "product_id": item.product_id,
            "product_name_snapshot": item.product_name_snapshot,
            "quantity": item.quantity,
            "unit_price": sell_p,
            "total_price": float(item.total_price),
            "my_price": my_p,
            "myPrice": my_p,
            "productName": item.product_name_snapshot,
            "name": item.product_name_snapshot,
            "code": item.code if hasattr(item, "code") else item_code,
            "image": item_img,
            "price": sell_p,
            "total": float(item.total_price),
        })

    subtotal = float(order.subtotal)
    discount = float(order.discount)
    delivery = float(order.delivery_charge)
    total = float(order.total_amount)

    extra_disc_pct = float(getattr(order, "extra_discount_percentage", 0.0) or 0.0)
    extra_disc_amt = float(getattr(order, "extra_discount_amount", 0.0) or 0.0)

    if extra_disc_pct > 0 and extra_disc_amt == 0 and order_profit_before_extra > 0:
        extra_disc_amt = round(order_profit_before_extra * (extra_disc_pct / 100.0), 2)

    final_total = round(total - extra_disc_amt, 2)
    adjusted_profit = round(order_profit_before_extra - extra_disc_amt, 2)

    order_code = order.order_number
    if not order_code or not str(order_code).startswith("CLC"):
        if isinstance(order.id, int):
            order_code = f"CLC{order.id:03d}"
        else:
            order_code = str(order.id)

    alt_phone = getattr(order, "customer_alternate_phone", None)

    return {
        "id": order.id,
        "db_id": order.id,
        "order_number": order_code,
        "customer_name": order.customer_name or "Customer",
        "customer_phone": order.customer_phone or "N/A",
        "customer_alternate_phone": alt_phone,
        "customer_email": order.customer_email,
        "address": order.address or "",
        "city": order.city or "",
        "state": order.state or "",
        "pincode": order.pincode or "",
        "subtotal": subtotal,
        "discount": discount,
        "coupon_code": getattr(order, "coupon_code", None),
        "couponCode": getattr(order, "coupon_code", None),
        "delivery_charge": delivery,
        "deliveryCharge": delivery,
        "shippingFee": delivery,
        "shipping_fee": delivery,
        "total_amount": total,
        "extra_discount_percentage": extra_disc_pct,
        "extra_discount_amount": extra_disc_amt,
        "final_total_amount": final_total,
        "profit": adjusted_profit,
        "payment_method": order.payment_method or "Cash on Delivery",
        "payment_status": order.payment_status or "Pending",
        "order_status": order.order_status or "Pending",
        "created_at": order.created_at,
        "updated_at": order.updated_at,
        "items": items,
        # React frontend compatibility
        "orderNumber": order_code,
        "status": order.order_status or "Pending",
        "total": total,
        "deliveryCharge": delivery,
        "shippingFee": delivery,
        "extraDiscountPercentage": extra_disc_pct,
        "extraDiscountAmount": extra_disc_amt,
        "finalTotal": final_total,
        "createdAt": order.created_at.isoformat() if order.created_at else None,
        "customer": {
            "name": order.customer_name or "Customer",
            "phone": order.customer_phone or "N/A",
            "alternatePhone": alt_phone,
            "alternate_phone": alt_phone,
            "email": order.customer_email,
            "address": order.address or "",
            "city": order.city or "",
            "state": order.state or "",
            "pincode": order.pincode or "",
        }
    }
