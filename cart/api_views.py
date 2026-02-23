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


def make_error_response(message, error_type='error', details=None, status_code=status.HTTP_400_BAD_REQUEST):
    """Create a consistent error response."""
    return Response({
        'success': False,
        'error': {
            'type': error_type,
            'message': message,
            'details': details
        },
        'status_code': status_code
    }, status=status_code)


class CartAPIView(APIView):
    """Get current cart."""
    permission_classes = [AllowAny]
    
    def get(self, request):
        try:
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
            
            return Response({
                'success': True,
                'items': items,
                'total': total,
                'count': count
            })
        except Exception as e:
            logger.error(f"Cart retrieve failed: {e}", exc_info=True)
            return make_error_response(
                'Failed to retrieve cart',
                'server_error',
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class AddToCartAPIView(APIView):
    """Add product to cart."""
    permission_classes = [AllowAny]
    
    def post(self, request):
        try:
            product_id = validate_id(request.data.get('product_id'))
            if not product_id:
                return make_error_response('Invalid product ID', 'validation_error')
            
            try:
                quantity = int(request.data.get('quantity', 1))
                if not 1 <= quantity <= 999:
                    return make_error_response('Quantity must be between 1 and 999', 'validation_error')
            except ValueError:
                return make_error_response('Invalid quantity', 'validation_error')
            
            try:
                product = Product.objects.get(id=product_id, is_active=True)
            except Product.DoesNotExist:
                return make_error_response('Product not found', 'not_found', status_code=status.HTTP_404_NOT_FOUND)
            
            if product.track_inventory and product.stock_quantity < quantity:
                return make_error_response(
                    f'Only {product.stock_quantity} items available',
                    'validation_error'
                )
            
            cart = request.session.get('cart', [])
            
            for item in cart:
                if item.get('product_id') == str(product.id):
                    new_qty = item.get('quantity', 0) + quantity
                    if product.track_inventory and product.stock_quantity < new_qty:
                        return make_error_response(
                            f'Only {product.stock_quantity} items available',
                            'validation_error'
                        )
                    item['quantity'] = new_qty
                    break
            else:
                primary_image = product.primary_image
                cart.append({
                    'product_id': str(product.id),
                    'product_name': product.name[:255],
                    'product_price': float(product.price),
                    'product_image': primary_image.image.url if primary_image and primary_image.image else '',
                    'quantity': quantity,
                })
            
            request.session['cart'] = cart
            request.session.modified = True
            
            logger.info(f"Product {product_id} added to cart by {request.user.email if request.user.is_authenticated else 'guest'}")
            
            return Response({
                'success': True,
                'message': f'{product.name} added to cart',
                'cart_count': sum(item.get('quantity', 1) for item in cart),
            })
        except Exception as e:
            logger.error(f"Add to cart failed: {e}", exc_info=True)
            return make_error_response(
                'Failed to add item to cart',
                'server_error',
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class UpdateCartItemAPIView(APIView):
    """Update cart item quantity."""
    permission_classes = [AllowAny]
    
    def post(self, request):
        try:
            product_id = request.data.get('product_id')
            if not product_id:
                return make_error_response('Product ID is required', 'validation_error')
            
            try:
                quantity = int(request.data.get('quantity', 1))
                if not 1 <= quantity <= 999:
                    return make_error_response('Quantity must be between 1 and 999', 'validation_error')
            except ValueError:
                return make_error_response('Invalid quantity', 'validation_error')
            
            cart = request.session.get('cart', [])
            
            for item in cart:
                if item.get('product_id') == str(product_id):
                    product_id_int = validate_id(product_id)
                    if product_id_int:
                        try:
                            product = Product.objects.get(id=product_id_int, is_active=True)
                            if product.track_inventory and product.stock_quantity < quantity:
                                return make_error_response(
                                    f'Only {product.stock_quantity} items available',
                                    'validation_error'
                                )
                        except Product.DoesNotExist:
                            pass
                    
                    item['quantity'] = quantity
                    request.session['cart'] = cart
                    request.session.modified = True
                    
                    return Response({
                        'success': True,
                        'message': 'Cart updated',
                        'cart_count': sum(item.get('quantity', 1) for item in cart),
                    })
            
            return make_error_response('Item not found in cart', 'not_found', status_code=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error(f"Update cart failed: {e}", exc_info=True)
            return make_error_response(
                'Failed to update cart',
                'server_error',
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class RemoveFromCartAPIView(APIView):
    """Remove item from cart."""
    permission_classes = [AllowAny]
    
    def post(self, request):
        try:
            product_id = request.data.get('product_id')
            if not product_id:
                return make_error_response('Product ID is required', 'validation_error')
            
            cart = request.session.get('cart', [])
            
            original_len = len(cart)
            cart = [item for item in cart if item.get('product_id') != str(product_id)]
            
            if len(cart) == original_len:
                return make_error_response('Item not found in cart', 'not_found', status_code=status.HTTP_404_NOT_FOUND)
            
            request.session['cart'] = cart
            request.session.modified = True
            
            return Response({
                'success': True,
                'message': 'Item removed from cart',
                'cart_count': sum(item.get('quantity', 1) for item in cart),
            })
        except Exception as e:
            logger.error(f"Remove from cart failed: {e}", exc_info=True)
            return make_error_response(
                'Failed to remove item from cart',
                'server_error',
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class ClearCartAPIView(APIView):
    """Clear entire cart."""
    permission_classes = [AllowAny]
    
    def post(self, request):
        try:
            request.session['cart'] = []
            request.session.modified = True
            return Response({
                'success': True,
                'message': 'Cart cleared',
                'cart_count': 0,
            })
        except Exception as e:
            logger.error(f"Clear cart failed: {e}", exc_info=True)
            return make_error_response(
                'Failed to clear cart',
                'server_error',
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
