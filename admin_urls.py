from django.urls import path
from admin_views import (
    AdminDashboardView,
    AdminUserListView, AdminUserCreateView, AdminUserEditView, AdminUserDeleteView,
    AdminProductListView, AdminProductCreateView, AdminProductEditView, AdminProductDeleteView, AdminProductStatusUpdateView,
    AdminOrderListView, AdminOrderDetailView, AdminOrderUpdateView,
    AdminCouponListView, AdminCouponCreateView, AdminCouponEditView, AdminCouponDeleteView,
    AdminOfferListView, AdminOfferCreateView, AdminOfferEditView, AdminOfferDeleteView,
    AdminReviewListView, AdminReviewApproveView
)
from analytics.views import AnalyticsDashboardView

urlpatterns = [
    path('', AdminDashboardView.as_view(), name='admin_dashboard'),
    
    path('users/', AdminUserListView.as_view(), name='admin_users'),
    path('users/create/', AdminUserCreateView.as_view(), name='admin_user_create'),
    path('users/edit/<str:user_id>/', AdminUserEditView.as_view(), name='admin_user_edit'),
    path('users/delete/<str:user_id>/', AdminUserDeleteView.as_view(), name='admin_user_delete'),
    
    path('products/', AdminProductListView.as_view(), name='admin_products'),
    path('products/create/', AdminProductCreateView.as_view(), name='admin_product_create'),
    path('products/edit/<str:product_id>/', AdminProductEditView.as_view(), name='admin_product_edit'),
    path('products/delete/<str:product_id>/', AdminProductDeleteView.as_view(), name='admin_product_delete'),
    path('products/status/<str:product_id>/', AdminProductStatusUpdateView.as_view(), name='admin_product_status'),
    
    path('orders/', AdminOrderListView.as_view(), name='admin_orders'),
    path('orders/<str:order_number>/', AdminOrderDetailView.as_view(), name='admin_order_detail'),
    path('orders/update/<str:order_number>/', AdminOrderUpdateView.as_view(), name='admin_order_update'),
    
    path('analytics/', AnalyticsDashboardView.as_view(), name='admin_analytics'),
    
    path('coupons/', AdminCouponListView.as_view(), name='admin_coupons'),
    path('coupons/create/', AdminCouponCreateView.as_view(), name='admin_coupon_create'),
    path('coupons/edit/<str:coupon_id>/', AdminCouponEditView.as_view(), name='admin_coupon_edit'),
    path('coupons/delete/<str:coupon_id>/', AdminCouponDeleteView.as_view(), name='admin_coupon_delete'),
    
    path('offers/', AdminOfferListView.as_view(), name='admin_offers'),
    path('offers/create/', AdminOfferCreateView.as_view(), name='admin_offer_create'),
    path('offers/edit/<str:offer_id>/', AdminOfferEditView.as_view(), name='admin_offer_edit'),
    path('offers/delete/<str:offer_id>/', AdminOfferDeleteView.as_view(), name='admin_offer_delete'),
    
    path('reviews/', AdminReviewListView.as_view(), name='admin_reviews'),
    path('reviews/approve/<str:review_id>/', AdminReviewApproveView.as_view(), name='admin_review_approve'),
]
