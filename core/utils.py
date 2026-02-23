"""
Shared utility functions for the E-Commerce application.
"""

import re
import math
from decimal import Decimal, ROUND_HALF_UP


def validate_id(id_string):
    """Validate that ID is a valid integer."""
    if not id_string:
        return None
    try:
        return int(id_string)
    except (ValueError, TypeError):
        return None


def validate_quantity(quantity, min_val=1, max_val=999):
    """Validate quantity is a positive integer within reasonable limits."""
    try:
        qty = int(quantity)
        if not min_val <= qty <= max_val:
            return None, f'Quantity must be between {min_val} and {max_val}'
        return qty, None
    except (ValueError, TypeError):
        return None, 'Invalid quantity format'


def validate_email(email):
    """Validate email format."""
    if not email:
        return False
    email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(email_pattern, email))


def validate_password_strength(password):
    """
    Validate password strength.
    Returns (is_valid, errors) tuple.
    """
    errors = []
    
    if len(password) < 8:
        errors.append('Password must be at least 8 characters long')
    
    if not re.search(r'[A-Z]', password):
        errors.append('Password must contain at least one uppercase letter')
    
    if not re.search(r'[a-z]', password):
        errors.append('Password must contain at least one lowercase letter')
    
    if not re.search(r'\d', password):
        errors.append('Password must contain at least one digit')
    
    if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
        errors.append('Password must contain at least one special character')
    
    return len(errors) == 0, errors


def sanitize_email_header(value):
    """Prevent email header injection."""
    if not value:
        return ''
    return re.sub(r'[\r\n]', '', str(value))[:200]


def parse_json_body(request, max_size=1024*512):
    """Safely parse JSON request body with size limit (512KB max)."""
    import json
    
    if len(request.body) > max_size:
        raise ValueError("Request body too large")
    
    try:
        return json.loads(request.body.decode('utf-8'))
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON: {str(e)}")
    except UnicodeDecodeError as e:
        raise ValueError(f"Invalid encoding: {str(e)}")


def calculate_order_totals(cart_items, coupon_code=None, user_email=None, settings_obj=None):
    """
    Calculate order totals server-side with Decimal precision.
    Returns tuple: (subtotal, shipping, tax, discount, total)
    """
    from offers.models import Coupon
    
    subtotal = Decimal('0')
    for item in cart_items:
        try:
            price = Decimal(str(item.get('product_price', 0)))
            qty = int(item.get('quantity', 1))
            subtotal += price * qty
        except (ValueError, TypeError):
            continue
    
    free_shipping_threshold = Decimal(str(getattr(settings_obj, 'free_shipping_threshold', 4000)))
    shipping_cost = Decimal(str(getattr(settings_obj, 'shipping_cost', 99)))
    tax_rate = Decimal(str(getattr(settings_obj, 'tax_rate', 18))) / 100
    
    shipping = Decimal('0') if subtotal >= free_shipping_threshold else shipping_cost
    
    tax = (subtotal * tax_rate).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    
    discount = Decimal('0')
    if coupon_code and user_email:
        try:
            coupon = Coupon.objects.get(code=coupon_code.upper(), is_active=True)
            can_use, _ = coupon.can_use(user_email)
            if can_use and coupon.is_valid:
                discount_val = coupon.calculate_discount(float(subtotal))
                discount = Decimal(str(discount_val)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
                discount = min(discount, subtotal)
        except Coupon.DoesNotExist:
            pass
    
    total = (subtotal + shipping + tax - discount).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    
    return subtotal, shipping, tax, discount, total


def get_client_ip(request):
    """Get client IP address from request."""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        return x_forwarded_for.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR', '127.0.0.1')


def generate_slug(name):
    """Generate a URL-safe slug from a name."""
    from django.utils.text import slugify
    return slugify(name)


def get_pagination_bounds(page, per_page, total_items):
    """Calculate pagination bounds."""
    total_pages = math.ceil(total_items / per_page) if total_items > 0 else 1
    page = max(1, min(page, total_pages))
    start = (page - 1) * per_page
    end = start + per_page
    return page, total_pages, start, end
