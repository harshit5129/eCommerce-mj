from django.urls import path
from products.api_views import ProductListAPIView, ProductDetailAPIView, FeaturedProductsAPIView

urlpatterns = [
    path('products/', ProductListAPIView.as_view(), name='api_product_list'),
    path('products/<str:pk>/', ProductDetailAPIView.as_view(), name='api_product_detail'),
    path('products/featured/', FeaturedProductsAPIView.as_view(), name='api_featured_products'),
]
