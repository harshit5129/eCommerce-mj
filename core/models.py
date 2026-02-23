from django.db import models
from django.core.exceptions import ValidationError


class SiteConfiguration(models.Model):
    SETTING_TYPES = (
        ('string', 'String'),
        ('integer', 'Integer'),
        ('boolean', 'Boolean'),
        ('email', 'Email'),
        ('url', 'URL'),
        ('password', 'Password'),
    )

    SETTINGS_CATEGORIES = (
        ('database', 'Database'),
        ('email', 'Email'),
        ('payment', 'Payment Gateway'),
        ('security', 'Security'),
        ('general', 'General'),
        ('social', 'Social Auth'),
        ('redis', 'Redis/Cache'),
        ('storage', 'Storage'),
    )

    key = models.CharField(max_length=100, unique=True, db_index=True)
    value = models.TextField(blank=True)
    description = models.CharField(max_length=255, blank=True)
    setting_type = models.CharField(max_length=20, choices=SETTING_TYPES, default='string')
    category = models.CharField(max_length=20, choices=SETTINGS_CATEGORIES, default='general')
    is_secret = models.BooleanField(default=False, help_text="Hide value in admin (for passwords, keys)")
    is_required = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['category', 'key']
        verbose_name = 'Site Configuration'
        verbose_name_plural = 'Site Configuration'

    def __str__(self):
        return self.key

    def get_value(self):
        if self.setting_type == 'boolean':
            return self.value.lower() in ('true', '1', 'yes')
        elif self.setting_type == 'integer':
            try:
                return int(self.value)
            except (ValueError, TypeError):
                return 0
        return self.value

    @classmethod
    def get(cls, key, default=None):
        try:
            config = cls.objects.get(key=key)
            return config.get_value()
        except cls.DoesNotExist:
            return default

    @classmethod
    def set(cls, key, value, **kwargs):
        obj, created = cls.objects.update_or_create(
            key=key,
            defaults={'value': str(value), **kwargs}
        )
        return obj


class HeroImage(models.Model):
    """Hero banner/slider images for homepage."""
    
    title = models.CharField(max_length=100, blank=True)
    subtitle = models.CharField(max_length=200, blank=True)
    image = models.ImageField(upload_to='hero/')
    mobile_image = models.ImageField(upload_to='hero/', blank=True, null=True, help_text="Optional mobile version")
    
    button_text = models.CharField(max_length=50, blank=True)
    button_link = models.CharField(max_length=255, blank=True)
    
    sort_order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['sort_order', '-created_at']
        verbose_name = 'Hero Image'
        verbose_name_plural = 'Hero Images'
    
    def __str__(self):
        return self.title or f"Hero Image {self.id}"


class SocialLink(models.Model):
    """Social media links for footer/header."""
    
    PLATFORM_CHOICES = (
        ('facebook', 'Facebook'),
        ('instagram', 'Instagram'),
        ('youtube', 'YouTube'),
        ('pinterest', 'Pinterest'),
        ('discord', 'Discord'),
    )
    
    platform = models.CharField(max_length=20, choices=PLATFORM_CHOICES, unique=True)
    url = models.URLField(max_length=255)
    icon_class = models.CharField(max_length=50, blank=True, help_text="Font Awesome icon class (e.g., fab fa-facebook)")
    is_active = models.BooleanField(default=True)
    sort_order = models.PositiveIntegerField(default=0)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['sort_order', 'platform']
        verbose_name = 'Social Link'
        verbose_name_plural = 'Social Links'
    
    def __str__(self):
        return self.get_platform_display()
    
    def save(self, *args, **kwargs):
        if not self.icon_class:
            icon_map = {
                'facebook': 'fab fa-facebook-f',
                'instagram': 'fab fa-instagram',
                'youtube': 'fab fa-youtube',
                'pinterest': 'fab fa-pinterest',
                'discord': 'fab fa-discord',
            }
            self.icon_class = icon_map.get(self.platform, 'fas fa-link')
        super().save(*args, **kwargs)


class SiteSettings(models.Model):
    """Site-wide configurable settings managed through admin panel."""
    
    # Store Settings
    store_name = models.CharField(max_length=100, default='E-Commerce Store')
    store_email = models.EmailField(default='contact@store.com')
    store_phone = models.CharField(max_length=20, blank=True)
    store_address = models.TextField(blank=True)
    
    # Shipping Settings
    free_shipping_threshold = models.DecimalField(
        max_digits=10, decimal_places=2, default=4000,
        help_text="Order amount above which shipping is free"
    )
    shipping_cost = models.DecimalField(
        max_digits=10, decimal_places=2, default=99,
        help_text="Default shipping cost"
    )
    
    # Tax Settings
    tax_rate = models.DecimalField(
        max_digits=5, decimal_places=2, default=18,
        help_text="Tax rate percentage (e.g., 18 for 18% GST)"
    )
    tax_name = models.CharField(max_length=50, default='GST')
    
    # Currency Settings
    currency_code = models.CharField(max_length=3, default='INR')
    currency_symbol = models.CharField(max_length=5, default='₹')
    
    # Order Settings
    order_prefix = models.CharField(max_length=10, default='ORD')
    min_order_amount = models.DecimalField(
        max_digits=10, decimal_places=2, default=0,
        help_text="Minimum order amount allowed"
    )
    
    # Inventory Settings
    low_stock_threshold = models.PositiveIntegerField(
        default=10,
        help_text="Alert when stock falls below this level"
    )
    allow_out_of_stock_purchase = models.BooleanField(
        default=False,
        help_text="Allow purchasing items that are out of stock"
    )
    
    # SEO Settings
    meta_title = models.CharField(max_length=200, blank=True)
    meta_description = models.TextField(max_length=500, blank=True)
    meta_keywords = models.CharField(max_length=500, blank=True)
    
    # Social Media Links
    facebook_url = models.URLField(blank=True)
    instagram_url = models.URLField(blank=True)
    twitter_url = models.URLField(blank=True)
    youtube_url = models.URLField(blank=True)
    pinterest_url = models.URLField(blank=True)
    
    # Analytics Settings
    google_analytics_id = models.CharField(max_length=50, blank=True)
    facebook_pixel_id = models.CharField(max_length=50, blank=True)
    
    # Feature Flags
    enable_reviews = models.BooleanField(default=True)
    enable_wishlist = models.BooleanField(default=True)
    enable_coupons = models.BooleanField(default=True)
    enable_newsletter = models.BooleanField(default=True)
    
    # Email Settings
    order_confirmation_email = models.BooleanField(default=True)
    order_shipped_email = models.BooleanField(default=True)
    order_cancelled_email = models.BooleanField(default=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Site Settings'
        verbose_name_plural = 'Site Settings'
    
    def __str__(self):
        return self.store_name
    
    @classmethod
    def get_settings(cls):
        """Get or create site settings singleton."""
        settings, _ = cls.objects.get_or_create(pk=1)
        return settings
    
    def save(self, *args, **kwargs):
        # Ensure only one instance exists
        self.pk = 1
        super().save(*args, **kwargs)
    
    def delete(self, *args, **kwargs):
        pass  # Prevent deletion of settings


def get_config(key, default=None):
    return SiteConfiguration.get(key, default)
