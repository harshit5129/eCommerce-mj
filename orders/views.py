from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.views import View
from django.http import JsonResponse
from django.conf import settings
import json
import uuid
from datetime import datetime

from orders.models import Order, OrderItem, ShippingAddress
from products.models import Product


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
        
        shipping_cost = 9.99 if cart_total < 50 else 0
        tax = cart_total * 0.08
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
            user_email = request.session.get('user_email', data.get('email'))
            
            cart_total = sum(
                item.get('product_price', 0) * item.get('quantity', 1) 
                for item in cart
            )
            shipping_cost = float(data.get('shipping_cost', 9.99))
            tax = float(data.get('tax', 0))
            discount = float(data.get('discount', 0))
            total = cart_total + shipping_cost + tax - discount
            
            order_items = []
            for item in cart:
                order_items.append(OrderItem(
                    product_id=item.get('product_id'),
                    product_name=item.get('product_name'),
                    product_image=item.get('product_image'),
                    price=item.get('product_price'),
                    quantity=item.get('quantity'),
                ))
                
                product = Product.objects(id=item.get('product_id')).first()
                if product and product.track_inventory:
                    product.stock_quantity -= item.get('quantity', 1)
                    product.save()
            
            order_number = f"ORD-{datetime.utcnow().strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}"
            
            shipping_address = ShippingAddress(
                first_name=address.get('first_name'),
                last_name=address.get('last_name'),
                email=address.get('email'),
                phone=address.get('phone'),
                street=address.get('street'),
                city=address.get('city'),
                state=address.get('state'),
                postal_code=address.get('postal_code'),
                country=address.get('country', 'USA'),
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
            
            request.session['cart'] = []
            request.session.modified = True
            
            return JsonResponse({
                'success': True,
                'order_number': order_number,
                'redirect_url': f'/orders/success/?order={order_number}',
            })
        
        except Exception as e:
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
        
        # Try to get MongoDB user for proper ID
        user_id_to_use = str(user_id) if user_id else None
        if not user_id_to_use or len(str(user_id_to_use)) < 20:
            # Try to get MongoDB user by email
            from users.mongo_models import User
            try:
                mongo_user = User.objects.get(email=user_email)
                user_id_to_use = str(mongo_user.id)
            except:
                pass
        
        orders = Order.objects(user_id=user_id_to_use).order_by('-created_at')
        
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
        
        # Try to get MongoDB user for proper ID
        user_id_to_use = str(user_id) if user_id else None
        if not user_id_to_use or len(str(user_id_to_use)) < 20:
            from users.mongo_models import User
            try:
                mongo_user = User.objects.get(email=user_email)
                user_id_to_use = str(mongo_user.id)
            except:
                pass
        
        order = Order.objects(order_number=order_number, user_id=user_id_to_use).first()
        
        if not order:
            messages.error(request, 'Order not found.')
            return redirect('order_history')
        
        return render(request, self.template_name, {'order': order})


def cancel_order(request):
    """Cancel an order."""
    if request.method != 'POST':
        return JsonResponse({'error': 'Invalid request method'}, status=405)
    
    user_id = request.session.get('user_id')
    user_email = request.session.get('user_email')
    
    if not user_id and not user_email:
        return JsonResponse({'error': 'Please login'}, status=401)
    
    # Get proper user_id
    user_id_to_use = str(user_id) if user_id else None
    if not user_id_to_use or len(str(user_id_to_use)) < 20:
        from users.mongo_models import User
        try:
            mongo_user = User.objects.get(email=user_email)
            user_id_to_use = str(mongo_user.id)
        except:
            pass
    
    try:
        data = json.loads(request.body)
        order_number = data.get('order_number')
        
        order = Order.objects(order_number=order_number, user_id=user_id_to_use).first()
        
        if not order:
            return JsonResponse({'error': 'Order not found'}, status=404)
        
        if not order.is_cancellable:
            return JsonResponse({'error': 'Order cannot be cancelled'}, status=400)
        
        for item in order.items:
            product = Product.objects(id=item.product_id).first()
            if product and product.track_inventory:
                product.stock_quantity += item.quantity
                product.save()
        
        order.order_status = 'cancelled'
        from datetime import datetime
        order.cancelled_at = datetime.utcnow()
        order.save()
        
        return JsonResponse({
            'success': True,
            'message': 'Order cancelled successfully',
        })
    
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)
