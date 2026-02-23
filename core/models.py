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


def get_config(key, default=None):
    return SiteConfiguration.get(key, default)
