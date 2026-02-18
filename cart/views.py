from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.views import View
from django.http import JsonResponse
from products.models import Product
import json


class CartView(View):
    """Shopping cart page."""
    
    template_name = 'cart/cart.html'
    
    def get(self, request):
        cart_items = request.session.get('cart', [])
        
        for item in cart_items:
            item['total'] = item.get('product_price', 0) * item.get('quantity', 1)
        
        cart_total = sum(item.get('total', 0) for item in cart_items)
        
        context = {
            'cart_items': cart_items,
            'cart_total': cart_total,
        }
        return render(request, self.template_name, context)


def add_to_cart(request):
    """Add product to cart via AJAX."""
    if request.method != 'POST':
        return JsonResponse({'error': 'Invalid request method'}, status=405)
    
    try:
        data = json.loads(request.body)
        product_id = data.get('product_id')
        quantity = int(data.get('quantity', 1))
        
        product = get_object_or_404(Product, id=product_id, is_active=True)
        
        if product.track_inventory and product.stock_quantity < quantity:
            return JsonResponse({
                'error': f'Only {product.stock_quantity} items available in stock'
            }, status=400)
        
        cart = request.session.get('cart', [])
        
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
                'product_name': product.name,
                'product_price': product.price,
                'product_image': primary_image.url if primary_image else None,
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
    
    except Product.DoesNotExist:
        return JsonResponse({'error': 'Product not found'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


def update_cart_item(request):
    """Update cart item quantity via AJAX."""
    if request.method != 'POST':
        return JsonResponse({'error': 'Invalid request method'}, status=405)
    
    try:
        data = json.loads(request.body)
        product_id = data.get('product_id')
        quantity = int(data.get('quantity', 1))
        
        if quantity < 1:
            return remove_from_cart(request)
        
        cart = request.session.get('cart', [])
        
        product = Product.objects.get(id=product_id, is_active=True)
        if product.track_inventory and product.stock_quantity < quantity:
            return JsonResponse({
                'error': f'Only {product.stock_quantity} items available in stock'
            }, status=400)
        
        for item in cart:
            if item.get('product_id') == product_id:
                item['quantity'] = quantity
                item['total'] = item.get('product_price', 0) * quantity
                break
        
        request.session['cart'] = cart
        request.session.modified = True
        
        cart_total = sum(item.get('total', 0) for item in cart)
        cart_count = sum(item.get('quantity', 1) for item in cart)
        
        return JsonResponse({
            'success': True,
            'cart_total': cart_total,
            'cart_count': cart_count,
            'item_total': item.get('total', 0),
        })
    
    except Product.DoesNotExist:
        return JsonResponse({'error': 'Product not found'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


def remove_from_cart(request):
    """Remove item from cart via AJAX."""
    if request.method != 'POST':
        return JsonResponse({'error': 'Invalid request method'}, status=405)
    
    try:
        data = json.loads(request.body)
        product_id = data.get('product_id')
        
        cart = request.session.get('cart', [])
        cart = [item for item in cart if item.get('product_id') != product_id]
        
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
    
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


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
