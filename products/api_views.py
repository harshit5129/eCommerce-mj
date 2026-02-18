from rest_framework import generics, filters
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticatedOrReadOnly, IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend

from products.models import Product
from products.serializers import ProductListSerializer, ProductDetailSerializer


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
        queryset = Product.objects.filter(is_active=True)
        
        category = self.request.query_params.get('category')
        if category:
            queryset = queryset.filter(category__slug=category)
        
        min_price = self.request.query_params.get('min_price')
        max_price = self.request.query_params.get('max_price')
        if min_price:
            try:
                queryset = queryset.filter(price__gte=float(min_price))
            except ValueError:
                pass
        if max_price:
            try:
                queryset = queryset.filter(price__lte=float(max_price))
            except ValueError:
                pass
        
        return queryset.select_related('category')


class ProductDetailAPIView(generics.RetrieveAPIView):
    """
    Retrieve a single product by ID or slug.
    """
    serializer_class = ProductDetailSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]
    lookup_field = 'pk'
    queryset = Product.objects.filter(is_active=True)
    
    def get_object(self):
        pk_or_slug = self.kwargs['pk']
        
        # Try to get by ID first
        try:
            pk = int(pk_or_slug)
            return Product.objects.get(id=pk, is_active=True)
        except (ValueError, Product.DoesNotExist):
            pass
        
        # Try to get by slug
        try:
            return Product.objects.get(slug=pk_or_slug, is_active=True)
        except Product.DoesNotExist:
            return None
    
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
        return Product.objects.filter(is_featured=True, is_active=True)[:8]
