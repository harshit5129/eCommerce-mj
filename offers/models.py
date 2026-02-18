from datetime import datetime
from mongoengine import (
    Document, EmbeddedDocument,
    StringField, BooleanField, DateTimeField,
    IntField, FloatField, ListField, EmbeddedDocumentField,
    DictField, ObjectIdField
)
from bson import ObjectId


class Coupon(Document):
    """Coupon/Discount code model."""
    
    DISCOUNT_TYPE_CHOICES = (
        ('percentage', 'Percentage'),
        ('fixed', 'Fixed Amount'),
    )
    
    code = StringField(required=True, unique=True, max_length=50)
    description = StringField(max_length=200)
    
    discount_type = StringField(choices=DISCOUNT_TYPE_CHOICES, default='percentage')
    discount_value = FloatField(required=True, min_value=0)
    
    min_order_value = FloatField(default=0)
    max_discount = FloatField(default=0)
    
    usage_limit = IntField(default=0)
    used_count = IntField(default=0)
    per_user_limit = IntField(default=1)
    
    valid_from = DateTimeField(default=datetime.utcnow)
    valid_until = DateTimeField(required=True)
    
    is_active = BooleanField(default=True)
    is_first_order_only = BooleanField(default=False)
    
    applicable_categories = ListField(StringField(), default=list)
    applicable_products = ListField(StringField(), default=list)
    
    created_at = DateTimeField(default=datetime.utcnow)
    
    meta = {
        'collection': 'coupons',
        'indexes': ['code', 'is_active', 'valid_until']
    }
    
    @property
    def is_valid(self):
        now = datetime.utcnow()
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
        if cart_total < self.min_order_value:
            return 0
        
        if self.discount_type == 'percentage':
            discount = (self.discount_value / 100) * cart_total
            if self.max_discount > 0:
                discount = min(discount, self.max_discount)
        else:
            discount = self.discount_value
        
        return round(discount, 2)
    
    def can_use(self, user_email):
        if not self.is_valid:
            return False, "Coupon is not valid"
        
        if self.is_first_order_only:
            from orders.models import Order
            existing_orders = Order.objects(user_email=user_email).count()
            if existing_orders > 0:
                return False, "This coupon is only for first-time customers"
        
        return True, "Valid"
    
    def __str__(self):
        return self.code


class CouponUsage(Document):
    """Track coupon usage per user."""
    
    coupon_id = ObjectIdField(required=True)
    coupon_code = StringField(required=True)
    user_email = StringField(required=True)
    order_number = StringField(required=True)
    discount_amount = FloatField(required=True)
    used_at = DateTimeField(default=datetime.utcnow)
    
    meta = {
        'collection': 'coupon_usage',
        'indexes': ['coupon_id', 'user_email', 'order_number']
    }


class LimitedOffer(Document):
    """Limited time flash sale offer."""
    
    OFFER_TYPE_CHOICES = (
        ('flash_sale', 'Flash Sale'),
        ('deal_of_day', 'Deal of the Day'),
        ('weekend_special', 'Weekend Special'),
        ('clearance', 'Clearance'),
    )
    
    name = StringField(required=True, max_length=100)
    slug = StringField(required=True, unique=True, max_length=100)
    description = StringField(max_length=500)
    offer_type = StringField(choices=OFFER_TYPE_CHOICES, default='flash_sale')
    
    product_ids = ListField(StringField(), default=list)
    category_ids = ListField(StringField(), default=list)
    
    discount_type = StringField(choices=[('percentage', 'Percentage'), ('fixed', 'Fixed')], default='percentage')
    discount_value = FloatField(required=True, min_value=0)
    
    original_prices = DictField(default=dict)
    
    starts_at = DateTimeField(required=True)
    ends_at = DateTimeField(required=True)
    
    banner_image = StringField()
    banner_text = StringField(max_length=100)
    banner_color = StringField(default='red')
    
    is_active = BooleanField(default=True)
    show_countdown = BooleanField(default=True)
    show_banner = BooleanField(default=True)
    
    max_items = IntField(default=0)
    items_sold = IntField(default=0)
    
    created_at = DateTimeField(default=datetime.utcnow)
    
    meta = {
        'collection': 'limited_offers',
        'indexes': ['slug', 'is_active', 'starts_at', 'ends_at']
    }
    
    @property
    def is_live(self):
        now = datetime.utcnow()
        return (
            self.is_active and
            self.starts_at <= now and
            self.ends_at >= now
        )
    
    @property
    def is_upcoming(self):
        now = datetime.utcnow()
        return self.is_active and self.starts_at > now
    
    @property
    def time_remaining(self):
        if not self.is_live:
            return None
        remaining = self.ends_at - datetime.utcnow()
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
        if self.discount_type == 'percentage':
            return original_price * (1 - self.discount_value / 100)
        return max(0, original_price - self.discount_value)
    
    def __str__(self):
        return self.name


class ProductReview(Document):
    """Product review and rating model."""
    
    product_id = ObjectIdField(required=True)
    user_email = StringField(required=True)
    user_name = StringField(required=True)
    
    rating = IntField(required=True, min_value=1, max_value=5)
    title = StringField(max_length=100)
    review = StringField(max_length=2000)
    images = ListField(StringField(), default=list)
    
    is_verified_purchase = BooleanField(default=False)
    order_number = StringField()
    
    helpful_count = IntField(default=0)
    helpful_users = ListField(StringField(), default=list)
    
    is_approved = BooleanField(default=True)
    admin_response = StringField()
    
    pros = ListField(StringField(), default=list)
    cons = ListField(StringField(), default=list)
    
    created_at = DateTimeField(default=datetime.utcnow)
    updated_at = DateTimeField(default=datetime.utcnow)
    
    meta = {
        'collection': 'product_reviews',
        'indexes': ['product_id', 'user_email', 'rating', 'created_at']
    }
    
    def save(self, *args, **kwargs):
        self.updated_at = datetime.utcnow()
        return super().save(*args, **kwargs)
    
    @property
    def stars_display(self):
        filled = self.rating
        empty = 5 - self.rating
        return {'filled': range(filled), 'empty': range(empty)}
    
    def mark_helpful(self, user_email):
        if user_email not in self.helpful_users:
            self.helpful_users.append(user_email)
            self.helpful_count += 1
            self.save()
            return True
        return False
    
    def __str__(self):
        return f"Review by {self.user_name} - {self.rating} stars"


class ReviewSummary(EmbeddedDocument):
    """Summary of product reviews."""
    
    total_reviews = IntField(default=0)
    average_rating = FloatField(default=0)
    rating_distribution = DictField(default=lambda: {'1': 0, '2': 0, '3': 0, '4': 0, '5': 0})
    
    def update_from_reviews(self, reviews):
        self.total_reviews = len(reviews)
        if self.total_reviews > 0:
            self.average_rating = sum(r.rating for r in reviews) / self.total_reviews
            self.rating_distribution = {'1': 0, '2': 0, '3': 0, '4': 0, '5': 0}
            for r in reviews:
                self.rating_distribution[str(r.rating)] = self.rating_distribution.get(str(r.rating), 0) + 1
