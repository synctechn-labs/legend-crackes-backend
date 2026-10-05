import os
import json
import urllib.request
import urllib.parse
from typing import Dict, Any
from app.core.config import settings
from app.core.logging import audit_logger


def send_telegram_order_alert(order_data: Dict[str, Any]):
    """
    Dispatches instant mobile notification to Telegram Bot when a new order is placed.
    Fully compatible with Vercel Serverless / AWS Lambda (synchronous HTTP execution to prevent Vercel container freeze).
    """
    bot_token = (os.environ.get("TELEGRAM_BOT_TOKEN") or getattr(settings, "TELEGRAM_BOT_TOKEN", "") or "").strip()
    chat_id = (os.environ.get("TELEGRAM_CHAT_ID") or getattr(settings, "TELEGRAM_CHAT_ID", "") or "").strip()

    if not bot_token or not chat_id or bot_token == "YOUR_TELEGRAM_BOT_TOKEN":
        audit_logger.info(f"Telegram notification skipped: bot_token={bool(bot_token)}, chat_id={bool(chat_id)}")
        return

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
        for item in items[:6]:
            pname = item.get("product_name_snapshot") or item.get("product_name") or item.get("name") or "Item"
            qty = item.get("quantity") or 1
            items_summary += f"  • {pname} × {qty}\n"

        if len(items) > 6:
            items_summary += f"  ...and {len(items) - 6} more item(s)\n"

        message = (
            f"🚨 *NEW ORDER RECEIVED!* 🎆\n\n"
            f"📦 *Order ID:* `{order_no}`\n"
            f"👤 *Customer:* {cust_name}\n"
            f"📞 *Mobile:* `{cust_phone}`\n"
            f"📍 *Location:* {city} ({pincode})\n"
            f"💰 *Total Amount:* ₹{total:,.2f} ({payment})\n\n"
            f"🛒 *Ordered Crackers:*\n{items_summary}\n"
            f"⚡ *Status:* Pending Processing"
        )

        url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        payload = {
            "chat_id": chat_id,
            "text": message,
            "parse_mode": "Markdown"
        }

        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=5) as response:
            audit_logger.info(f"Telegram mobile push notification dispatched for Order {order_no}, HTTP {response.status}")
    except Exception as e:
        audit_logger.error(f"Telegram notification error: {e}")


telegram_service = send_telegram_order_alert
