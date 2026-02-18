from django.urls import path
from orders.views import (
    CheckoutView, OrderSuccessView, OrderHistoryView, 
    OrderDetailView, cancel_order
)
from orders.razorpay_views import (
    CreateRazorpayOrderView, VerifyRazorpayPaymentView,
    RazorpayWebhookView, PaymentStatusView
)

urlpatterns = [
    path('checkout/', CheckoutView.as_view(), name='checkout'),
    path('success/', OrderSuccessView.as_view(), name='order_success'),
    path('cancel/', cancel_order, name='cancel_order'),
    path('history/', OrderHistoryView.as_view(), name='order_history'),
    path('payment/create/', CreateRazorpayOrderView.as_view(), name='create_payment'),
    path('payment/verify/', VerifyRazorpayPaymentView.as_view(), name='verify_payment'),
    path('payment/status/', PaymentStatusView.as_view(), name='payment_status'),
    path('webhook/razorpay/', RazorpayWebhookView.as_view(), name='razorpay_webhook'),
    path('<str:order_number>/', OrderDetailView.as_view(), name='order_detail'),
]
