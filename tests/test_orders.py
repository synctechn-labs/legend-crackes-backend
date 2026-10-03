def test_order_fails_below_minimum_amount(client):
    payload = {
        "customer_name": "Low Buyer",
        "customer_phone": "9842199887",
        "address": "45 Gandhi Bazaar",
        "city": "Madurai",
        "state": "Tamil Nadu",
        "pincode": "625001",
        "items": [
            {
                "product_id": 1,
                "quantity": 2  # Subtotal 120.0 is < 3000.0
            }
        ]
    }
    res = client.post("/api/orders", json=payload)
    assert res.status_code == 400
    assert "Minimum order amount is ₹3,000" in res.json()["message"]


def test_public_guest_checkout_recalculates_server_prices(client):
    # Customer payload trying to submit incorrect manipulated price 5.0
    payload = {
        "customer_name": "Ramesh Sundar",
        "customer_phone": "9842199887",
        "customer_email": "ramesh@example.com",
        "address": "45 Gandhi Bazaar",
        "city": "Madurai",
        "state": "Tamil Nadu",
        "pincode": "625001",
        "items": [
            {
                "product_id": 1,
                "quantity": 50,  # 50 * 60.0 = 3000.0
                "unit_price": 5.0,  # FAKE CLIENT PRICE - BACKEND MUST IGNORE!
                "total_price": 250.0
            }
        ],
        "payment_method": "Cash on Delivery"
    }

    prod_before = client.get("/api/products/1").json()
    stock_before = prod_before["stock_quantity"]

    response = client.post("/api/orders", json=payload)
    assert response.status_code == 201
    order = response.json()

    # Backend product 1 selling price is 60.0. Qty = 50 -> subtotal = 3000.0
    assert order["subtotal"] == 3000.0
    # Delivery charge is 500 for all orders
    assert order["delivery_charge"] == 500.0
    assert order["total_amount"] == 3500.0
    assert order["order_number"].startswith("ORD-")
    assert len(order["items"]) == 1
    assert order["items"][0]["unit_price"] == 60.0
    assert order["items"][0]["total_price"] == 3000.0

    # Verify order placed successfully without stock constraints
    prod_after = client.get("/api/products/1").json()
    assert prod_after["id"] == 1


def test_order_creation_without_stock_limits(client):
    payload = {
        "customer_name": "Large Buyer",
        "customer_phone": "9842100000",
        "address": "1 Main St",
        "city": "Chennai",
        "state": "Tamil Nadu",
        "pincode": "600001",
        "items": [
            {
                "product_id": 2,
                "quantity": 100
            }
        ]
    }
    response = client.post("/api/orders", json=payload)
    assert response.status_code == 201


def test_admin_orders_list_and_update(client, admin_headers):
    # List orders
    list_res = client.get("/api/admin/orders", headers=admin_headers)
    assert list_res.status_code == 200
    orders_data = list_res.json()
    assert orders_data["total"] >= 1
    target_order_id = orders_data["orders"][0]["id"]

    # Update status to Confirmed
    status_res = client.patch(
        f"/api/admin/orders/{target_order_id}/status",
        json={"status": "Confirmed"},
        headers=admin_headers
    )
    assert status_res.status_code == 200
    assert status_res.json()["order_status"] == "Confirmed"
