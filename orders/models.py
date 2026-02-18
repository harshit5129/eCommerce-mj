from datetime import datetime
from mongoengine import (
    Document, EmbeddedDocument,
    StringField, BooleanField, DateTimeField,
    IntField, FloatField, ListField, EmbeddedDocumentField,
    DictField
)


class OrderItem(EmbeddedDocument):
    """
    Embedded order item - embedded because:
    - Order is a complete snapshot, items won't change
    - No need to query items independently
    - Faster reads (single document query)
    """
    product_id = StringField(required=True)
    product_name = StringField(required=True)
    product_sku = StringField()
    product_image = StringField()
    
    price = FloatField(required=True)
    quantity = IntField(required=True, min_value=1)
    
    def to_dict(self):
        return {
            'product_id': self.product_id,
            'product_name': self.product_name,
            'product_sku': self.product_sku,
            'product_image': self.product_image,
            'price': self.price,
            'quantity': self.quantity,
            'total': self.price * self.quantity
        }
    
    @property
    def total(self):
        return self.price * self.quantity


class ShippingAddress(EmbeddedDocument):
    """Embedded shipping address for orders."""
    first_name = StringField(required=True)
    last_name = StringField(required=True)
    email = StringField(required=True)
    phone = StringField()
    
    street = StringField(required=True)
    city = StringField(required=True)
    state = StringField(required=True)
    postal_code = StringField(required=True)
    country = StringField(required=True, default='USA')
    
    def to_dict(self):
        return {
            'first_name': self.first_name,
            'last_name': self.last_name,
            'email': self.email,
            'phone': self.phone,
            'street': self.street,
            'city': self.city,
            'state': self.state,
            'postal_code': self.postal_code,
            'country': self.country
        }
    
    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"
    
    @property
    def full_address(self):
        return f"{self.street}, {self.city}, {self.state} {self.postal_code}, {self.country}"


class Order(Document):
    """
    Order model for e-commerce orders.
    
    Design decisions:
    - Order items embedded (complete snapshot, never changes)
    - Shipping address embedded (historical record)
    - Reference to user_id for queries
    - Status tracking with timestamps
    - Index on user_id for order history queries
    """
    
    ORDER_STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('shipped', 'Shipped'),
        ('delivered', 'Delivered'),
        ('cancelled', 'Cancelled'),
        ('refunded', 'Refunded'),
    )
    
    PAYMENT_STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('paid', 'Paid'),
        ('failed', 'Failed'),
        ('refunded', 'Refunded'),
    )
    
    PAYMENT_METHOD_CHOICES = (
        ('cash', 'Cash on Delivery'),
        ('card', 'Credit/Debit Card'),
    )
    
    order_number = StringField(required=True, unique=True)
    user_id = StringField(required=True)
    user_email = StringField(required=True)
    
    items = ListField(EmbeddedDocumentField(OrderItem), required=True)
    
    subtotal = FloatField(required=True)
    shipping_cost = FloatField(default=0)
    tax = FloatField(default=0)
    discount = FloatField(default=0)
    total = FloatField(required=True)
    
    shipping_address = EmbeddedDocumentField(ShippingAddress, required=True)
    
    order_status = StringField(
        choices=ORDER_STATUS_CHOICES,
        default='pending'
    )
    payment_status = StringField(
        choices=PAYMENT_STATUS_CHOICES,
        default='pending'
    )
    payment_method = StringField(
        choices=PAYMENT_METHOD_CHOICES,
        default='cash'
    )
    
    notes = StringField()
    
    shipping_method = StringField()
    tracking_number = StringField()
    
    created_at = DateTimeField(default=datetime.utcnow)
    updated_at = DateTimeField(default=datetime.utcnow)
    cancelled_at = DateTimeField()
    
    meta = {
        'collection': 'orders',
        'indexes': [
            'order_number',
            'user_id',
            'user_email',
            'order_status',
            'payment_status',
            'created_at',
            {
                'fields': ['user_id', '-created_at'],
                'unique': False
            }
        ],
        'ordering': ['-created_at']
    }
    
    def save(self, *args, **kwargs):
        self.updated_at = datetime.utcnow()
        return super().save(*args, **kwargs)
    
    @property
    def item_count(self):
        return sum(item.quantity for item in self.items)
    
    @property
    def is_cancellable(self):
        return self.order_status in ['pending', 'processing']
    
    def __str__(self):
        return f"Order {self.order_number}"
    
    def to_dict(self):
        return {
            'id': str(self.id),
            'order_number': self.order_number,
            'user_id': self.user_id,
            'user_email': self.user_email,
            'items': [item.to_dict() for item in self.items],
            'item_count': self.item_count,
            'subtotal': self.subtotal,
            'shipping_cost': self.shipping_cost,
            'tax': self.tax,
            'discount': self.discount,
            'total': self.total,
            'shipping_address': self.shipping_address.to_dict() if self.shipping_address else None,
            'order_status': self.order_status,
            'payment_status': self.payment_status,
            'payment_method': self.payment_method,
            'notes': self.notes,
            'tracking_number': self.tracking_number,
            'is_cancellable': self.is_cancellable,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }
