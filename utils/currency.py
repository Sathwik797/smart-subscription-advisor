"""Currency formatting utility for Indian Rupee (INR / ₹) standardizations."""

def format_inr(value, force_decimals=False):
    """
    Formats a numeric value into a standardized Indian Rupee (₹) currency string.
    Examples:
        499        -> "₹499"
        1299.5     -> "₹1,299.50"
        1999.99    -> "₹1,999.99"
        999.00 (with force_decimals=True) -> "₹999.00"
    """
    if value is None or value == "" or value == "—":
        return "₹—"
    try:
        val = float(value)
        if force_decimals or (val % 1 != 0):
            formatted = f"{val:,.2f}"
        else:
            formatted = f"{int(val):,}"
        return f"₹{formatted}"
    except (ValueError, TypeError):
        return f"₹{value}"
