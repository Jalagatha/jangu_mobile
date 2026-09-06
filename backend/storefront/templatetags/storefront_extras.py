from decimal import Decimal, InvalidOperation

from django import template

register = template.Library()


@register.filter
def ugx(value):
    """Format a number as `UGX 2,800,000` (no decimals)."""
    if value is None or value == "":
        return "—"
    try:
        amount = int(round(Decimal(str(value))))
    except (InvalidOperation, ValueError, TypeError):
        return "—"
    return f"UGX {amount:,}"


@register.filter
def variant_label(attributes):
    """`{"storage": "128GB", "color": "Black"}` -> `128GB / Black`; `{}` -> `Standard`."""
    if not isinstance(attributes, dict) or not attributes:
        return "Standard"
    return " / ".join(str(v) for v in attributes.values())
