from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny
import logging

from products.models import Product

logger = logging.getLogger(__name__)


def validate_id(id_string):
    """Validate that ID is a valid integer."""
    if not id_string:
        return None
    try:
        return int(id_string)
    except (ValueError, TypeError):
        return None


class CartAPIView(APIView):
    """Get current cart."""
    permission_classes = [AllowAny]
    
    def get(self, request):
        cart = request.session.get('cart', [])
        items = []
        total = 0
        count = 0
        
        for item in cart:
            item_total = item.get('product_price', 0) * item.get('quantity', 1)
            items.append({
                'product_id': item.get('product_id'),
                'product_name': item.get('product_name'),
                'product_price': item.get('product_price'),
                'quantity': item.get('quantity'),
                'total': item_total,
            })
            total += item_total
            count += item.get('quantity', 1)
        
        return Response({'items': items, 'total': total, 'count': count})


class AddToCartAPIView(APIView):
    """Add product to cart."""
    permission_classes = [AllowAny]
    
    def post(self, request):
        product_id = validate_id(request.data.get('product_id'))
        if not product_id:
            return Response({'error': 'Invalid product ID'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            quantity = int(request.data.get('quantity', 1))
        except ValueError:
            return Response({'error': 'Invalid quantity'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            product = Product.objects.get(id=product_id, is_active=True)
        except Product.DoesNotExist:
            return Response({'error': 'Product not found'}, status=status.HTTP_404_NOT_FOUND)
        
        if product.track_inventory and product.stock_quantity < quantity:
            return Response({'error': f'Only {product.stock_quantity} items available'}, status=status.HTTP_400_BAD_REQUEST)
        
        cart = request.session.get('cart', [])
        
        for item in cart:
            if item.get('product_id') == str(product.id):
                item['quantity'] = item.get('quantity', 0) + quantity
                break
        else:
            primary_image = product.primary_image
            cart.append({
                'product_id': str(product.id),
                'product_name': product.name,
                'product_price': float(product.price),
                'product_image': primary_image.url if primary_image else '',
                'quantity': quantity,
            })
        
        request.session['cart'] = cart
        request.session.modified = True
        
        return Response({
            'success': True,
            'message': f'{product.name} added to cart',
            'cart_count': sum(item.get('quantity', 1) for item in cart),
        })


class UpdateCartItemAPIView(APIView):
    """Update cart item quantity."""
    permission_classes = [AllowAny]
    
    def post(self, request):
        product_id = request.data.get('product_id')
        try:
            quantity = int(request.data.get('quantity', 1))
        except ValueError:
            return Response({'error': 'Invalid quantity'}, status=status.HTTP_400_BAD_REQUEST)
        
        if quantity < 1:
            return Response({'error': 'Quantity must be at least 1'}, status=status.HTTP_400_BAD_REQUEST)
        
        cart = request.session.get('cart', [])
        
        for item in cart:
            if item.get('product_id') == str(product_id):
                item['quantity'] = quantity
                request.session['cart'] = cart
                request.session.modified = True
                return Response({
                    'success': True,
                    'message': 'Cart updated',
                    'cart_count': sum(item.get('quantity', 1) for item in cart),
                })
        
        return Response({'error': 'Item not found in cart'}, status=status.HTTP_404_NOT_FOUND)


class RemoveFromCartAPIView(APIView):
    """Remove item from cart."""
    permission_classes = [AllowAny]
    
    def post(self, request):
        product_id = request.data.get('product_id')
        cart = request.session.get('cart', [])
        
        original_len = len(cart)
        cart = [item for item in cart if item.get('product_id') != str(product_id)]
        
        if len(cart) == original_len:
            return Response({'error': 'Item not found in cart'}, status=status.HTTP_404_NOT_FOUND)
        
        request.session['cart'] = cart
        request.session.modified = True
        
        return Response({
            'success': True,
            'message': 'Item removed from cart',
            'cart_count': sum(item.get('quantity', 1) for item in cart),
        })


class ClearCartAPIView(APIView):
    """Clear entire cart."""
    permission_classes = [AllowAny]
    
    def post(self, request):
        request.session['cart'] = []
        request.session.modified = True
        return Response({
            'success': True,
            'message': 'Cart cleared',
            'cart_count': 0,
        })
