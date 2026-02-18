from django.core.management.base import BaseCommand
from products.models import Product, Category, ProductImage
from users.mongo_models import User


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
                'price': 149.99,
                'compare_price': 199.99,
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
                'price': 299.99,
                'compare_price': 349.99,
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
                'price': 49.99,
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
                'price': 24.99,
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
                'price': 79.99,
                'compare_price': 99.99,
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
                'price': 39.99,
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
                'price': 34.99,
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
                'price': 89.99,
                'compare_price': 119.99,
                'category': clothing,
                'tags': ['shoes', 'running', 'sports'],
                'stock_quantity': 40,
                'is_featured': True,
            },
        ]
        
        for data in products_data:
            product = Product(**data)
            product.save()
            self.stdout.write(f'Created: {product.name}')
        
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
