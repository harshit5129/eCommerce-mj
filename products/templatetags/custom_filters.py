from django import template

register = template.Library()


@register.filter
def get_range(value):
    """Return a range from 1 to value."""
    return range(1, value + 1)


@register.filter
def multiply(value, arg):
    """Multiply value by arg."""
    try:
        return float(value) * float(arg)
    except (ValueError, TypeError):
        return 0


@register.filter
def div(value, arg):
    """Divide value by arg."""
    try:
        return float(value) / float(arg)
    except (ValueError, ZeroDivisionError, TypeError):
        return 0


@register.filter
def make_list(value):
    """Split a string by comma into a list."""
    if isinstance(value, str):
        return [item.strip() for item in value.split(',')]
    return value


@register.simple_tag
def currency(value):
    """Format value as Indian Rupees."""
    try:
        amount = float(value)
        return f"₹{amount:,.2f}"
    except (ValueError, TypeError):
        return "₹0.00"


@register.filter
def rupee(value):
    """Format value as Indian Rupees (filter version)."""
    try:
        amount = float(value)
        return f"₹{amount:,.2f}"
    except (ValueError, TypeError):
        return "₹0.00"


@register.filter
def discount_amount(price, compare_price):
    """Calculate discount amount."""
    try:
        return float(compare_price) - float(price)
    except (ValueError, TypeError):
        return 0


@register.filter
def status_display(value):
    """Convert status code to display text."""
    status_map = {
        'pending': 'Pending',
        'processing': 'Processing',
        'shipped': 'Shipped',
        'delivered': 'Delivered',
        'cancelled': 'Cancelled',
        'refunded': 'Refunded',
        'paid': 'Paid',
        'failed': 'Failed',
        'active': 'Active',
        'draft': 'Draft',
        'archived': 'Archived',
        'out_of_stock': 'Out of Stock',
        'coming_soon': 'Coming Soon',
    }
    return status_map.get(value, value.replace('_', ' ').title() if value else '')
