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


def get_config(key, default=None):
    return SiteConfiguration.get(key, default)
