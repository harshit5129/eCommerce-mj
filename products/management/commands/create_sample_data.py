from django.core.management.base import BaseCommand
from products.models import Product, Category, ProductImage
from users.mongo_models import User
from offers.models import Coupon, LimitedOffer
from datetime import datetime, timedelta


class Command(BaseCommand):
    help = 'Create sample products for testing'
    
    def handle(self, *args, **options):
        self.stdout.write('Creating sample data...')
        
        electronics = Category(name='Electronics', slug='electronics')
        clothing = Category(name='Clothing', slug='clothing')
        books = Category(name='Books', slug='books')
        home = Category(name='Home & Garden', slug='home-garden')
        
        products_data = [
            {
                'name': 'Wireless Bluetooth Headphones',
                'slug': 'wireless-bluetooth-headphones',
                'sku': 'ELEC-001',
                'description': 'Premium wireless headphones with noise cancellation and 30-hour battery life.',
                'short_description': 'Premium wireless headphones',
                'price': 12999,
                'compare_price': 16999,
                'category': electronics,
                'tags': ['audio', 'wireless', 'bluetooth'],
                'stock_quantity': 50,
                'is_featured': True,
            },
            {
                'name': 'Smart Watch Pro',
                'slug': 'smart-watch-pro',
                'sku': 'ELEC-002',
                'description': 'Advanced smartwatch with health monitoring, GPS, and 7-day battery life.',
                'short_description': 'Advanced smartwatch',
                'price': 24999,
                'compare_price': 29999,
                'category': electronics,
                'tags': ['wearable', 'smart', 'fitness'],
                'stock_quantity': 30,
                'is_featured': True,
            },
            {
                'name': 'Laptop Stand Ergonomic',
                'slug': 'laptop-stand-ergonomic',
                'sku': 'HOME-001',
                'description': 'Adjustable aluminum laptop stand for better posture and cooling.',
                'short_description': 'Ergonomic laptop stand',
                'price': 3999,
                'category': home,
                'tags': ['office', 'ergonomic', 'laptop'],
                'stock_quantity': 100,
            },
            {
                'name': 'Cotton T-Shirt Classic',
                'slug': 'cotton-tshirt-classic',
                'sku': 'CLOTH-001',
                'description': 'Premium cotton t-shirt, comfortable and durable.',
                'short_description': 'Classic cotton t-shirt',
                'price': 1999,
                'category': clothing,
                'tags': ['clothing', 'cotton', 'casual'],
                'stock_quantity': 200,
            },
            {
                'name': 'Programming Book Collection',
                'slug': 'programming-book-collection',
                'sku': 'BOOK-001',
                'description': 'Collection of essential programming books for developers.',
                'short_description': 'Programming books bundle',
                'price': 6999,
                'compare_price': 8999,
                'category': books,
                'tags': ['programming', 'development', 'coding'],
                'stock_quantity': 25,
                'is_featured': True,
            },
            {
                'name': 'USB-C Hub Multiport',
                'slug': 'usb-c-hub-multiport',
                'sku': 'ELEC-003',
                'description': '7-in-1 USB-C hub with HDMI, USB 3.0, and card reader.',
                'short_description': 'Multiport USB-C hub',
                'price': 2999,
                'category': electronics,
                'tags': ['usb', 'hub', 'accessories'],
                'stock_quantity': 75,
            },
            {
                'name': 'Desk Lamp LED',
                'slug': 'desk-lamp-led',
                'sku': 'HOME-002',
                'description': 'Adjustable LED desk lamp with multiple brightness levels.',
                'short_description': 'LED desk lamp',
                'price': 2499,
                'category': home,
                'tags': ['lamp', 'led', 'desk'],
                'stock_quantity': 60,
            },
            {
                'name': 'Running Shoes Comfort',
                'slug': 'running-shoes-comfort',
                'sku': 'CLOTH-002',
                'description': 'Lightweight running shoes with superior cushioning.',
                'short_description': 'Comfortable running shoes',
                'price': 7999,
                'compare_price': 9999,
                'category': clothing,
                'tags': ['shoes', 'running', 'sports'],
                'stock_quantity': 40,
                'is_featured': True,
            },
        ]
        
        created_products = []
        for data in products_data:
            product = Product(**data)
            product.save()
            created_products.append(product)
            self.stdout.write(f'Created: {product.name}')
        
        # Create sample coupons
        coupons_data = [
            {
                'code': 'WELCOME10',
                'description': '10% off for new customers',
                'discount_type': 'percentage',
                'discount_value': 10,
                'min_order_value': 1000,
                'max_discount': 500,
                'usage_limit': 1000,
                'per_user_limit': 1,
                'valid_until': datetime.utcnow() + timedelta(days=365),
                'is_active': True,
                'is_first_order_only': True,
            },
            {
                'code': 'SAVE500',
                'description': '₹500 off on orders above ₹5000',
                'discount_type': 'fixed',
                'discount_value': 500,
                'min_order_value': 5000,
                'usage_limit': 500,
                'per_user_limit': 2,
                'valid_until': datetime.utcnow() + timedelta(days=90),
                'is_active': True,
                'is_first_order_only': False,
            },
            {
                'code': 'FLASH20',
                'description': '20% off flash sale',
                'discount_type': 'percentage',
                'discount_value': 20,
                'min_order_value': 2000,
                'max_discount': 2000,
                'usage_limit': 100,
                'per_user_limit': 1,
                'valid_until': datetime.utcnow() + timedelta(days=7),
                'is_active': True,
                'is_first_order_only': False,
            },
        ]
        
        for coupon_data in coupons_data:
            coupon = Coupon(**coupon_data)
            coupon.save()
            self.stdout.write(f'Created coupon: {coupon.code}')
        
        # Create sample limited time offer
        offer = LimitedOffer(
            name='Diwali Flash Sale',
            slug='diwali-flash-sale',
            description='Exclusive Diwali discounts on electronics and fashion!',
            offer_type='flash_sale',
            product_ids=[str(p.id) for p in created_products[:4]],
            discount_type='percentage',
            discount_value=15,
            starts_at=datetime.utcnow(),
            ends_at=datetime.utcnow() + timedelta(days=7),
            banner_text='🎉 Diwali Sale - Up to 15% OFF!',
            is_active=True,
            show_countdown=True,
        )
        offer.save()
        self.stdout.write(f'Created offer: {offer.name}')
        
        # Create admin user
        admin_user = User(
            email='admin@example.com',
            username='admin',
            first_name='Admin',
            last_name='User',
            is_staff=True,
            is_superuser=True,
        )
        admin_user.set_password('admin123')
        admin_user.save()
        
        self.stdout.write(self.style.SUCCESS('Sample data created successfully!'))
        self.stdout.write('Admin credentials: admin@example.com / admin123')
        self.stdout.write('Coupons: WELCOME10, SAVE500, FLASH20')
