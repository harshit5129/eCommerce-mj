from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated, AllowAny

from products.models import Product
from mongoengine.errors import DoesNotExist, ValidationError


class CartAPIView(APIView):
    """
    Get current cart.
    """
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
                'product_image': item.get('product_image'),
                'quantity': item.get('quantity'),
                'total': item_total,
            })
            total += item_total
            count += item.get('quantity', 1)
        
        return Response({
            'items': items,
            'total': total,
            'count': count,
        })


class AddToCartAPIView(APIView):
    """
    Add product to cart.
    """
    permission_classes = [AllowAny]
    
    def post(self, request):
        product_id = request.data.get('product_id')
        quantity = int(request.data.get('quantity', 1))
        
        if not product_id:
            return Response(
                {'error': 'Product ID is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        product = Product.objects(id=product_id, is_active=True).first()
        if not product:
            return Response(
                {'error': 'Product not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        if product.track_inventory and product.stock_quantity < quantity:
            return Response(
                {'error': f'Only {product.stock_quantity} items available'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        cart = request.session.get('cart', [])
        
        existing_item = None
        for item in cart:
            if item.get('product_id') == str(product.id):
                existing_item = item
                break
        
        if existing_item:
            new_quantity = existing_item.get('quantity', 0) + quantity
            if product.track_inventory and product.stock_quantity < new_quantity:
                return Response(
                    {'error': f'Only {product.stock_quantity} items available'},
                    status=status.HTTP_400_BAD_REQUEST
                )
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
        
        return Response({
            'success': True,
            'message': f'{product.name} added to cart',
            'cart_count': cart_count,
        })


class UpdateCartItemAPIView(APIView):
    """
    Update cart item quantity.
    """
    permission_classes = [AllowAny]
    
    def post(self, request):
        product_id = request.data.get('product_id')
        quantity = int(request.data.get('quantity', 1))
        
        if quantity < 1:
            return Response(
                {'error': 'Quantity must be at least 1'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        product = Product.objects(id=product_id, is_active=True).first()
        if not product:
            return Response(
                {'error': 'Product not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        if product.track_inventory and product.stock_quantity < quantity:
            return Response(
                {'error': f'Only {product.stock_quantity} items available'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        cart = request.session.get('cart', [])
        
        for item in cart:
            if item.get('product_id') == product_id:
                item['quantity'] = quantity
                break
        
        request.session['cart'] = cart
        request.session.modified = True
        
        cart_total = sum(
            item.get('product_price', 0) * item.get('quantity', 1) 
            for item in cart
        )
        cart_count = sum(item.get('quantity', 1) for item in cart)
        
        return Response({
            'success': True,
            'cart_total': cart_total,
            'cart_count': cart_count,
        })


class RemoveFromCartAPIView(APIView):
    """
    Remove item from cart.
    """
    permission_classes = [AllowAny]
    
    def post(self, request):
        product_id = request.data.get('product_id')
        
        cart = request.session.get('cart', [])
        cart = [item for item in cart if item.get('product_id') != product_id]
        
        request.session['cart'] = cart
        request.session.modified = True
        
        cart_total = sum(
            item.get('product_price', 0) * item.get('quantity', 1) 
            for item in cart
        )
        cart_count = sum(item.get('quantity', 1) for item in cart)
        
        return Response({
            'success': True,
            'message': 'Item removed from cart',
            'cart_total': cart_total,
            'cart_count': cart_count,
        })


class ClearCartAPIView(APIView):
    """
    Clear all items from cart.
    """
    permission_classes = [AllowAny]
    
    def post(self, request):
        request.session['cart'] = []
        request.session.modified = True
        
        return Response({
            'success': True,
            'message': 'Cart cleared',
            'cart_count': 0,
        })
