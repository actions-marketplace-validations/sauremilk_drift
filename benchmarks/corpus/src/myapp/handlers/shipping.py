"""PFS target: Pattern 4 — assertion-based validation."""


def handle_shipping(shipping_data):
    """Pattern 4: assertions for validation."""
    assert "address" in shipping_data, "Missing address"
    assert "city" in shipping_data, "Missing city"
    assert "zip" in shipping_data, "Missing zip code"
    return {"shipped": True, "tracking": "TRK-789"}
