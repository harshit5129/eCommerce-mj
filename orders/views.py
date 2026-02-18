from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.views import View
from django.http import JsonResponse
from django.conf import settings
from django.core.mail import send_mail
import json
import uuid
from datetime import datetime

from orders.models import Order, OrderItem, ShippingAddress
from products.models import Product


def send_order_confirmation_email(order):
    """Send order confirmation email to customer."""
    items_list = "\n".join([
        f"  - {item.product_name} x {item.quantity} = ₹{item.price * item.quantity:,.2f}"
        for item in order.items
    ])
    
    message = f'''
Dear {order.shipping_address.first_name or 'Customer'},

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
{order.shipping_address.first_name} {order.shipping_address.last_name}
{order.shipping_address.street}
{order.shipping_address.city}, {order.shipping_address.state} {order.shipping_address.postal_code}
{order.shipping_address.country}
Phone: {order.shipping_address.phone}

PAYMENT METHOD
--------------
{'Cash on Delivery' if order.payment_method == 'cash' else order.payment_method.title()}

You can track your order status at: {settings.SITE_URL}/orders/

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


def send_order_cancellation_email(order):
    """Send order cancellation email to customer."""
    message = f'''
Dear {order.shipping_address.first_name or 'Customer'},

Your order has been cancelled as requested.

ORDER DETAILS
-------------
Order Number: {order.order_number}
Cancelled On: {order.cancelled_at.strftime('%B %d, %Y at %I:%M %p')}

Total Amount: ₹{order.total:,.2f}

If you paid online, a refund will be processed within 5-7 business days.
For Cash on Delivery orders, no payment was collected.

If you have any questions, please contact our support team.

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


class CheckoutView(View):
    """Checkout page for placing orders."""
    
    template_name = 'orders/checkout.html'
    
    def get(self, request):
        cart = request.session.get('cart', [])
        
        if not cart:
            messages.warning(request, 'Your cart is empty.')
            return redirect('cart')
        
        cart_total = sum(
            item.get('product_price', 0) * item.get('quantity', 1) 
            for item in cart
        )
        
        shipping_cost = 99 if cart_total < 4000 else 0
        tax = cart_total * 0.18
        total = cart_total + shipping_cost + tax
        
        user = None
        if request.session.get('user_id'):
            from users.mongo_models import User
            from bson import ObjectId
            try:
                user = User.objects.get(id=ObjectId(request.session.get('user_id')))
            except:
                try:
                    user_email = request.session.get('user_email')
                    if user_email:
                        user = User.objects.get(email=user_email)
                except:
                    pass
        
        context = {
            'cart': cart,
            'cart_total': cart_total,
            'shipping_cost': shipping_cost,
            'tax': tax,
            'total': total,
            'user': user,
        }
        return render(request, self.template_name, context)
    
    def post(self, request):
        cart = request.session.get('cart', [])
        
        if not cart:
            return JsonResponse({'error': 'Cart is empty'}, status=400)
        
        try:
            data = json.loads(request.body)
            
            address = data.get('shipping_address', {})
            
            user_id = request.session.get('user_id')
            user_email = request.session.get('user_email') or address.get('email')
            
            if not user_email:
                return JsonResponse({'error': 'Email is required'}, status=400)
            
            cart_total = sum(
                item.get('product_price', 0) * item.get('quantity', 1) 
                for item in cart
            )
            shipping_cost = 0 if cart_total >= 4000 else 99
            tax = cart_total * 0.18
            discount = float(data.get('discount', 0) if data.get('discount') else 0)
            total = cart_total + shipping_cost + tax - discount
            
            order_items = []
            for item in cart:
                order_items.append(OrderItem(
                    product_id=item.get('product_id'),
                    product_name=item.get('product_name'),
                    product_image=item.get('product_image'),
                    price=float(item.get('product_price', 0)),
                    quantity=int(item.get('quantity', 1)),
                ))
                
                product = Product.objects(id=item.get('product_id')).first()
                if product and product.track_inventory:
                    product.stock_quantity -= int(item.get('quantity', 1))
                    product.save()
            
            order_number = f"ORD-{datetime.utcnow().strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}"
            
            shipping_address = ShippingAddress(
                first_name=address.get('first_name', ''),
                last_name=address.get('last_name', ''),
                email=address.get('email', user_email),
                phone=address.get('phone', ''),
                street=address.get('street', ''),
                city=address.get('city', ''),
                state=address.get('state', ''),
                postal_code=address.get('postal_code', ''),
                country=address.get('country', 'India'),
            )
            
            order = Order(
                order_number=order_number,
                user_id=str(user_id) if user_id else 'guest',
                user_email=user_email,
                items=order_items,
                subtotal=cart_total,
                shipping_cost=shipping_cost,
                tax=tax,
                discount=discount,
                total=total,
                shipping_address=shipping_address,
                payment_method=data.get('payment_method', 'cash'),
                notes=data.get('notes', ''),
            )
            order.save()
            
            send_order_confirmation_email(order)
            
            request.session['cart'] = []
            request.session.modified = True
            
            return JsonResponse({
                'success': True,
                'order_number': order_number,
                'redirect_url': f'/orders/success/?order={order_number}',
            })
        
        except Exception as e:
            import traceback
            traceback.print_exc()
            return JsonResponse({'error': str(e)}, status=500)


class OrderSuccessView(View):
    """Order success page."""
    
    template_name = 'orders/success.html'
    
    def get(self, request):
        order_number = request.GET.get('order')
        order = Order.objects(order_number=order_number).first()
        
        if not order:
            messages.error(request, 'Order not found.')
            return redirect('home')
        
        return render(request, self.template_name, {'order': order})


class OrderHistoryView(View):
    """User order history page."""
    
    template_name = 'orders/order_history.html'
    
    def get(self, request):
        user_id = request.session.get('user_id')
        user_email = request.session.get('user_email')
        
        if not user_id and not user_email:
            messages.warning(request, 'Please login to view your orders.')
            return redirect('login')
        
        orders = Order.objects(user_email=user_email).order_by('-created_at')
        
        return render(request, self.template_name, {'orders': orders})


class OrderDetailView(View):
    """Order detail page."""
    
    template_name = 'orders/order_detail.html'
    
    def get(self, request, order_number):
        user_id = request.session.get('user_id')
        user_email = request.session.get('user_email')
        
        if not user_id and not user_email:
            messages.warning(request, 'Please login to view order details.')
            return redirect('login')
        
        order = Order.objects(order_number=order_number, user_email=user_email).first()
        
        if not order:
            messages.error(request, 'Order not found.')
            return redirect('order_history')
        
        return render(request, self.template_name, {'order': order})


def cancel_order(request):
    """Cancel an order."""
    if request.method != 'POST':
        return JsonResponse({'error': 'Invalid request method'}, status=405)
    
    user_email = request.session.get('user_email')
    
    if not user_email:
        return JsonResponse({'error': 'Please login to cancel orders'}, status=401)
    
    try:
        data = json.loads(request.body)
        order_number = data.get('order_number')
        
        if not order_number:
            return JsonResponse({'error': 'Order number is required'}, status=400)
        
        order = Order.objects(order_number=order_number, user_email=user_email).first()
        
        if not order:
            return JsonResponse({'error': 'Order not found or you are not authorized'}, status=404)
        
        if order.order_status not in ['pending', 'processing']:
            return JsonResponse({
                'error': f'Order cannot be cancelled. Current status: {order.order_status.title()}. Only pending and processing orders can be cancelled.'
            }, status=400)
        
        for item in order.items:
            product = Product.objects(id=item.product_id).first()
            if product and product.track_inventory:
                product.stock_quantity += item.quantity
                product.save()
        
        order.order_status = 'cancelled'
        order.cancelled_at = datetime.utcnow()
        order.save()
        
        send_order_cancellation_email(order)
        
        return JsonResponse({
            'success': True,
            'message': 'Order cancelled successfully',
        })
    
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JsonResponse({'error': str(e)}, status=500)
