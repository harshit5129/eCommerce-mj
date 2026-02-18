from datetime import datetime
import uuid
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated, AllowAny

from orders.models import Order, OrderItem, ShippingAddress
from orders.serializers import OrderSerializer, CreateOrderSerializer
from products.models import Product


class OrderListAPIView(APIView):
    """
    List user's orders.
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        user_id = str(request.user.id)
        orders = Order.objects(user_id=user_id).order_by('-created_at')
        
        return Response({
            'orders': [OrderSerializer(order).data for order in orders],
            'count': orders.count(),
        })


class OrderDetailAPIView(APIView):
    """
    Get order details.
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request, order_number):
        user_id = str(request.user.id)
        
        try:
            order = Order.objects.get(order_number=order_number, user_id=user_id)
            return Response(OrderSerializer(order).data)
        except Order.DoesNotExist:
            return Response(
                {'error': 'Order not found'},
                status=status.HTTP_404_NOT_FOUND
            )


class CreateOrderAPIView(APIView):
    """
    Create a new order.
    """
    permission_classes = [AllowAny]
    
    def post(self, request):
        cart = request.session.get('cart', [])
        
        if not cart:
            return Response(
                {'error': 'Cart is empty'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        serializer = CreateOrderSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        address_data = serializer.validated_data['shipping_address']
        
        cart_total = sum(
            item.get('product_price', 0) * item.get('quantity', 1) 
            for item in cart
        )
        shipping_cost = float(serializer.validated_data.get('shipping_cost', 9.99))
        tax = float(serializer.validated_data.get('tax', cart_total * 0.08))
        discount = float(serializer.validated_data.get('discount', 0))
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
        
        user_id = str(request.user.id) if hasattr(request.user, 'id') else 'guest'
        
        shipping_address = ShippingAddress(
            first_name=address_data.get('first_name'),
            last_name=address_data.get('last_name'),
            email=address_data.get('email'),
            phone=address_data.get('phone', ''),
            street=address_data.get('street'),
            city=address_data.get('city'),
            state=address_data.get('state'),
            postal_code=address_data.get('postal_code'),
            country=address_data.get('country', 'USA'),
        )
        
        order = Order(
            order_number=order_number,
            user_id=user_id,
            user_email=address_data.get('email'),
            items=order_items,
            subtotal=cart_total,
            shipping_cost=shipping_cost,
            tax=tax,
            discount=discount,
            total=total,
            shipping_address=shipping_address,
            payment_method=serializer.validated_data.get('payment_method', 'cash'),
            notes=serializer.validated_data.get('notes', ''),
        )
        order.save()
        
        request.session['cart'] = []
        request.session.modified = True
        
        return Response({
            'success': True,
            'order': OrderSerializer(order).data,
            'order_number': order_number,
        }, status=status.HTTP_201_CREATED)


class CancelOrderAPIView(APIView):
    """
    Cancel an order.
    """
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        order_number = request.data.get('order_number')
        
        if not order_number:
            return Response(
                {'error': 'Order number is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        user_id = str(request.user.id)
        
        try:
            order = Order.objects.get(order_number=order_number, user_id=user_id)
        except Order.DoesNotExist:
            return Response(
                {'error': 'Order not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        if not order.is_cancellable:
            return Response(
                {'error': 'Order cannot be cancelled'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        for item in order.items:
            product = Product.objects(id=item.product_id).first()
            if product and product.track_inventory:
                product.stock_quantity += item.quantity
                product.save()
        
        order.order_status = 'cancelled'
        order.cancelled_at = datetime.utcnow()
        order.save()
        
        return Response({
            'success': True,
            'message': 'Order cancelled successfully',
        })
