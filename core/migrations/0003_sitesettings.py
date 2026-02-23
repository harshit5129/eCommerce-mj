from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0002_heroimage_sociallink_and_more'),
    ]

    operations = [
        migrations.CreateModel(
            name='SiteSettings',
            fields=[
                ('id', models.AutoField(primary_key=True)),
                ('store_name', models.CharField(default='E-Commerce Store', max_length=100)),
                ('store_email', models.EmailField(default='contact@store.com')),
                ('store_phone', models.CharField(blank=True, max_length=20)),
                ('store_address', models.TextField(blank=True)),
                ('free_shipping_threshold', models.DecimalField(decimal_places=2, default=4000, max_digits=10, help_text='Order amount above which shipping is free')),
                ('shipping_cost', models.DecimalField(decimal_places=2, default=99, help_text='Default shipping cost', max_digits=10)),
                ('tax_rate', models.DecimalField(decimal_places=2, default=18, help_text='Tax rate percentage (e.g., 18 for 18% GST)', max_digits=5)),
                ('tax_name', models.CharField(default='GST', max_length=50)),
                ('currency_code', models.CharField(default='INR', max_length=3)),
                ('currency_symbol', models.CharField(default='₹', max_length=5)),
                ('order_prefix', models.CharField(default='ORD', max_length=10)),
                ('min_order_amount', models.DecimalField(decimal_places=2, default=0, help_text='Minimum order amount allowed', max_digits=10)),
                ('low_stock_threshold', models.PositiveIntegerField(default=10, help_text='Alert when stock falls below this level')),
                ('allow_out_of_stock_purchase', models.BooleanField(default=False, help_text='Allow purchasing items that are out of stock')),
                ('meta_title', models.CharField(blank=True, max_length=200)),
                ('meta_description', models.TextField(blank=True, max_length=500)),
                ('meta_keywords', models.CharField(blank=True, max_length=500)),
                ('facebook_url', models.URLField(blank=True)),
                ('instagram_url', models.URLField(blank=True)),
                ('twitter_url', models.URLField(blank=True)),
                ('youtube_url', models.URLField(blank=True)),
                ('pinterest_url', models.URLField(blank=True)),
                ('google_analytics_id', models.CharField(blank=True, max_length=50)),
                ('facebook_pixel_id', models.CharField(blank=True, max_length=50)),
                ('enable_reviews', models.BooleanField(default=True)),
                ('enable_wishlist', models.BooleanField(default=True)),
                ('enable_coupons', models.BooleanField(default=True)),
                ('enable_newsletter', models.BooleanField(default=True)),
                ('order_confirmation_email', models.BooleanField(default=True)),
                ('order_shipped_email', models.BooleanField(default=True)),
                ('order_cancelled_email', models.BooleanField(default=True, help_text='Send email when order is cancelled')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'verbose_name': 'Site Settings',
                'verbose_name_plural': 'Site Settings',
            },
        ),
    ]
