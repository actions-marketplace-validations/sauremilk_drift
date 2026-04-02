"""MDS target: duplicate utility functions."""


def format_currency(amount, currency="USD"):
    """Format a monetary amount."""
    symbols = {"USD": "$", "EUR": "€", "GBP": "£"}
    symbol = symbols.get(currency, currency)
    return f"{symbol}{amount:,.2f}"


def format_money(value, curr="USD"):
    """Format a monetary value (near-duplicate of format_currency)."""
    symbol_map = {"USD": "$", "EUR": "€", "GBP": "£"}
    sym = symbol_map.get(curr, curr)
    return f"{sym}{value:,.2f}"
