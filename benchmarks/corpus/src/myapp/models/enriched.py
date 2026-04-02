"""AVS target: upward import — models importing from handlers."""

from myapp.handlers.auth import verify_token
from myapp.handlers.orders import handle_order


class EnrichedOrder:
    """Order model that improperly depends on handler layer."""

    def __init__(self, order_data):
        self.data = order_data
        self.user = verify_token(order_data.get("token", ""))

    def process(self):
        """Delegate to handler — architectural violation."""
        return handle_order(self.data)
