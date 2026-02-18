from rest_framework import serializers
from products.models import Product, Category, ProductImage


class CategorySerializer(serializers.Serializer):
    name = serializers.CharField()
    slug = serializers.CharField()


class ProductImageSerializer(serializers.Serializer):
    url = serializers.CharField()
    alt_text = serializers.CharField(allow_blank=True)
    is_primary = serializers.BooleanField()


class ProductListSerializer(serializers.Serializer):
    id = serializers.CharField(source='pk')
    name = serializers.CharField()
    slug = serializers.CharField()
    sku = serializers.CharField()
    price = serializers.FloatField()
    compare_price = serializers.FloatField(allow_null=True)
    discount_percentage = serializers.FloatField()
    category = CategorySerializer(allow_null=True)
    tags = serializers.ListField(child=serializers.CharField())
    primary_image = ProductImageSerializer(allow_null=True)
    stock_quantity = serializers.IntegerField()
    in_stock = serializers.BooleanField()
    is_featured = serializers.BooleanField()
    created_at = serializers.DateTimeField()


class ProductDetailSerializer(ProductListSerializer):
    description = serializers.CharField(allow_blank=True)
    short_description = serializers.CharField(allow_blank=True)
    images = ProductImageSerializer(many=True)
    track_inventory = serializers.BooleanField()
    allow_backorders = serializers.BooleanField()
    weight = serializers.FloatField(allow_null=True)
    updated_at = serializers.DateTimeField()
