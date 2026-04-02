"""AVS target: transitive layer violation — utils importing models importing handlers."""

from myapp.models.enriched import EnrichedOrder


def build_order_summary(raw_data):
    """Transitive violation: utils -> models -> handlers."""
    order = EnrichedOrder(raw_data)
    result = order.process()
    return {
        "summary": True,
        "total": result.get("total", 0),
        "user": str(order.user),
    }
