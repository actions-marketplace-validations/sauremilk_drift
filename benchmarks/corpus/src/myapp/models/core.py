"""PFS target (return patterns): 3 variants in models layer."""


class User:
    """User model — return pattern variant 1: None."""

    def __init__(self, name, email):
        self.name = name
        self.email = email

    def find_by_email(self, email):
        """Return None on not-found."""
        if email == self.email:
            return self
        return None


class Product:
    """Product model — return pattern variant 2: raise."""

    def __init__(self, sku, price):
        self.sku = sku
        self.price = price

    def find_by_sku(self, sku):
        """Raise on not-found."""
        if sku == self.sku:
            return self
        raise ValueError(f"Product not found: {sku}")


class Inventory:
    """Inventory model — return pattern variant 3: tuple."""

    def __init__(self, items):
        self.items = items

    def check_stock(self, sku):
        """Return (found, item) tuple."""
        for item in self.items:
            if item["sku"] == sku:
                return (True, item)
        return (False, None)
