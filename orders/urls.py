from django.urls import path
from orders.views import (
    CheckoutView, OrderSuccessView, OrderHistoryView, 
    OrderDetailView, cancel_order
)

urlpatterns = [
    path('checkout/', CheckoutView.as_view(), name='checkout'),
    path('success/', OrderSuccessView.as_view(), name='order_success'),
    path('history/', OrderHistoryView.as_view(), name='order_history'),
    path('<str:order_number>/', OrderDetailView.as_view(), name='order_detail'),
    path('cancel/', cancel_order, name='cancel_order'),
]
