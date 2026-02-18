from rest_framework import serializers


class CartItemSerializer(serializers.Serializer):
    product_id = serializers.CharField()
    product_name = serializers.CharField()
    product_price = serializers.FloatField()
    product_image = serializers.CharField(allow_null=True)
    quantity = serializers.IntegerField()
    total = serializers.FloatField()


class CartSerializer(serializers.Serializer):
    items = CartItemSerializer(many=True)
    total = serializers.FloatField()
    count = serializers.IntegerField()
