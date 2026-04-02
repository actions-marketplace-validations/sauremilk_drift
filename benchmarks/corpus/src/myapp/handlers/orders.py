"""PFS target: Pattern 2 — custom exception classes."""


class OrderError(Exception):
    """Custom order error."""


class PaymentError(Exception):
    """Custom payment error."""


def handle_order(order_data):
    """Pattern 2: custom exception hierarchy."""
    if not order_data.get("items"):
        raise OrderError("Empty order")
    total = sum(item["price"] for item in order_data["items"])
    if total <= 0:
        raise PaymentError("Invalid total")
    return {"status": "ok", "total": total}
