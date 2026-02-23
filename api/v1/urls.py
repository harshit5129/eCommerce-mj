"""
E-Commerce API v1
This module contains all API endpoints for version 1.
"""

from django.urls import path, include

app_name = 'v1'

urlpatterns = [
    path('', include('products.api_urls')),
    path('auth/', include('users.api_urls')),
    path('cart/', include('cart.api_urls')),
    path('orders/', include('orders.api_urls')),
    path('offers/', include('offers.urls')),
]
