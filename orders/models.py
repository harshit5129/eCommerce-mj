from django.db import models
from django.core.validators import MinValueValidator
from django.utils import timezone
import json


class Order(models.Model):
    """Order model - PostgreSQL version."""
    
    ORDER_STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('shipped', 'Shipped'),
        ('delivered', 'Delivered'),
        ('cancelled', 'Cancelled'),
        ('refunded', 'Refunded'),
    ]
    
    PAYMENT_STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('paid', 'Paid'),
        ('failed', 'Failed'),
        ('refunded', 'Refunded'),
    ]
    
    PAYMENT_METHOD_CHOICES = [
        ('razorpay', 'Razorpay'),
        ('cod', 'Cash on Delivery'),
    ]
    
    order_number = models.CharField(max_length=50, unique=True, db_index=True)
    user_id = models.CharField(max_length=100, db_index=True)  # Can be 'guest' or user ID
    user_email = models.EmailField()
    
    subtotal = models.DecimalField(max_digits=12, decimal_places=2)
    shipping_cost = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    tax = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    discount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total = models.DecimalField(max_digits=12, decimal_places=2)
    
    # Shipping Address stored as JSON for flexibility
    shipping_address = models.JSONField()
    
    order_status = models.CharField(
        max_length=20,
        choices=ORDER_STATUS_CHOICES,
        default='pending',
        db_index=True
    )
    payment_status = models.CharField(
        max_length=20,
        choices=PAYMENT_STATUS_CHOICES,
        default='pending'
    )
    payment_method = models.CharField(
        max_length=20,
        choices=PAYMENT_METHOD_CHOICES,
        default='razorpay'
    )
    
    notes = models.TextField(blank=True)
    
    shipping_method = models.CharField(max_length=100, blank=True)
    tracking_number = models.CharField(max_length=100, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)
    
    # Razorpay payment fields
    razorpay_order_id = models.CharField(max_length=100, blank=True, db_index=True)
    razorpay_payment_id = models.CharField(max_length=100, blank=True)
    razorpay_signature = models.CharField(max_length=255, blank=True)
    
    class Meta:
        db_table = 'orders'
        indexes = [
            models.Index(fields=['order_number']),
            models.Index(fields=['user_id']),
            models.Index(fields=['user_email']),
            models.Index(fields=['order_status']),
            models.Index(fields=['payment_status']),
            models.Index(fields=['user_id', '-created_at']),
        ]
        ordering = ['-created_at']
        constraints = [
            models.CheckConstraint(
                condition=models.Q(subtotal__gte=0),
                name='order_subtotal_non_negative'
            ),
            models.CheckConstraint(
                condition=models.Q(total__gte=0),
                name='order_total_non_negative'
            ),
            models.CheckConstraint(
                condition=models.Q(shipping_cost__gte=0),
                name='order_shipping_cost_non_negative'
            ),
            models.CheckConstraint(
                condition=models.Q(tax__gte=0),
                name='order_tax_non_negative'
            ),
            models.CheckConstraint(
                condition=models.Q(discount__gte=0),
                name='order_discount_non_negative'
            ),
        ]
    
    def __str__(self):
        return f"Order {self.order_number}"
    
    @property
    def item_count(self):
        """Total quantity of items in order."""
        return sum(item.quantity for item in self.items.all())
    
    @property
    def is_cancellable(self):
        """Check if order can be cancelled."""
        return self.order_status in ['pending', 'processing']
    
    def to_dict(self):
        """Convert order to dictionary."""
        return {
            'id': self.id,
            'order_number': self.order_number,
            'user_id': self.user_id,
            'user_email': self.user_email,
            'items': [item.to_dict() for item in self.items.all()],
            'item_count': self.item_count,
            'subtotal': float(self.subtotal),
            'shipping_cost': float(self.shipping_cost),
            'tax': float(self.tax),
            'discount': float(self.discount),
            'total': float(self.total),
            'shipping_address': self.shipping_address,
            'order_status': self.order_status,
            'payment_status': self.payment_status,
            'payment_method': self.payment_method,
            'notes': self.notes,
            'tracking_number': self.tracking_number,
            'is_cancellable': self.is_cancellable,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }


class OrderItem(models.Model):
    """Order item model - PostgreSQL version."""
    
    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name='items'
    )
    
    product_id = models.IntegerField()  # Reference to Product.id
    product_name = models.CharField(max_length=255)
    product_sku = models.CharField(max_length=100, blank=True, default='')
    product_image = models.URLField(max_length=500, blank=True, default='')
    
    price = models.DecimalField(max_digits=10, decimal_places=2)
    quantity = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    
    class Meta:
        db_table = 'order_items'
        indexes = [
            models.Index(fields=['product_id']),
        ]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(price__gte=0),
                name='order_item_price_non_negative'
            ),
            models.CheckConstraint(
                condition=models.Q(quantity__gte=1),
                name='order_item_quantity_at_least_one'
            ),
        ]
    
    def __str__(self):
        return f"{self.product_name} x {self.quantity}"
    
    @property
    def total(self):
        """Calculate item total."""
        return float(self.price) * self.quantity
    
    def to_dict(self):
        """Convert order item to dictionary."""
        return {
            'product_id': self.product_id,
            'product_name': self.product_name,
            'product_sku': self.product_sku,
            'product_image': self.product_image,
            'price': float(self.price),
            'quantity': self.quantity,
            'total': self.total
        }


class PaymentTransaction(models.Model):
    """Payment transaction log for tracking all payment attempts."""
    
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('initiated', 'Initiated'),
        ('success', 'Success'),
        ('failed', 'Failed'),
        ('refunded', 'Refunded'),
    ]
    
    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name='payment_transactions'
    )
    
    transaction_id = models.CharField(max_length=100, unique=True)
    payment_method = models.CharField(max_length=20)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    
    # Razorpay specific
    razorpay_order_id = models.CharField(max_length=100, blank=True)
    razorpay_payment_id = models.CharField(max_length=100, blank=True)
    razorpay_signature = models.CharField(max_length=255, blank=True)
    
    # Error tracking
    error_code = models.CharField(max_length=100, blank=True)
    error_message = models.TextField(blank=True)
    
    # Metadata
    response_data = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'payment_transactions'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['transaction_id']),
            models.Index(fields=['razorpay_order_id']),
            models.Index(fields=['razorpay_payment_id']),
            models.Index(fields=['status']),
        ]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(amount__gte=0),
                name='payment_transaction_amount_non_negative'
            ),
        ]
    
    def __str__(self):
        return f"Payment {self.transaction_id} - {self.status}"
