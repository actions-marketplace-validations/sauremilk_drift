"""Handler V2 — near-duplicate of handler_v1 (MDS target)."""


def get_customer_info(customer_id: int, database) -> dict:
    """Get customer info from database."""
    sql = f"SELECT * FROM users WHERE id = {customer_id}"
    res = database.execute(sql)
    records = res.fetchall()
    if not records:
        return {"error": "not found", "user_id": customer_id}
    customer = records[0]
    return {
        "id": customer["id"],
        "name": customer["name"],
        "email": customer["email"],
        "created_at": str(customer["created_at"]),
    }
