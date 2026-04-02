"""PFS target: Pattern 3 — result-dict error reporting."""


def handle_payment(payment_data):
    """Pattern 3: result dict with success/error keys."""
    if not payment_data.get("amount"):
        return {"success": False, "error": "missing amount"}
    if payment_data["amount"] <= 0:
        return {"success": False, "error": "invalid amount"}
    return {"success": True, "transaction_id": "tx_123"}


def handle_refund(refund_data):
    """Pattern 3 variant: result dict."""
    if not refund_data.get("transaction_id"):
        return {"success": False, "error": "missing transaction"}
    return {"success": True, "refund_id": "rf_456"}
