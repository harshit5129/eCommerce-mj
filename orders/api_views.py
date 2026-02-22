from datetime import datetime
import uuid
from django.utils import timezone
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.pagination import PageNumberPagination
from django.db import transaction
from django.db.models import F

from orders.models import Order, OrderItem
from orders.serializers import OrderSerializer, CreateOrderSerializer
from products.models import Product


class OrderPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size = 50


class OrderListAPIView(APIView):
    """
    List user's orders with pagination.
    """
    permission_classes = [IsAuthenticated]
    pagination_class = OrderPagination
    
    def get(self, request):
        user_id = str(request.user.id)
        orders = Order.objects.filter(user_id=user_id).order_by('-created_at')
        
        paginator = self.pagination_class()
        page = paginator.paginate_queryset(orders, request)
        
        if page is not None:
            return paginator.get_paginated_response([
                OrderSerializer(order).data for order in page
            ])
        
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
        except Order.DoesNotExist:
            return Response(
                {'error': 'Order not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        return Response(OrderSerializer(order).data)


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
        
        # Validate cart items and get actual prices from database
        validated_items = []
        cart_total = 0
        
        for item in cart:
            try:
                product_id = int(item.get('product_id'))
                quantity = int(item.get('quantity', 1))
                
                if quantity < 1:
                    continue
                
                # Fetch actual product price from database to prevent price manipulation
                try:
                    product = Product.objects.get(id=product_id, status='active')
                except Product.DoesNotExist:
                    return Response(
                        {'error': f'Product {product_id} not found or unavailable'},
                        status=status.HTTP_400_BAD_REQUEST
                    )
                
                # Check inventory if tracking is enabled
                if product.track_inventory and product.stock_quantity < quantity:
                    return Response(
                        {'error': f'Insufficient stock for {product.name}'},
                        status=status.HTTP_400_BAD_REQUEST
                    )
                
                actual_price = float(product.sale_price if product.sale_price else product.price)
                item_total = actual_price * quantity
                cart_total += item_total
                
                validated_items.append({
                    'product_id': product_id,
                    'product_name': product.name,
                    'product_image': product.primary_image.url if product.primary_image else '',
                    'price': actual_price,
                    'quantity': quantity,
                })
                
            except (ValueError, TypeError) as e:
                return Response(
                    {'error': f'Invalid cart item data: {str(e)}'},
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        if not validated_items:
            return Response(
                {'error': 'No valid items in cart'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Calculate shipping and tax
        shipping_cost = 99.0 if cart_total < 4000 else 0.0
        tax = round(cart_total * 0.18, 2)
        discount = float(serializer.validated_data.get('discount', 0))
        total = cart_total + shipping_cost + tax - discount
        
        order_number = f"ORD-{timezone.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}"
        user_id = str(request.user.id) if hasattr(request.user, 'id') and request.user.is_authenticated else 'guest'
        
        # Validate payment method
        payment_method = serializer.validated_data.get('payment_method', 'cod')
        if payment_method not in ['razorpay', 'cod']:
            payment_method = 'cod'
        
        with transaction.atomic():
            # Create order
            order = Order.objects.create(
                order_number=order_number,
                user_id=user_id,
                user_email=address_data.get('email'),
                subtotal=cart_total,
                shipping_cost=shipping_cost,
                tax=tax,
                discount=discount,
                total=total,
                shipping_address={
                    'first_name': address_data.get('first_name'),
                    'last_name': address_data.get('last_name'),
                    'email': address_data.get('email'),
                    'phone': address_data.get('phone', ''),
                    'street': address_data.get('street'),
                    'city': address_data.get('city'),
                    'state': address_data.get('state'),
                    'postal_code': address_data.get('postal_code'),
                    'country': address_data.get('country', 'USA'),
                },
                payment_method=payment_method,
                notes=serializer.validated_data.get('notes', ''),
            )
            
            # Create order items and deduct inventory
            for item in validated_items:
                OrderItem.objects.create(
                    order=order,
                    product_id=item['product_id'],
                    product_name=item['product_name'],
                    product_image=item['product_image'],
                    price=item['price'],
                    quantity=item['quantity'],
                )
                
                # Deduct inventory atomically
                Product.objects.filter(id=item['product_id'], track_inventory=True).update(
                    stock_quantity=F('stock_quantity') - item['quantity']
                )
        
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
        
        with transaction.atomic():
            # Restore inventory
            for item in order.items.all():
                Product.objects.filter(id=item.product_id, track_inventory=True).update(
                    stock_quantity=F('stock_quantity') + item.quantity
                )
            
            order.order_status = 'cancelled'
            order.cancelled_at = timezone.now()
            order.save()
        
        return Response({
            'success': True,
            'message': 'Order cancelled successfully',
        })
