from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
import json


class Coupon(models.Model):
    """Coupon/Discount code model - PostgreSQL version."""
    
    DISCOUNT_TYPE_CHOICES = [
        ('percentage', 'Percentage'),
        ('fixed', 'Fixed Amount'),
    ]
    
    code = models.CharField(max_length=50, unique=True, db_index=True)
    description = models.CharField(max_length=200, blank=True)
    
    discount_type = models.CharField(
        max_length=20, 
        choices=DISCOUNT_TYPE_CHOICES, 
        default='percentage'
    )
    discount_value = models.DecimalField(
        max_digits=10, 
        decimal_places=2,
        validators=[MinValueValidator(0)]
    )
    
    min_order_value = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        default=0,
        validators=[MinValueValidator(0)]
    )
    max_discount = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        default=0,
        validators=[MinValueValidator(0)]
    )
    
    usage_limit = models.PositiveIntegerField(default=0)
    used_count = models.PositiveIntegerField(default=0)
    per_user_limit = models.PositiveIntegerField(default=1)
    
    valid_from = models.DateTimeField(default=timezone.now)
    valid_until = models.DateTimeField()
    
    is_active = models.BooleanField(default=True)
    is_first_order_only = models.BooleanField(default=False)
    
    applicable_categories = models.JSONField(default=list, blank=True)
    applicable_products = models.JSONField(default=list, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'coupons'
        indexes = [
            models.Index(fields=['code']),
            models.Index(fields=['is_active']),
            models.Index(fields=['valid_until']),
        ]
        ordering = ['-created_at']
        constraints = [
            models.CheckConstraint(
                check=models.Q(discount_value__gte=0),
                name='coupon_discount_value_non_negative'
            ),
            models.CheckConstraint(
                check=models.Q(min_order_value__gte=0),
                name='coupon_min_order_value_non_negative'
            ),
            models.CheckConstraint(
                check=models.Q(max_discount__gte=0),
                name='coupon_max_discount_non_negative'
            ),
        ]
    
    def __str__(self):
        return self.code
    
    @property
    def is_valid(self):
        """Check if coupon is currently valid."""
        now = timezone.now()
        if not self.is_active:
            return False
        if self.valid_from and self.valid_from > now:
            return False
        if self.valid_until and self.valid_until < now:
            return False
        if self.usage_limit > 0 and self.used_count >= self.usage_limit:
            return False
        return True
    
    def calculate_discount(self, cart_total):
        """Calculate discount amount for given cart total."""
        if cart_total < float(self.min_order_value):
            return 0
        
        if self.discount_type == 'percentage':
            discount = (float(self.discount_value) / 100) * cart_total
            if self.max_discount > 0:
                discount = min(discount, float(self.max_discount))
        else:
            discount = float(self.discount_value)
        
        return round(min(discount, cart_total), 2)
    
    def can_use(self, user_email):
        """Check if user can use this coupon."""
        if not self.is_valid:
            return False, "Coupon is not valid"
        
        if self.is_first_order_only and user_email:
            # Check if user has any orders
            from orders.models import Order
            existing_orders = Order.objects.filter(user_email=user_email).exists()
            if existing_orders:
                return False, "This coupon is only for first-time customers"
        
        # Check per-user usage limit
        if self.per_user_limit > 0 and user_email:
            usage_count = CouponUsage.objects.filter(
                coupon=self, 
                user_email=user_email
            ).count()
            if usage_count >= self.per_user_limit:
                return False, f"You have reached the usage limit for this coupon ({self.per_user_limit}x)"
        
        return True, "Valid"


class CouponUsage(models.Model):
    """Track coupon usage per user - PostgreSQL version."""
    
    coupon = models.ForeignKey(
        Coupon, 
        on_delete=models.CASCADE,
        related_name='usages'
    )
    user_email = models.EmailField()
    order_number = models.CharField(max_length=50)
    discount_amount = models.DecimalField(max_digits=10, decimal_places=2)
    used_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'coupon_usage'
        indexes = [
            models.Index(fields=['coupon', 'user_email']),
            models.Index(fields=['order_number']),
            models.Index(fields=['user_email', 'used_at']),
        ]
        ordering = ['-used_at']
        constraints = [
            models.CheckConstraint(
                check=models.Q(discount_amount__gte=0),
                name='coupon_usage_discount_non_negative'
            ),
        ]
    
    def __str__(self):
        return f"{self.coupon.code} used by {self.user_email}"


class LimitedOffer(models.Model):
    """Limited time flash sale offer - PostgreSQL version."""
    
    OFFER_TYPE_CHOICES = [
        ('flash_sale', 'Flash Sale'),
        ('deal_of_day', 'Deal of the Day'),
        ('weekend_special', 'Weekend Special'),
        ('clearance', 'Clearance'),
    ]
    
    name = models.CharField(max_length=100)
    slug = models.SlugField(max_length=100, unique=True, db_index=True)
    description = models.TextField(blank=True)
    offer_type = models.CharField(
        max_length=20,
        choices=OFFER_TYPE_CHOICES,
        default='flash_sale'
    )
    
    product_ids = models.JSONField(default=list, blank=True)
    category_ids = models.JSONField(default=list, blank=True)
    
    discount_type = models.CharField(
        max_length=20,
        choices=[('percentage', 'Percentage'), ('fixed', 'Fixed')],
        default='percentage'
    )
    discount_value = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0)]
    )
    
    original_prices = models.JSONField(default=dict, blank=True)
    
    starts_at = models.DateTimeField()
    ends_at = models.DateTimeField()
    
    banner_image = models.URLField(max_length=500, blank=True)
    banner_text = models.CharField(max_length=100, blank=True)
    banner_color = models.CharField(max_length=20, default='red')
    
    is_active = models.BooleanField(default=True)
    show_countdown = models.BooleanField(default=True)
    show_banner = models.BooleanField(default=True)
    
    max_items = models.PositiveIntegerField(default=0)
    items_sold = models.PositiveIntegerField(default=0)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'limited_offers'
        indexes = [
            models.Index(fields=['slug']),
            models.Index(fields=['is_active']),
            models.Index(fields=['starts_at', 'ends_at']),
            models.Index(fields=['is_active', 'starts_at', 'ends_at']),
        ]
        ordering = ['-created_at']
        constraints = [
            models.CheckConstraint(
                check=models.Q(discount_value__gte=0),
                name='limited_offer_discount_non_negative'
            ),
        ]
    
    def __str__(self):
        return self.name
    
    @property
    def is_live(self):
        """Check if offer is currently live."""
        now = timezone.now()
        return (
            self.is_active and
            self.starts_at <= now and
            self.ends_at >= now
        )
    
    @property
    def is_upcoming(self):
        """Check if offer is upcoming."""
        now = timezone.now()
        return self.is_active and self.starts_at > now
    
    @property
    def time_remaining(self):
        """Calculate time remaining for live offer."""
        if not self.is_live:
            return None
        
        remaining = self.ends_at - timezone.now()
        total_seconds = int(remaining.total_seconds())
        
        if total_seconds <= 0:
            return {'days': 0, 'hours': 0, 'minutes': 0, 'seconds': 0}
        
        return {
            'days': total_seconds // 86400,
            'hours': (total_seconds % 86400) // 3600,
            'minutes': (total_seconds % 3600) // 60,
            'seconds': total_seconds % 60
        }
    
    def get_discounted_price(self, original_price, product_id=None):
        """Calculate discounted price."""
        if self.discount_type == 'percentage':
            return original_price * (1 - float(self.discount_value) / 100)
        return max(0, original_price - float(self.discount_value))


class ProductReview(models.Model):
    """Product review and rating model - PostgreSQL version."""
    
    product_id = models.IntegerField(db_index=True)
    user_email = models.EmailField(db_index=True)
    user_name = models.CharField(max_length=100)
    
    rating = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)]
    )
    title = models.CharField(max_length=100, blank=True)
    review = models.TextField(blank=True)
    images = models.JSONField(default=list, blank=True)
    videos = models.JSONField(default=list, blank=True)
    
    is_verified_purchase = models.BooleanField(default=False)
    order_number = models.CharField(max_length=50, blank=True)
    
    helpful_count = models.PositiveIntegerField(default=0)
    helpful_users = models.JSONField(default=list, blank=True)
    
    is_approved = models.BooleanField(default=True)
    admin_response = models.TextField(blank=True)
    
    pros = models.JSONField(default=list, blank=True)
    cons = models.JSONField(default=list, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'product_reviews'
        indexes = [
            models.Index(fields=['product_id']),
            models.Index(fields=['user_email']),
            models.Index(fields=['rating']),
            models.Index(fields=['created_at']),
            models.Index(fields=['is_approved']),
        ]
        ordering = ['-helpful_count', '-created_at']
        constraints = [
            models.CheckConstraint(
                check=models.Q(rating__gte=1, rating__lte=5),
                name='product_review_rating_range'
            ),
        ]
    
    def __str__(self):
        return f"Review by {self.user_name} - {self.rating} stars"
    
    @property
    def stars_display(self):
        """Return star display ranges."""
        filled = self.rating
        empty = 5 - self.rating
        return {'filled': range(filled), 'empty': range(empty)}
    
    def mark_helpful(self, user_email):
        """Mark review as helpful by a user."""
        if user_email not in self.helpful_users:
            self.helpful_users.append(user_email)
            self.helpful_count += 1
            self.save(update_fields=['helpful_users', 'helpful_count'])
            return True
        return False


class ReviewSummary(models.Model):
    """Summary of product reviews - PostgreSQL version."""
    
    product_id = models.IntegerField(unique=True, db_index=True)
    total_reviews = models.PositiveIntegerField(default=0)
    average_rating = models.DecimalField(max_digits=3, decimal_places=2, default=0)
    rating_distribution = models.JSONField(default=dict)
    
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'review_summaries'
    
    def update_from_reviews(self):
        """Update summary from all reviews for this product."""
        reviews = ProductReview.objects.filter(product_id=self.product_id, is_approved=True)
        self.total_reviews = reviews.count()
        
        if self.total_reviews > 0:
            avg = reviews.aggregate(models.Avg('rating'))['rating__avg']
            self.average_rating = round(avg, 2) if avg else 0
            
            # Calculate distribution
            self.rating_distribution = {'1': 0, '2': 0, '3': 0, '4': 0, '5': 0}
            for review in reviews:
                key = str(review.rating)
                self.rating_distribution[key] = self.rating_distribution.get(key, 0) + 1
        
        self.save()
