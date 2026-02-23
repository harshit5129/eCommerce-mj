from rest_framework import generics, filters
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticatedOrReadOnly, IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
import logging

from products.models import Product
from products.serializers import ProductListSerializer, ProductDetailSerializer

logger = logging.getLogger(__name__)


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
        try:
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
        except Exception as e:
            logger.error(f"Product list query failed: {e}", exc_info=True)
            return Product.objects.none()
    
    def list(self, request, *args, **kwargs):
        try:
            queryset = self.filter_queryset(self.get_queryset())
            page = self.paginate_queryset(queryset)
            if page is not None:
                serializer = self.get_serializer(page, many=True)
                return self.get_paginated_response({
                    'success': True,
                    'products': serializer.data
                })
            serializer = self.get_serializer(queryset, many=True)
            return Response({
                'success': True,
                'products': serializer.data
            })
        except Exception as e:
            logger.error(f"Product list failed: {e}", exc_info=True)
            return Response({
                'success': False,
                'error': {
                    'type': 'server_error',
                    'message': 'Failed to retrieve products',
                    'details': None
                },
                'status_code': status.HTTP_500_INTERNAL_SERVER_ERROR
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


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
        
        try:
            pk = int(pk_or_slug)
            try:
                return Product.objects.get(id=pk, is_active=True)
            except Product.DoesNotExist:
                pass
        except (ValueError, TypeError):
            pass
        
        try:
            return Product.objects.get(slug=pk_or_slug, is_active=True)
        except Product.DoesNotExist:
            return None
    
    def retrieve(self, request, *args, **kwargs):
        try:
            instance = self.get_object()
            if instance is None:
                return Response({
                    'success': False,
                    'error': {
                        'type': 'not_found',
                        'message': 'Product not found',
                        'details': None
                    },
                    'status_code': status.HTTP_404_NOT_FOUND
                }, status=status.HTTP_404_NOT_FOUND)
            serializer = self.get_serializer(instance)
            return Response({
                'success': True,
                'product': serializer.data
            })
        except Exception as e:
            logger.error(f"Product detail failed: {e}", exc_info=True)
            return Response({
                'success': False,
                'error': {
                    'type': 'server_error',
                    'message': 'Failed to retrieve product',
                    'details': None
                },
                'status_code': status.HTTP_500_INTERNAL_SERVER_ERROR
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class FeaturedProductsAPIView(generics.ListAPIView):
    """
    List featured products.
    """
    serializer_class = ProductListSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]
    
    def get_queryset(self):
        return Product.objects.filter(is_featured=True, is_active=True)[:8]
    
    def list(self, request, *args, **kwargs):
        try:
            queryset = self.get_queryset()
            serializer = self.get_serializer(queryset, many=True)
            return Response({
                'success': True,
                'products': serializer.data
            })
        except Exception as e:
            logger.error(f"Featured products failed: {e}", exc_info=True)
            return Response({
                'success': False,
                'error': {
                    'type': 'server_error',
                    'message': 'Failed to retrieve featured products',
                    'details': None
                },
                'status_code': status.HTTP_500_INTERNAL_SERVER_ERROR
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
