"""EDS target: high complexity function without documentation."""


def calculate_pricing(items, user, config):
    total = 0
    for item in items:
        price = item["price"]
        qty = item.get("quantity", 1)
        if user.get("membership") == "gold":
            if qty > 10:
                discount = 0.20
            elif qty > 5:
                discount = 0.15
            else:
                discount = 0.10
        elif user.get("membership") == "silver":
            if qty > 10:
                discount = 0.12
            elif qty > 5:
                discount = 0.08
            else:
                discount = 0.05
        else:
            if qty > 20:
                discount = 0.05
            else:
                discount = 0
        subtotal = price * qty * (1 - discount)
        if config.get("tax_enabled"):
            tax_rate = config.get("tax_rate", 0.19)
            if item.get("category") == "food":
                tax_rate = config.get("food_tax_rate", 0.07)
            elif item.get("category") == "medicine":
                tax_rate = 0
            subtotal *= (1 + tax_rate)
        if config.get("shipping"):
            if total > config.get("free_shipping_threshold", 100):
                pass
            elif item.get("weight", 0) > 30:
                subtotal += config.get("heavy_shipping", 15)
            else:
                subtotal += config.get("standard_shipping", 5)
        total += subtotal
    if user.get("coupon"):
        coupon = user["coupon"]
        if coupon.get("type") == "percent":
            total *= (1 - coupon["value"] / 100)
        elif coupon.get("type") == "fixed":
            total -= coupon["value"]
        if total < 0:
            total = 0
    return round(total, 2)
