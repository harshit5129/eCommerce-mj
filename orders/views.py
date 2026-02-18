from django.shortcuts import render, redirect
from django.contrib import messages
from django.views import View
from django.http import JsonResponse
from django.conf import settings
from django.core.mail import send_mail
from django.views.decorators.csrf import csrf_protect
from django.utils.decorators import method_decorator
from django.db import transaction
from django.db.models import F
from django.core.cache import cache
from decimal import Decimal, ROUND_HALF_UP
import json
import uuid
import logging
import re
from datetime import datetime

from orders.models import Order, OrderItem
from products.models import Product
from offers.models import Coupon, CouponUsage

logger = logging.getLogger(__name__)


def validate_id(id_string):
    """Validate that ID is a valid integer."""
    if not id_string:
        return None
    try:
        return int(id_string)
    except (ValueError, TypeError):
        return None


def parse_json_body(request, max_size=1024*512):
    """Safely parse JSON request body with size limit (512KB max)."""
    if len(request.body) > max_size:
        raise ValueError("Request body too large")
    
    try:
        return json.loads(request.body.decode('utf-8'))
    except (json.JSONDecodeError, UnicodeDecodeError) as e:
        raise ValueError(f"Invalid JSON: {str(e)}")


def sanitize_email_header(value):
    """Prevent email header injection."""
    if not value:
        return ''
    return re.sub(r'[\r\n]', '', str(value))[:200]


def calculate_order_totals(cart_items, coupon_code=None, user_email=None):
    """
    Calculate order totals server-side with Decimal precision.
    Returns tuple: (subtotal, shipping, tax, discount, total)
    """
    subtotal = Decimal('0')
    for item in cart_items:
        try:
            price = Decimal(str(item.get('product_price', 0)))
            qty = int(item.get('quantity', 1))
            subtotal += price * qty
        except (ValueError, TypeError):
            continue
    
    # Free shipping over ₹4000
    shipping = Decimal('0') if subtotal >= Decimal('4000') else Decimal('99')
    
    # Tax (18% GST)
    tax = (subtotal * Decimal('0.18')).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    
    # Calculate discount
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


def send_order_confirmation_email(order):
    """Send order confirmation email to customer."""
    try:
        # Use select_related/prefetch_related to avoid N+1
        items = order.items.all()
        
        items_list = "\n".join([
            f"  - {sanitize_email_header(item.product_name)} x {item.quantity} = ₹{item.price * item.quantity:,.2f}"
            for item in items
        ])
        
        first_name = sanitize_email_header(order.shipping_address.get('first_name', ''))
        
        message = f'''Dear {first_name or 'Customer'},

Thank you for your order! Your order has been successfully placed.

ORDER DETAILS
-------------
Order Number: {order.order_number}
Order Date: {order.created_at.strftime('%B %d, %Y at %I:%M %p')}

ITEMS ORDERED:
{items_list}

ORDER SUMMARY
-------------
Subtotal: ₹{order.subtotal:,.2f}
Shipping: {'FREE' if order.shipping_cost == 0 else f'₹{order.shipping_cost:,.2f}'}
Tax (18% GST): ₹{order.tax:,.2f}
{f'Discount: -₹{order.discount:,.2f}' if order.discount > 0 else ''}
-----------------------------------
TOTAL: ₹{order.total:,.2f}

SHIPPING ADDRESS
----------------
{sanitize_email_header(order.shipping_address.get('first_name', ''))} {sanitize_email_header(order.shipping_address.get('last_name', ''))}
{sanitize_email_header(order.shipping_address.get('street', ''))}
{sanitize_email_header(order.shipping_address.get('city', ''))}, {sanitize_email_header(order.shipping_address.get('state', ''))} {sanitize_email_header(order.shipping_address.get('postal_code', ''))}
Phone: {sanitize_email_header(order.shipping_address.get('phone', ''))}

PAYMENT METHOD
--------------
Online Payment (Razorpay)

Thank you for shopping with us!

Best regards,
{settings.SITE_NAME} Team
'''
        
        send_mail(
            subject=f'Order Confirmed - {order.order_number} | {settings.SITE_NAME}',
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[order.user_email],
            fail_silently=True,
        )
    except Exception as e:
        logger.error(f"Failed to send order confirmation email: {e}")


def send_order_cancellation_email(order):
    """Send order cancellation email to customer."""
    try:
        first_name = sanitize_email_header(order.shipping_address.get('first_name', ''))
        
        message = f'''Dear {first_name or 'Customer'},

Your order has been cancelled as requested.

ORDER DETAILS
-------------
Order Number: {order.order_number}
Cancelled On: {order.cancelled_at.strftime('%B %d, %Y at %I:%M %p')}
Total Amount: ₹{order.total:,.2f}

If your payment was already processed, a refund will be issued within 5-7 business days.

Best regards,
{settings.SITE_NAME} Team
'''
        
        send_mail(
            subject=f'Order Cancelled - {order.order_number} | {settings.SITE_NAME}',
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[order.user_email],
            fail_silently=True,
        )
    except Exception as e:
        logger.error(f"Failed to send cancellation email: {e}")


def validate_cart_items(cart):
    """Validate all cart items and return products dict."""
    errors = []
    products = {}
    
    for item in cart:
        product_id = validate_id(item.get('product_id'))
        if not product_id:
            errors.append('Invalid product in cart')
            continue
        
        try:
            product = Product.objects.get(id=product_id, is_active=True)
            quantity = int(item.get('quantity', 1))
            
            if product.track_inventory and product.stock_quantity < quantity:
                errors.append(f'Insufficient stock for {product.name}. Only {product.stock_quantity} available.')
            else:
                products[product_id] = product
        except Product.DoesNotExist:
            errors.append(f'Product no longer available')
    
    return products, errors


@method_decorator(csrf_protect, name='dispatch')
class CheckoutView(View):
    """Checkout page for placing orders."""
    
    template_name = 'orders/checkout.html'
    
    def get(self, request):
        cart = request.session.get('cart', [])
        
        if not cart:
            messages.warning(request, 'Your cart is empty.')
            return redirect('cart')
        
        subtotal, shipping, tax, discount, total = calculate_order_totals(cart)
        
        user = None
        if request.user.is_authenticated:
            user = request.user
        
        context = {
            'cart': cart,
            'cart_total': float(subtotal),
            'shipping_cost': float(shipping),
            'tax': float(tax),
            'total': float(total),
            'user': user,
        }
        return render(request, self.template_name, context)
    
    def post(self, request):
        cart = request.session.get('cart', [])
        
        if not cart:
            return JsonResponse({'error': 'Cart is empty'}, status=400)
        
        try:
            data = parse_json_body(request)
            address = data.get('shipping_address', {})
            
            # Validate required fields
            required_fields = ['first_name', 'last_name', 'email', 'street', 'city', 'state', 'postal_code']
            missing = [f for f in required_fields if not address.get(f)]
            if missing:
                return JsonResponse({
                    'error': f'{missing[0].replace("_", " ").title()} is required'
                }, status=400)
            
            # Get user info
            user_id = str(request.user.id) if request.user.is_authenticated else 'guest'
            user_email = request.user.email if request.user.is_authenticated else address.get('email')
            
            if not user_email:
                return JsonResponse({'error': 'Email is required'}, status=400)
            
            # Validate email format
            email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
            if not re.match(email_pattern, user_email):
                return JsonResponse({'error': 'Invalid email format'}, status=400)
            
            # Calculate totals
            coupon_code = data.get('coupon_code')
            subtotal, shipping, tax, discount, total = calculate_order_totals(
                cart, coupon_code=coupon_code, user_email=user_email
            )
            
            # Validate cart items
            products, errors = validate_cart_items(cart)
            if errors:
                return JsonResponse({'error': errors[0]}, status=400)
            
            # Generate order number
            order_number = f"ORD-{datetime.utcnow().strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}"
            
            with transaction.atomic():
                # Create order
                order = Order.objects.create(
                    order_number=order_number,
                    user_id=user_id,
                    user_email=user_email[:100],
                    subtotal=float(subtotal),
                    shipping_cost=float(shipping),
                    tax=float(tax),
                    discount=float(discount),
                    total=float(total),
                    shipping_address={
                        'first_name': address.get('first_name', '')[:50],
                        'last_name': address.get('last_name', '')[:50],
                        'email': user_email[:100],
                        'phone': address.get('phone', '')[:20],
                        'street': address.get('street', '')[:200],
                        'city': address.get('city', '')[:50],
                        'state': address.get('state', '')[:50],
                        'postal_code': address.get('postal_code', '')[:20],
                        'country': address.get('country', 'India')[:50],
                    },
                    payment_method='razorpay',
                    notes=data.get('notes', '')[:500],
                )
                
                # Create order items and deduct inventory
                for item in cart:
                    product_id = int(item.get('product_id'))
                    quantity = int(item.get('quantity', 1))
                    product = products.get(product_id)
                    
                    if not product:
                        continue
                    
                    # Deduct inventory atomically
                    if product.track_inventory:
                        Product.objects.filter(id=product_id).update(
                            stock_quantity=F('stock_quantity') - quantity
                        )
                    
                    OrderItem.objects.create(
                        order=order,
                        product_id=product_id,
                        product_name=item.get('product_name', product.name)[:255],
                        product_sku=product.sku[:100] if product.sku else '',
                        product_image=item.get('product_image', '')[:500],
                        price=float(item.get('product_price', product.price)),
                        quantity=quantity,
                    )
                
                # Record coupon usage
                if coupon_code and discount > 0:
                    try:
                        coupon = Coupon.objects.get(code=coupon_code.upper(), is_active=True)
                        CouponUsage.objects.create(
                            coupon=coupon,
                            user_email=user_email,
                            order_number=order_number,
                            discount_amount=float(discount),
                        )
                        coupon.used_count = F('used_count') + 1
                        coupon.save(update_fields=['used_count'])
                    except Coupon.DoesNotExist:
                        pass
            
            # Store order number in session for payment
            request.session['pending_order_number'] = order_number
            request.session.modified = True
            
            # Invalidate product caches
            for product_id in products.keys():
                cache.delete(f"product_detail:{products[product_id].slug}")
            
            logger.info(f"Order created: {order_number} by {user_email}")
            
            return JsonResponse({
                'success': True,
                'order_number': order_number,
                'requires_payment': True,
            })
        
        except ValueError as e:
            return JsonResponse({'error': str(e)}, status=400)
        except Exception as e:
            logger.error(f"Order creation failed: {e}", exc_info=True)
            return JsonResponse({'error': 'An error occurred. Please try again.'}, status=500)


class OrderSuccessView(View):
    """Order success page."""
    
    template_name = 'orders/success.html'
    
    def get(self, request):
        order_number = request.GET.get('order')
        if not order_number:
            messages.error(request, 'Order number required.')
            return redirect('home')
        
        try:
            order = Order.objects.prefetch_related('items').get(order_number=order_number)
        except Order.DoesNotExist:
            messages.error(request, 'Order not found.')
            return redirect('home')
        
        # Security: Verify user is authorized to view this order
        if request.user.is_authenticated:
            if order.user_id != str(request.user.id) and not request.user.is_staff:
                messages.error(request, 'You are not authorized to view this order.')
                return redirect('home')
        else:
            # For guest orders, verify session has pending order number matching
            pending_order = request.session.get('pending_order_number')
            if pending_order != order_number:
                messages.error(request, 'Please login to view order details.')
                return redirect('login')
        
        if order.payment_status == 'pending':
            messages.warning(request, 'Payment is pending for this order.')
        
        return render(request, self.template_name, {'order': order})


class OrderHistoryView(View):
    """User order history page."""
    
    template_name = 'orders/order_history.html'
    
    def get(self, request):
        if not request.user.is_authenticated:
            messages.warning(request, 'Please login to view your orders.')
            return redirect('login')
        
        # Use select_related and only fetch needed fields
        orders = Order.objects.filter(
            user_id=str(request.user.id)
        ).order_by('-created_at')[:50]
        
        return render(request, self.template_name, {'orders': orders})


class OrderDetailView(View):
    """Order detail page."""
    
    template_name = 'orders/order_detail.html'
    
    def get(self, request, order_number):
        if not request.user.is_authenticated:
            messages.warning(request, 'Please login to view order details.')
            return redirect('login')
        
        try:
            order = Order.objects.prefetch_related('items').get(
                order_number=order_number, 
                user_id=str(request.user.id)
            )
        except Order.DoesNotExist:
            messages.error(request, 'Order not found.')
            return redirect('order_history')
        
        return render(request, self.template_name, {'order': order})


@csrf_protect
def cancel_order(request):
    """Cancel an order."""
    if request.method != 'POST':
        return JsonResponse({'error': 'Invalid request method'}, status=405)
    
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Please login to cancel orders'}, status=401)
    
    try:
        data = parse_json_body(request)
        order_number = data.get('order_number')
        
        if not order_number:
            return JsonResponse({'error': 'Order number is required'}, status=400)
        
        try:
            order = Order.objects.prefetch_related('items').get(
                order_number=order_number, 
                user_id=str(request.user.id)
            )
        except Order.DoesNotExist:
            return JsonResponse({'error': 'Order not found'}, status=404)
        
        if order.order_status not in ['pending', 'processing']:
            return JsonResponse({
                'error': f'Cannot cancel order with status: {order.order_status.title()}'
            }, status=400)
        
        with transaction.atomic():
            # Restore inventory
            for item in order.items.all():
                try:
                    Product.objects.filter(id=item.product_id, track_inventory=True).update(
                        stock_quantity=F('stock_quantity') + item.quantity
                    )
                except Exception:
                    pass
            
            order.order_status = 'cancelled'
            order.cancelled_at = datetime.utcnow()
            order.save(update_fields=['order_status', 'cancelled_at'])
        
        send_order_cancellation_email(order)
        
        logger.info(f"Order cancelled: {order_number}")
        
        return JsonResponse({'success': True, 'message': 'Order cancelled successfully'})
    
    except Exception as e:
        logger.error(f"Order cancellation failed: {e}", exc_info=True)
        return JsonResponse({'error': 'An error occurred'}, status=500)
