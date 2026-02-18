from django.db import models
from django.core.validators import MinValueValidator
from django.utils import timezone
from django.utils.text import slugify


class Category(models.Model):
    """Category model - PostgreSQL version."""
    
    name = models.CharField(max_length=100)
    slug = models.SlugField(max_length=100, unique=True, db_index=True)
    description = models.TextField(blank=True)
    parent = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='children'
    )
    is_active = models.BooleanField(default=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'categories'
        verbose_name_plural = 'categories'
        ordering = ['name']
    
    def __str__(self):
        return self.name
    
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'slug': self.slug,
            'description': self.description,
        }


class Product(models.Model):
    """Product model - PostgreSQL version."""
    
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('draft', 'Draft'),
        ('archived', 'Archived'),
    ]
    
    name = models.CharField(max_length=255, db_index=True)
    slug = models.SlugField(max_length=255, unique=True, db_index=True)
    sku = models.CharField(max_length=100, unique=True, db_index=True)
    
    description = models.TextField(blank=True)
    short_description = models.CharField(max_length=500, blank=True)
    
    price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0)]
    )
    compare_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(0)]
    )
    cost_per_item = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(0)]
    )
    
    category = models.ForeignKey(
        Category,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='products'
    )
    tags = models.JSONField(default=list, blank=True)
    
    stock_quantity = models.PositiveIntegerField(default=0)
    track_inventory = models.BooleanField(default=True)
    allow_backorders = models.BooleanField(default=False)
    
    weight = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(0)]
    )
    dimensions = models.JSONField(default=dict, blank=True)
    
    is_active = models.BooleanField(default=True, db_index=True)
    is_featured = models.BooleanField(default=False, db_index=True)
    product_status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='active'
    )
    
    deleted_at = models.DateTimeField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'products'
        indexes = [
            models.Index(fields=['slug']),
            models.Index(fields=['sku']),
            models.Index(fields=['price']),
            models.Index(fields=['is_active', 'is_featured']),
            models.Index(fields=['category', 'is_active']),
            models.Index(fields=['name'], name='product_name_idx'),
        ]
        ordering = ['-created_at']
    
    def __str__(self):
        return self.name
    
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)
    
    @property
    def primary_image(self):
        """Get primary product image."""
        primary = self.images.filter(is_primary=True).first()
        if primary:
            return primary
        return self.images.first()
    
    @property
    def discount_percentage(self):
        """Calculate discount percentage."""
        if self.compare_price and self.compare_price > self.price:
            return round(
                ((float(self.compare_price) - float(self.price)) / float(self.compare_price)) * 100,
                2
            )
        return 0
    
    @property
    def in_stock(self):
        """Check if product is in stock."""
        return self.stock_quantity > 0 if self.track_inventory else True
    
    def to_dict(self, include_images=True):
        """Convert product to dictionary."""
        data = {
            'id': self.id,
            'name': self.name,
            'slug': self.slug,
            'sku': self.sku,
            'description': self.description,
            'short_description': self.short_description,
            'price': float(self.price),
            'compare_price': float(self.compare_price) if self.compare_price else None,
            'discount_percentage': self.discount_percentage,
            'category': self.category.to_dict() if self.category else None,
            'tags': self.tags,
            'stock_quantity': self.stock_quantity,
            'in_stock': self.in_stock,
            'is_active': self.is_active,
            'is_featured': self.is_featured,
            'weight': float(self.weight) if self.weight else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }
        
        if include_images:
            data['images'] = [img.to_dict() for img in self.images.all()]
            primary = self.primary_image
            data['primary_image'] = primary.to_dict() if primary else None
        
        return data


class ProductImage(models.Model):
    """Product image model - PostgreSQL version."""
    
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='images'
    )
    image = models.ImageField(upload_to='products/%Y/%m/')
    alt_text = models.CharField(max_length=255, blank=True)
    is_primary = models.BooleanField(default=False)
    sort_order = models.PositiveIntegerField(default=0)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'product_images'
        ordering = ['sort_order', '-is_primary', 'created_at']
    
    def __str__(self):
        return f"Image for {self.product.name}"
    
    def to_dict(self):
        return {
            'id': self.id,
            'url': self.image.url if self.image else None,
            'alt_text': self.alt_text,
            'is_primary': self.is_primary,
        }


class Wishlist(models.Model):
    """Wishlist model - PostgreSQL version."""
    
    user_id = models.CharField(max_length=100, db_index=True)
    user_email = models.EmailField()
    products = models.ManyToManyField(
        Product,
        related_name='wishlisted_by',
        blank=True
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'wishlists'
        indexes = [
            models.Index(fields=['user_id']),
            models.Index(fields=['user_email']),
        ]
    
    def __str__(self):
        return f"Wishlist for {self.user_email}"
    
    def has_product(self, product_id):
        """Check if product is in wishlist."""
        return self.products.filter(id=product_id).exists()
    
    def add_product(self, product):
        """Add product to wishlist."""
        self.products.add(product)
    
    def remove_product(self, product):
        """Remove product from wishlist."""
        self.products.remove(product)
