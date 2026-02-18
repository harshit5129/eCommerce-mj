from django.urls import path
from admin_views import (
    AdminDashboardView,
    AdminUserListView, AdminUserEditView, AdminUserDeleteView,
    AdminProductListView, AdminProductCreateView, AdminProductEditView, AdminProductDeleteView,
    AdminOrderListView, AdminOrderDetailView, AdminOrderUpdateView
)

urlpatterns = [
    path('', AdminDashboardView.as_view(), name='admin_dashboard'),
    
    # User management
    path('users/', AdminUserListView.as_view(), name='admin_users'),
    path('users/edit/<str:user_id>/', AdminUserEditView.as_view(), name='admin_user_edit'),
    path('users/delete/<str:user_id>/', AdminUserDeleteView.as_view(), name='admin_user_delete'),
    
    # Product management
    path('products/', AdminProductListView.as_view(), name='admin_products'),
    path('products/create/', AdminProductCreateView.as_view(), name='admin_product_create'),
    path('products/edit/<str:product_id>/', AdminProductEditView.as_view(), name='admin_product_edit'),
    path('products/delete/<str:product_id>/', AdminProductDeleteView.as_view(), name='admin_product_delete'),
    
    # Order management
    path('orders/', AdminOrderListView.as_view(), name='admin_orders'),
    path('orders/<str:order_number>/', AdminOrderDetailView.as_view(), name='admin_order_detail'),
    path('orders/update/<str:order_number>/', AdminOrderUpdateView.as_view(), name='admin_order_update'),
]
