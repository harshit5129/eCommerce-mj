from datetime import datetime
from mongoengine import (
    Document, EmbeddedDocument,
    StringField, BooleanField, DateTimeField,
    IntField, FloatField, ListField, EmbeddedDocumentField,
    DictField
)


class Category(EmbeddedDocument):
    """Embedded category for product classification."""
    name = StringField(required=True, max_length=100)
    slug = StringField(required=True, max_length=100)
    
    def to_dict(self):
        return {
            'name': self.name,
            'slug': self.slug
        }


class ProductImage(EmbeddedDocument):
    """Embedded image document for products."""
    url = StringField(required=True)
    alt_text = StringField(max_length=255)
    is_primary = BooleanField(default=False)
    
    def to_dict(self):
        return {
            'url': self.url,
            'alt_text': self.alt_text,
            'is_primary': self.is_primary
        }


class Product(Document):
    """
    Product model for e-commerce catalog.
    
    Design decisions:
    - Embedded categories (few per product, fast access)
    - Embedded images (products typically have few images)
    - Denormalized fields for read performance (name in cart items)
    - Sparse indexes for optional fields
    - Text index for search functionality
    """
    
    name = StringField(required=True, max_length=255)
    slug = StringField(required=True, unique=True, max_length=255)
    sku = StringField(required=True, unique=True, max_length=100)
    
    description = StringField()
    short_description = StringField(max_length=500)
    
    price = FloatField(required=True, min_value=0)
    compare_price = FloatField(min_value=0)
    cost_per_item = FloatField(min_value=0)
    
    category = EmbeddedDocumentField(Category)
    tags = ListField(StringField(max_length=50), default=list)
    
    images = ListField(EmbeddedDocumentField(ProductImage), default=list)
    
    stock_quantity = IntField(default=0, min_value=0)
    track_inventory = BooleanField(default=True)
    allow_backorders = BooleanField(default=False)
    
    weight = FloatField(min_value=0)
    dimensions = DictField()
    
    is_active = BooleanField(default=True)
    is_featured = BooleanField(default=False)
    product_status = StringField(max_length=20, default='active')
    
    meta = {
        'collection': 'products',
        'indexes': [
            'slug',
            'sku',
            'price',
            'is_active',
            'is_featured',
            'category.slug',
            {
                'fields': ['$name', '$description', '$tags'],
                'default_language': 'english',
                'unique': False,
                'sparse': False,
                'name': 'product_text_index'
            }
        ],
        'ordering': ['-created_at']
    }
    
    created_at = DateTimeField(default=datetime.utcnow)
    updated_at = DateTimeField(default=datetime.utcnow)
    
    def save(self, *args, **kwargs):
        self.updated_at = datetime.utcnow()
        return super().save(*args, **kwargs)
    
    @property
    def primary_image(self):
        for img in self.images:
            if img.is_primary:
                return img
        return self.images[0] if self.images else None
    
    @property
    def discount_percentage(self):
        if self.compare_price and self.compare_price > self.price:
            return round(((self.compare_price - self.price) / self.compare_price) * 100, 2)
        return 0
    
    @property
    def in_stock(self):
        return self.stock_quantity > 0 if self.track_inventory else True
    
    def __str__(self):
        return self.name
    
    def to_dict(self, include_images=True):
        data = {
            'id': str(self.id),
            'name': self.name,
            'slug': self.slug,
            'sku': self.sku,
            'description': self.description,
            'short_description': self.short_description,
            'price': self.price,
            'compare_price': self.compare_price,
            'discount_percentage': self.discount_percentage,
            'category': self.category.to_dict() if self.category else None,
            'tags': self.tags,
            'stock_quantity': self.stock_quantity,
            'in_stock': self.in_stock,
            'is_active': self.is_active,
            'is_featured': self.is_featured,
            'weight': self.weight,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }
        if include_images:
            data['images'] = [img.to_dict() for img in self.images]
            data['primary_image'] = self.primary_image.to_dict() if self.primary_image else None
        return data
