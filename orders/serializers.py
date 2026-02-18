from rest_framework import serializers
from orders.models import Order, OrderItem


class OrderItemSerializer(serializers.Serializer):
    product_id = serializers.CharField()
    product_name = serializers.CharField()
    product_sku = serializers.CharField(allow_blank=True)
    product_image = serializers.CharField(allow_null=True)
    price = serializers.FloatField()
    quantity = serializers.IntegerField()
    total = serializers.FloatField()


class ShippingAddressSerializer(serializers.Serializer):
    first_name = serializers.CharField()
    last_name = serializers.CharField()
    email = serializers.EmailField()
    phone = serializers.CharField(allow_blank=True)
    street = serializers.CharField()
    city = serializers.CharField()
    state = serializers.CharField()
    postal_code = serializers.CharField()
    country = serializers.CharField()


class OrderSerializer(serializers.Serializer):
    id = serializers.CharField()
    order_number = serializers.CharField()
    user_id = serializers.CharField()
    user_email = serializers.EmailField()
    items = OrderItemSerializer(many=True)
    item_count = serializers.IntegerField()
    subtotal = serializers.FloatField()
    shipping_cost = serializers.FloatField()
    tax = serializers.FloatField()
    discount = serializers.FloatField()
    total = serializers.FloatField()
    shipping_address = ShippingAddressSerializer()
    order_status = serializers.CharField()
    payment_status = serializers.CharField()
    payment_method = serializers.CharField()
    notes = serializers.CharField(allow_blank=True)
    tracking_number = serializers.CharField(allow_blank=True)
    is_cancellable = serializers.BooleanField()
    created_at = serializers.DateTimeField()


class CreateOrderSerializer(serializers.Serializer):
    shipping_address = ShippingAddressSerializer()
    payment_method = serializers.CharField()
    notes = serializers.CharField(allow_blank=True, required=False)
