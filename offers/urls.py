from django.urls import path
from offers.views import (
    ApplyCouponView, RemoveCouponView,
    ActiveOffersView,
    SubmitReviewView, MarkReviewHelpfulView, get_product_reviews
)

urlpatterns = [
    path('coupon/apply/', ApplyCouponView.as_view(), name='apply_coupon'),
    path('coupon/remove/', RemoveCouponView.as_view(), name='remove_coupon'),
    path('active/', ActiveOffersView.as_view(), name='active_offers'),
    path('review/submit/', SubmitReviewView.as_view(), name='submit_review'),
    path('review/helpful/', MarkReviewHelpfulView.as_view(), name='mark_review_helpful'),
    path('reviews/<str:product_id>/', get_product_reviews, name='product_reviews'),
]
