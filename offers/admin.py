from django.contrib import admin
from offers.models import Coupon, CouponUsage, LimitedOffer, ProductReview, ReviewSummary


class CouponUsageInline(admin.TabularInline):
    model = CouponUsage
    extra = 0
    readonly_fields = ['user_email', 'order_number', 'discount_amount', 'used_at']


@admin.register(Coupon)
class CouponAdmin(admin.ModelAdmin):
    list_display = ['code', 'discount_type', 'discount_value', 'is_active', 'used_count', 'valid_until']
    list_filter = ['is_active', 'discount_type', 'is_first_order_only']
    search_fields = ['code', 'description']
    list_editable = ['is_active']
    inlines = [CouponUsageInline]
    date_hierarchy = 'created_at'


@admin.register(CouponUsage)
class CouponUsageAdmin(admin.ModelAdmin):
    list_display = ['coupon', 'user_email', 'order_number', 'discount_amount', 'used_at']
    list_filter = ['used_at']
    search_fields = ['coupon__code', 'user_email', 'order_number']


@admin.register(LimitedOffer)
class LimitedOfferAdmin(admin.ModelAdmin):
    list_display = ['name', 'offer_type', 'discount_type', 'is_active', 'starts_at', 'ends_at']
    list_filter = ['is_active', 'offer_type', 'starts_at']
    search_fields = ['name', 'description']
    list_editable = ['is_active']
    date_hierarchy = 'starts_at'


@admin.register(ProductReview)
class ProductReviewAdmin(admin.ModelAdmin):
    list_display = ['product_id', 'user_name', 'rating', 'is_verified_purchase', 'is_approved', 'created_at']
    list_filter = ['rating', 'is_approved', 'is_verified_purchase', 'created_at']
    search_fields = ['product_name', 'user_name', 'review']
    list_editable = ['is_approved']
    date_hierarchy = 'created_at'


@admin.register(ReviewSummary)
class ReviewSummaryAdmin(admin.ModelAdmin):
    list_display = ['product_id', 'total_reviews', 'average_rating', 'updated_at']
    readonly_fields = ['product_id', 'total_reviews', 'average_rating', 'rating_distribution']
