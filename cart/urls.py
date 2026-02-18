from django.urls import path
from cart.views import CartView, add_to_cart, update_cart_item, remove_from_cart, clear_cart

urlpatterns = [
    path('', CartView.as_view(), name='cart'),
    path('add/', add_to_cart, name='add_to_cart'),
    path('update/', update_cart_item, name='update_cart_item'),
    path('remove/', remove_from_cart, name='remove_from_cart'),
    path('clear/', clear_cart, name='clear_cart'),
]
