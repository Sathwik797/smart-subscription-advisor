from decimal import Decimal


def format_inr(value, force_decimals=False):
    """
    Format a numeric value into a standardized Indian Rupee (₹) currency string
    following the Indian numbering system.

    Examples:
        499        -> "₹499"
        1299       -> "₹1,299"
        12999      -> "₹12,999"
        124999     -> "₹1,24,999"
        199.99     -> "₹199.99"
        499.50     -> "₹499.50"
        1299.75    -> "₹1,299.75"
    """
    if value is None or value == "" or value == "—":
        return "₹—"
    try:
        if isinstance(value, Decimal):
            d_val = value
        else:
            d_val = Decimal(str(value))
    except Exception:
        return f"₹{value}"

    # Determine whether to show decimal places
    is_fractional = force_decimals or (d_val % Decimal("1") != Decimal("0"))

    if is_fractional:
        quantized = d_val.quantize(Decimal("0.01"))
        sign = "-" if quantized < 0 else ""
        abs_val = abs(quantized)
        s_val = f"{abs_val:.2f}"
        int_part, dec_part = s_val.split(".")
    else:
        sign = "-" if d_val < 0 else ""
        int_part = str(abs(int(d_val)))
        dec_part = None

    # Apply Indian numbering grouping (last 3 digits, then chunks of 2)
    if len(int_part) <= 3:
        formatted_int = int_part
    else:
        last3 = int_part[-3:]
        rest = int_part[:-3]
        chunks = []
        while len(rest) > 2:
            chunks.insert(0, rest[-2:])
            rest = rest[:-2]
        if rest:
            chunks.insert(0, rest)
        formatted_int = ",".join(chunks) + "," + last3

    if dec_part is not None:
        return f"₹{sign}{formatted_int}.{dec_part}"
    return f"₹{sign}{formatted_int}"

