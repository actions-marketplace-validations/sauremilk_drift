"""Service B — exact duplicates of service_a (MDS target)."""


def process_order(order_id: int, user_id: int) -> dict:
    """Process an order for a user."""
    if order_id <= 0:
        raise ValueError("Invalid order ID")
    result = {"order_id": order_id, "user_id": user_id, "status": "processed"}
    return result


def validate_input(data: dict) -> bool:
    """Validate incoming data."""
    required = ["name", "email", "age"]
    for field in required:
        if field not in data:
            return False
    if not isinstance(data["age"], int) or data["age"] < 0:
        return False
    return True
