from django.urls import path
from orders.api_views import (
    OrderListAPIView, OrderDetailAPIView, 
    CreateOrderAPIView, CancelOrderAPIView
)

urlpatterns = [
    path('', OrderListAPIView.as_view(), name='api_order_list'),
    path('create/', CreateOrderAPIView.as_view(), name='api_create_order'),
    path('cancel/', CancelOrderAPIView.as_view(), name='api_cancel_order'),
    path('<str:order_number>/', OrderDetailAPIView.as_view(), name='api_order_detail'),
]
