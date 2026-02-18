from django.urls import path
from cart.api_views import (
    CartAPIView, AddToCartAPIView, UpdateCartItemAPIView,
    RemoveFromCartAPIView, ClearCartAPIView
)

urlpatterns = [
    path('', CartAPIView.as_view(), name='api_cart'),
    path('add/', AddToCartAPIView.as_view(), name='api_add_to_cart'),
    path('update/', UpdateCartItemAPIView.as_view(), name='api_update_cart'),
    path('remove/', RemoveFromCartAPIView.as_view(), name='api_remove_from_cart'),
    path('clear/', ClearCartAPIView.as_view(), name='api_clear_cart'),
]
