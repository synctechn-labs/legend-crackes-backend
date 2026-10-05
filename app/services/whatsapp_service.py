import urllib.request
import urllib.parse
import threading
from typing import Dict, Any
from app.core.config import settings
from app.core.logging import audit_logger


def send_whatsapp_order_alert(order_data: Dict[str, Any]):
    """
    Asynchronously dispatches instant mobile WhatsApp notification to Admin via CallMeBot API.
    100% Free, direct WhatsApp message delivery to Admin phone.
    """
    def _send():
        phone = (getattr(settings, "WHATSAPP_ADMIN_PHONE", None) or "").strip()
        api_key = (getattr(settings, "CALLMEBOT_API_KEY", None) or "").strip()

        if not phone or not api_key:
            audit_logger.info("WhatsApp notification skipped: WHATSAPP_ADMIN_PHONE or CALLMEBOT_API_KEY not configured.")
            return

        # Ensure phone format (must include country code without + sign, e.g. 919876543210)
        clean_phone = "".join([c for c in phone if c.isdigit()])

        try:
            order_id = order_data.get("id") or order_data.get("order_number") or "N/A"
            order_no = order_data.get("order_number") or f"#{order_id}"
            cust_name = order_data.get("customer_name") or "Customer"
            cust_phone = order_data.get("customer_phone") or "N/A"
            city = order_data.get("city") or "N/A"
            pincode = order_data.get("pincode") or ""
            total = float(order_data.get("total_amount") or 0.0)
            payment = order_data.get("payment_method") or "Cash on Delivery"
            items = order_data.get("items") or []

            items_summary = ""
            for item in items[:5]:
                pname = item.get("product_name_snapshot") or item.get("product_name") or item.get("name") or "Item"
                qty = item.get("quantity") or 1
                items_summary += f"- {pname} (x{qty})\n"

            if len(items) > 5:
                items_summary += f"- ...and {len(items) - 5} more item(s)\n"

            message = (
                f"🚨 *NEW ORDER RECEIVED!* 🎆\n\n"
                f"📦 Order ID: {order_no}\n"
                f"👤 Customer: {cust_name}\n"
                f"📞 Mobile: {cust_phone}\n"
                f"📍 City: {city} ({pincode})\n"
                f"💰 Total Amount: Rs.{total:,.2f} ({payment})\n\n"
                f"🛒 Items:\n{items_summary}\n"
                f"⚡ Status: Pending Processing"
            )

            encoded_msg = urllib.parse.quote(message)
            url = f"https://api.callmebot.com/whatsapp.php?phone={clean_phone}&text={encoded_msg}&apikey={api_key}"

            req = urllib.request.Request(
                url,
                headers={"User-Agent": "Mozilla/5.0"},
                method="GET"
            )
            with urllib.request.urlopen(req, timeout=10) as response:
                audit_logger.info(f"CallMeBot WhatsApp notification dispatched for Order {order_no}, HTTP {response.status}")
        except Exception as e:
            audit_logger.error(f"WhatsApp notification error: {e}")

    thread = threading.Thread(target=_send, daemon=True)
    thread.start()


whatsapp_service = send_whatsapp_order_alert
