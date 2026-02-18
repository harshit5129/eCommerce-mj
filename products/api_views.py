from rest_framework import generics, filters
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticatedOrReadOnly, IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend

from products.models import Product
from products.serializers import ProductListSerializer, ProductDetailSerializer
from mongoengine.errors import DoesNotExist, ValidationError


class ProductListAPIView(generics.ListAPIView):
    """
    List all products with filtering, search, and pagination.
    """
    serializer_class = ProductListSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['category__slug', 'is_featured', 'is_active']
    search_fields = ['name', 'description', 'tags', 'sku']
    ordering_fields = ['price', 'created_at', 'name']
    ordering = ['-created_at']
    
    def get_queryset(self):
        queryset = Product.objects(is_active=True)
        
        category = self.request.query_params.get('category')
        if category:
            queryset = queryset(category__slug=category)
        
        min_price = self.request.query_params.get('min_price')
        max_price = self.request.query_params.get('max_price')
        if min_price:
            queryset = queryset(price__gte=float(min_price))
        if max_price:
            queryset = queryset(price__lte=float(max_price))
        
        return queryset
    
    def get_serializer(self, *args, **kwargs):
        return super().get_serializer(*args, **kwargs)


class ProductDetailAPIView(generics.RetrieveAPIView):
    """
    Retrieve a single product by ID or slug.
    """
    serializer_class = ProductDetailSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]
    lookup_field = 'pk'
    
    def get_queryset(self):
        return Product.objects(is_active=True)
    
    def get_object(self):
        pk_or_slug = self.kwargs['pk']
        product = Product.objects(id=pk_or_slug, is_active=True).first()
        if product:
            return product
        product = Product.objects(slug=pk_or_slug, is_active=True).first()
        return product
    
    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        if instance is None:
            return Response(
                {'error': 'Product not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        serializer = self.get_serializer(instance)
        return Response(serializer.data)


class FeaturedProductsAPIView(generics.ListAPIView):
    """
    List featured products.
    """
    serializer_class = ProductListSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]
    
    def get_queryset(self):
        return Product.objects(is_featured=True, is_active=True)[:8]
