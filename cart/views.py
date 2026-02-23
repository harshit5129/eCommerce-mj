from django.shortcuts import render
from django.contrib import messages
from django.views import View
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_protect
from django.utils.decorators import method_decorator
from django.core.cache import cache
from decimal import Decimal, ROUND_HALF_UP
import json
import logging

from products.models import Product

logger = logging.getLogger(__name__)


def get_site_settings():
    """Get cached site settings."""
    from core.models import SiteSettings
    cache_key = 'site_settings'
    settings = cache.get(cache_key)
    if settings is None:
        settings = SiteSettings.get_settings()
        cache.set(cache_key, settings, 300)
    return settings


def validate_quantity(quantity):
    """Validate quantity is a positive integer within reasonable limits."""
    try:
        qty = int(quantity)
        if not 1 <= qty <= 999:
            return None, 'Quantity must be between 1 and 999'
        return qty, None
    except (ValueError, TypeError):
        return None, 'Invalid quantity format'


class CartView(View):
    """Shopping cart page."""
    
    template_name = 'cart/cart.html'
    
    def get(self, request):
        cart_items = request.session.get('cart', [])
        
        site_settings = get_site_settings()
        
        for item in cart_items:
            item['total'] = item.get('product_price', 0) * item.get('quantity', 1)
        
        cart_total = sum(item.get('total', 0) for item in cart_items)
        
        coupon_data = request.session.get('applied_coupon', {})
        coupon_code = coupon_data.get('code') if coupon_data else None
        
        user_email = request.user.email if request.user.is_authenticated else None
        
        discount = 0
        valid_coupon = None
        if coupon_code and user_email:
            from offers.models import Coupon
            try:
                coupon = Coupon.objects.get(code=coupon_code.upper(), is_active=True)
                can_use, _ = coupon.can_use(user_email)
                if can_use and coupon.is_valid:
                    discount = coupon.calculate_discount(cart_total)
                    discount = min(discount, cart_total)
                    valid_coupon = coupon
                else:
                    del request.session['applied_coupon']
                    request.session.modified = True
                    coupon_code = None
            except Coupon.DoesNotExist:
                del request.session['applied_coupon']
                request.session.modified = True
                coupon_code = None
        elif coupon_code and not user_email:
            del request.session['applied_coupon']
            request.session.modified = True
            coupon_code = None
        
        free_shipping_threshold = float(site_settings.free_shipping_threshold)
        shipping_cost = float(site_settings.shipping_cost)
        shipping = 0 if cart_total >= free_shipping_threshold else shipping_cost
        
        tax_rate = float(site_settings.tax_rate) / 100
        tax = cart_total * tax_rate
        
        order_total = cart_total + shipping + tax - discount
        
        context = {
            'cart_items': cart_items,
            'cart_total': cart_total,
            'shipping_cost': shipping,
            'tax': tax,
            'discount': discount,
            'order_total': order_total,
            'coupon_code': coupon_code if valid_coupon else None,
            'site_settings': site_settings,
        }
        return render(request, self.template_name, context)


@csrf_protect
def add_to_cart(request):
    """Add product to cart via AJAX."""
    if request.method != 'POST':
        return JsonResponse({'error': 'Invalid request method'}, status=405)
    
    try:
        data = json.loads(request.body)
        product_id = data.get('product_id')
        
        # Validate product_id
        if not product_id:
            return JsonResponse({'error': 'Product ID is required'}, status=400)
        
        try:
            product_id = int(product_id)
        except (ValueError, TypeError):
            return JsonResponse({'error': 'Invalid product ID'}, status=400)
        
        # Validate quantity
        quantity, error = validate_quantity(data.get('quantity', 1))
        if error:
            return JsonResponse({'error': error}, status=400)
        
        # Get product
        try:
            product = Product.objects.get(id=product_id, is_active=True)
        except Product.DoesNotExist:
            return JsonResponse({'error': 'Product not found'}, status=404)
        
        # Check stock
        if product.track_inventory and product.stock_quantity < quantity:
            return JsonResponse({
                'error': f'Only {product.stock_quantity} items available in stock'
            }, status=400)
        
        cart = request.session.get('cart', [])
        
        # Check if item already in cart
        existing_item = None
        for item in cart:
            if item.get('product_id') == str(product.id):
                existing_item = item
                break
        
        if existing_item:
            new_quantity = existing_item.get('quantity', 0) + quantity
            if product.track_inventory and product.stock_quantity < new_quantity:
                return JsonResponse({
                    'error': f'Only {product.stock_quantity} items available in stock'
                }, status=400)
            existing_item['quantity'] = new_quantity
        else:
            primary_image = product.primary_image
            cart.append({
                'product_id': str(product.id),
                'product_slug': product.slug,
                'product_name': product.name,
                'product_price': float(product.price),
                'product_image': primary_image.image.url if primary_image and primary_image.image else '',
                'quantity': quantity,
            })
        
        request.session['cart'] = cart
        request.session.modified = True
        
        cart_count = sum(item.get('quantity', 1) for item in cart)
        
        return JsonResponse({
            'success': True,
            'message': f'{product.name} added to cart',
            'cart_count': cart_count,
        })
    
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON data'}, status=400)
    except Exception as e:
        logger.error(f"Add to cart error: {e}", exc_info=True)
        return JsonResponse({'error': 'An error occurred'}, status=500)


@csrf_protect
def update_cart_item(request):
    """Update cart item quantity via AJAX."""
    if request.method != 'POST':
        return JsonResponse({'error': 'Invalid request method'}, status=405)
    
    try:
        data = json.loads(request.body)
        product_id = data.get('product_id')
        
        if not product_id:
            return JsonResponse({'error': 'Product ID is required'}, status=400)
        
        # Validate quantity
        quantity, error = validate_quantity(data.get('quantity', 1))
        if error:
            return JsonResponse({'error': error}, status=400)
        
        if quantity < 1:
            return remove_from_cart(request)
        
        cart = request.session.get('cart', [])
        
        # Get product
        try:
            product_id_int = int(product_id)
            product = Product.objects.get(id=product_id_int, is_active=True)
        except (ValueError, Product.DoesNotExist):
            return JsonResponse({'error': 'Product not found'}, status=404)
        
        # Check stock
        if product.track_inventory and product.stock_quantity < quantity:
            return JsonResponse({
                'error': f'Only {product.stock_quantity} items available in stock'
            }, status=400)
        
        # Update item
        item_total = 0
        item_found = False
        for item in cart:
            if item.get('product_id') == str(product_id):
                item['quantity'] = quantity
                item['total'] = item.get('product_price', 0) * quantity
                item_total = item['total']
                item_found = True
                break
        
        if not item_found:
            return JsonResponse({'error': 'Item not found in cart'}, status=404)
        
        request.session['cart'] = cart
        request.session.modified = True
        
        cart_total = sum(item.get('total', 0) for item in cart)
        cart_count = sum(item.get('quantity', 1) for item in cart)
        
        return JsonResponse({
            'success': True,
            'cart_total': cart_total,
            'cart_count': cart_count,
            'item_total': item_total,
        })
    
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON data'}, status=400)
    except Exception as e:
        logger.error(f"Update cart error: {e}", exc_info=True)
        return JsonResponse({'error': 'An error occurred'}, status=500)


@csrf_protect
def remove_from_cart(request):
    """Remove item from cart via AJAX."""
    if request.method != 'POST':
        return JsonResponse({'error': 'Invalid request method'}, status=405)
    
    try:
        data = json.loads(request.body)
        product_id = data.get('product_id')
        
        if not product_id:
            return JsonResponse({'error': 'Product ID is required'}, status=400)
        
        cart = request.session.get('cart', [])
        original_count = len(cart)
        cart = [item for item in cart if item.get('product_id') != str(product_id)]
        
        if len(cart) == original_count:
            return JsonResponse({'error': 'Item not found in cart'}, status=404)
        
        request.session['cart'] = cart
        request.session.modified = True
        
        cart_total = sum(item.get('total', 0) for item in cart)
        cart_count = sum(item.get('quantity', 1) for item in cart)
        
        return JsonResponse({
            'success': True,
            'message': 'Item removed from cart',
            'cart_total': cart_total,
            'cart_count': cart_count,
        })
    
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON data'}, status=400)
    except Exception as e:
        logger.error(f"Remove from cart error: {e}", exc_info=True)
        return JsonResponse({'error': 'An error occurred'}, status=500)


@csrf_protect
def clear_cart(request):
    """Clear all items from cart."""
    if request.method != 'POST':
        return JsonResponse({'error': 'Invalid request method'}, status=405)
    
    request.session['cart'] = []
    request.session.modified = True
    
    return JsonResponse({
        'success': True,
        'message': 'Cart cleared',
        'cart_count': 0,
    })
