from datetime import datetime
from mongoengine import (
    Document, EmbeddedDocument,
    StringField, BooleanField, DateTimeField,
    EmailField, ListField, EmbeddedDocumentField,
    IntField, FloatField, DictField
)
from django.contrib.auth.hashers import make_password, check_password


class Address(EmbeddedDocument):
    street = StringField(max_length=255)
    city = StringField(max_length=100)
    state = StringField(max_length=100)
    postal_code = StringField(max_length=20)
    country = StringField(max_length=100, default='USA')

    def to_dict(self):
        return {
            'street': self.street,
            'city': self.city,
            'state': self.state,
            'postal_code': self.postal_code,
            'country': self.country
        }


class User(Document):
    """
    User model for authentication and profile management.
    
    Design decisions:
    - Uses email as primary identifier (unique)
    - Password hashing with Django's make_password for compatibility
    - Stores addresses as embedded documents (small number per user)
    - timestamps for audit trail
    """
    
    email = EmailField(required=True, unique=True)
    username = StringField(max_length=150, required=True, unique=True)
    password = StringField(required=True)
    first_name = StringField(max_length=150)
    last_name = StringField(max_length=150)
    
    is_active = BooleanField(default=True)
    is_staff = BooleanField(default=False)
    is_superuser = BooleanField(default=False)
    
    phone = StringField(max_length=20)
    addresses = ListField(EmbeddedDocumentField(Address), default=list)
    
    date_joined = DateTimeField(default=datetime.utcnow)
    last_login = DateTimeField()
    
    meta = {
        'collection': 'users',
        'indexes': [
            'email',
            'username',
            'date_joined'
        ]
    }
    
    def set_password(self, raw_password):
        self.password = make_password(raw_password)
    
    def check_password(self, raw_password):
        return check_password(raw_password, self.password)
    
    def get_full_name(self):
        return f"{self.first_name} {self.last_name}".strip()
    
    def __str__(self):
        return self.email
    
    def to_dict(self, include_email=True):
        data = {
            'id': str(self.id),
            'username': self.username,
            'first_name': self.first_name,
            'last_name': self.last_name,
            'is_active': self.is_active,
            'date_joined': self.date_joined.isoformat() if self.date_joined else None,
            'last_login': self.last_login.isoformat() if self.last_login else None,
        }
        if include_email:
            data['email'] = self.email
        return data


class CartItem(EmbeddedDocument):
    """
    Embedded document for cart items.
    
    Design decision: Embedded in User document for quick access.
    - Cart is typically small (few items)
    - Always accessed with user data
    - No need for separate collection
    """
    product_id = StringField(required=True)
    product_name = StringField(required=True)
    product_price = FloatField(required=True)
    product_image = StringField()
    quantity = IntField(default=1, min_value=1)
    
    def to_dict(self):
        return {
            'product_id': self.product_id,
            'product_name': self.product_name,
            'product_price': self.product_price,
            'product_image': self.product_image,
            'quantity': self.quantity,
            'total': self.product_price * self.quantity
        }
    
    @property
    def total(self):
        return self.product_price * self.quantity
