#!/usr/bin/env python
"""
Generate Test Data Script

This script creates sample data for testing the PostgreSQL database.
Run this after running migrations.

Usage:
    python generate_test_data.py
"""

import os
import sys
import random
from datetime import datetime, timedelta

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.development')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import django
django.setup()

from django.db import transaction
from users.models import User
from products.models import Category, Product, ProductImage
from orders.models import Order, OrderItem
from offers.models import Coupon

print("Generating test data...")


@transaction.atomic
def create_categories():
    """Create sample categories."""
    categories_data = [
        {'name': 'Electronics', 'slug': 'electronics'},
        {'name': 'Clothing', 'slug': 'clothing'},
        {'name': 'Home & Garden', 'slug': 'home-garden'},
        {'name': 'Sports', 'slug': 'sports'},
        {'name': 'Books', 'slug': 'books'},
    ]
    
    categories = []
    for data in categories_data:
        cat, _ = Category.objects.get_or_create(slug=data['slug'], defaults=data)
        categories.append(cat)
    
    print(f"Created {len(categories)} categories")
    return categories


@transaction.atomic
def create_products(categories):
    """Create sample products."""
    products_data = [
        {'name': 'Wireless Headphones', 'sku': 'ELEC-001', 'price': 2499, 'category': categories[0]},
        {'name': 'Smart Watch', 'sku': 'ELEC-002', 'price': 4999, 'category': categories[0]},
        {'name': 'Bluetooth Speaker', 'sku': 'ELEC-003', 'price': 1499, 'category': categories[0]},
        {'name': 'Cotton T-Shirt', 'sku': 'CLTH-001', 'price': 599, 'category': categories[1]},
        {'name': 'Denim Jeans', 'sku': 'CLTH-002', 'price': 1499, 'category': categories[1]},
        {'name': 'Running Shoes', 'sku': 'CLTH-003', 'price': 2999, 'category': categories[1]},
        {'name': 'Coffee Maker', 'sku': 'HOME-001', 'price': 3499, 'category': categories[2]},
        {'name': 'Garden Tools Set', 'sku': 'HOME-002', 'price': 1999, 'category': categories[2]},
        {'name': 'Yoga Mat', 'sku': 'SPRT-001', 'price': 799, 'category': categories[3]},
        {'name': 'Dumbbell Set', 'sku': 'SPRT-002', 'price': 2499, 'category': categories[3]},
        {'name': 'Python Programming Book', 'sku': 'BOOK-001', 'price': 899, 'category': categories[4]},
        {'name': 'Web Development Guide', 'sku': 'BOOK-002', 'price': 1299, 'category': categories[4]},
    ]
    
    products = []
    for data in products_data:
        data['slug'] = data['sku'].lower()
        data['stock_quantity'] = random.randint(10, 100)
        data['is_active'] = True
        data['track_inventory'] = True
        
        product, _ = Product.objects.get_or_create(sku=data['sku'], defaults=data)
        products.append(product)
    
    print(f"Created {len(products)} products")
    return products


@transaction.atomic
def create_coupons():
    """Create sample coupons."""
    coupons_data = [
        {
            'code': 'WELCOME10',
            'description': '10% off on your first order',
            'discount_type': 'percentage',
            'discount_value': 10,
            'min_order_value': 1000,
            'is_active': True,
            'valid_until': datetime.now() + timedelta(days=90),
        },
        {
            'code': 'SAVE20',
            'description': '20% off on orders above 2000',
            'discount_type': 'percentage',
            'discount_value': 20,
            'min_order_value': 2000,
            'max_discount': 500,
            'is_active': True,
            'valid_until': datetime.now() + timedelta(days=30),
        },
        {
            'code': 'FLAT100',
            'description': 'Flat ₹100 off',
            'discount_type': 'fixed',
            'discount_value': 100,
            'min_order_value': 500,
            'is_active': True,
            'valid_until': datetime.now() + timedelta(days=60),
        },
    ]
    
    coupons = []
    for data in coupons_data:
        coupon, _ = Coupon.objects.get_or_create(code=data['code'], defaults=data)
        coupons.append(coupon)
    
    print(f"Created {len(coupons)} coupons")
    return coupons


@transaction.atomic
def create_superuser():
    """Create admin superuser."""
    if not User.objects.filter(is_superuser=True).exists():
        User.objects.create_superuser(
            email='admin@example.com',
            username='admin',
            password='admin123',
            first_name='Admin',
            last_name='User',
        )
        print("Created superuser: admin@example.com / admin123")
    else:
        print("Superuser already exists")


def main():
    print("=" * 60)
    print("Test Data Generation")
    print("=" * 60)
    print()
    
    try:
        # Create data in order
        create_superuser()
        categories = create_categories()
        products = create_products(categories)
        coupons = create_coupons()
        
        print()
        print("=" * 60)
        print("✅ Test Data Generated Successfully!")
        print("=" * 60)
        print()
        print("You can now:")
        print("1. Login as admin: admin@example.com / admin123")
        print("2. Browse products at /products/")
        print("3. Test checkout process")
        print("4. Apply coupons: WELCOME10, SAVE20, FLAT100")
        print()
        print("Run the server: python manage.py runserver")
        
    except Exception as e:
        print(f"\n✗ Error generating test data: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    main()
