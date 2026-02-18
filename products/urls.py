from django.urls import path
from products.views import (
    HomeView, ProductListView, ProductDetailView,
    WishlistView, WishlistToggleView, WishlistRemoveView
)

urlpatterns = [
    path('', HomeView.as_view(), name='home'),
    path('products/', ProductListView.as_view(), name='product_list'),
    path('products/<slug:slug>/', ProductDetailView.as_view(), name='product_detail'),
    
    path('wishlist/', WishlistView.as_view(), name='wishlist'),
    path('wishlist/toggle/<str:product_id>/', WishlistToggleView.as_view(), name='wishlist_toggle'),
    path('wishlist/remove/<str:product_id>/', WishlistRemoveView.as_view(), name='wishlist_remove'),
]
