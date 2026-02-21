"""
Comprehensive API Tests for the E-Commerce Application.
"""

import pytest
from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from decimal import Decimal
import json

from products.models import Product, Category, ProductImage
from orders.models import Order, OrderItem
from offers.models import Coupon, LimitedOffer
from cart.context_processors import cart

User = get_user_model()


class UserModelTests(TestCase):
    """Tests for the User model."""
    
    def setUp(self):
        self.user_data = {
            'email': 'test@example.com',
            'username': 'testuser',
            'password': 'SecurePass123!',
            'first_name': 'Test',
            'last_name': 'User',
        }
    
    def test_create_user(self):
        """Test user creation with valid data."""
        user = User.objects.create_user(**self.user_data)
        self.assertEqual(user.email, self.user_data['email'])
        self.assertEqual(user.username, self.user_data['username'])
        self.assertTrue(user.check_password(self.user_data['password']))
        self.assertTrue(user.is_active)
        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_superuser)
    
    def test_create_superuser(self):
        """Test superuser creation."""
        user = User.objects.create_superuser(**self.user_data)
        self.assertTrue(user.is_staff)
        self.assertTrue(user.is_superuser)
    
    def test_email_required(self):
        """Test that email is required."""
        with self.assertRaises(ValueError):
            User.objects.create_user(
                email='',
                username='test',
                password='pass123'
            )
    
    def test_user_str(self):
        """Test user string representation."""
        user = User.objects.create_user(**self.user_data)
        self.assertEqual(str(user), self.user_data['email'])
    
    def test_get_full_name(self):
        """Test get_full_name method."""
        user = User.objects.create_user(**self.user_data)
        self.assertEqual(user.get_full_name(), 'Test User')


class CategoryModelTests(TestCase):
    """Tests for the Category model."""
    
    def setUp(self):
        self.category = Category.objects.create(
            name='Electronics',
            slug='electronics',
            description='Electronic products'
        )
    
    def test_category_creation(self):
        """Test category creation."""
        self.assertEqual(self.category.name, 'Electronics')
        self.assertEqual(self.category.slug, 'electronics')
    
    def test_category_auto_slug(self):
        """Test auto slug generation."""
        cat = Category.objects.create(name='Test Category')
        self.assertEqual(cat.slug, 'test-category')
    
    def test_category_hierarchy(self):
        """Test category parent-child relationship."""
        child = Category.objects.create(
            name='Phones',
            slug='phones',
            parent=self.category
        )
        self.assertEqual(child.parent, self.category)


class ProductModelTests(TestCase):
    """Tests for the Product model."""
    
    def setUp(self):
        self.category = Category.objects.create(
            name='Electronics',
            slug='electronics'
        )
        self.product = Product.objects.create(
            name='iPhone 15',
            slug='iphone-15',
            sku='IPH15',
            description='Latest iPhone',
            price=Decimal('999.99'),
            compare_price=Decimal('1199.99'),
            category=self.category,
            stock_quantity=100,
            is_active=True,
            is_featured=True
        )
    
    def test_product_creation(self):
        """Test product creation."""
        self.assertEqual(self.product.name, 'iPhone 15')
        self.assertEqual(self.product.price, Decimal('999.99'))
        self.assertTrue(self.product.is_active)
    
    def test_discount_calculation(self):
        """Test discount percentage calculation."""
        discount = self.product.discount_percentage
        self.assertGreater(discount, 0)
        self.assertAlmostEqual(discount, 16.67, places=1)
    
    def test_in_stock_property(self):
        """Test in_stock property."""
        self.assertTrue(self.product.in_stock)
        self.product.stock_quantity = 0
        self.assertFalse(self.product.in_stock)
    
    def test_product_auto_slug(self):
        """Test auto slug generation."""
        prod = Product.objects.create(
            name='Test Product',
            sku='TEST001',
            price=Decimal('99.99')
        )
        self.assertEqual(prod.slug, 'test-product')


class AuthAPITests(APITestCase):
    """Tests for authentication API endpoints."""
    
    def setUp(self):
        self.client = APIClient()
        self.user_data = {
            'email': 'test@example.com',
            'username': 'testuser',
            'password': 'SecurePass123!',
            'password_confirm': 'SecurePass123!',
            'first_name': 'Test',
            'last_name': 'User'
        }
    
    def test_user_registration(self):
        """Test user registration endpoint."""
        response = self.client.post('/api/v1/auth/register/', self.user_data)
        self.assertIn(response.status_code, [status.HTTP_200_OK, status.HTTP_201_CREATED])
    
    def test_user_login(self):
        """Test user login endpoint."""
        # Create user first
        User.objects.create_user(
            email='test@example.com',
            username='testuser',
            password='SecurePass123!'
        )
        response = self.client.post('/api/v1/auth/login/', {
            'email': 'test@example.com',
            'password': 'SecurePass123!'
        })
        self.assertIn(response.status_code, [status.HTTP_200_OK, status.HTTP_201_CREATED])
    
    def test_duplicate_registration(self):
        """Test registration with duplicate email."""
        User.objects.create_user(
            email='test@example.com',
            username='testuser1',
            password='pass123'
        )
        response = self.client.post('/api/v1/auth/register/', self.user_data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class ProductAPITests(APITestCase):
    """Tests for product API endpoints."""
    
    def setUp(self):
        self.client = APIClient()
        self.category = Category.objects.create(
            name='Electronics',
            slug='electronics'
        )
        self.product = Product.objects.create(
            name='iPhone 15',
            slug='iphone-15',
            sku='IPH15',
            description='Latest iPhone',
            price=Decimal('999.99'),
            category=self.category,
            stock_quantity=100,
            is_active=True
        )
    
    def test_product_list(self):
        """Test product list endpoint."""
        response = self.client.get('/api/v1/products/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
    
    def test_product_detail(self):
        """Test product detail endpoint."""
        response = self.client.get(f'/api/v1/products/{self.product.id}/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['name'], 'iPhone 15')
    
    def test_product_detail_by_slug(self):
        """Test product detail by slug."""
        response = self.client.get(f'/api/v1/products/{self.product.slug}/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
    
    def test_product_filter_by_category(self):
        """Test product filtering by category."""
        response = self.client.get(f'/api/v1/products/?category={self.category.slug}')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
    
    def test_product_search(self):
        """Test product search."""
        response = self.client.get('/api/v1/products/?search=iPhone')
        self.assertEqual(response.status_code, status.HTTP_200_OK)


class CartAPITests(APITestCase):
    """Tests for cart API endpoints."""
    
    def setUp(self):
        self.client = APIClient()
        self.category = Category.objects.create(
            name='Electronics',
            slug='electronics'
        )
        self.product = Product.objects.create(
            name='iPhone 15',
            slug='iphone-15',
            sku='IPH15',
            price=Decimal('999.99'),
            category=self.category,
            stock_quantity=100,
            is_active=True
        )
    
    def test_add_to_cart(self):
        """Test adding item to cart."""
        response = self.client.post('/api/v1/cart/add/', {
            'product_id': self.product.id,
            'quantity': 1
        })
        self.assertIn(response.status_code, [status.HTTP_200_OK, status.HTTP_201_CREATED])
    
    def test_add_invalid_product(self):
        """Test adding invalid product to cart."""
        response = self.client.post('/api/v1/cart/add/', {
            'product_id': 99999,
            'quantity': 1
        })
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


class OrderModelTests(TestCase):
    """Tests for the Order model."""
    
    def setUp(self):
        self.user = User.objects.create_user(
            email='test@example.com',
            username='testuser',
            password='pass123'
        )
        self.order = Order.objects.create(
            order_number='ORD-20240101-ABC123',
            user_id=str(self.user.id),
            user_email=self.user.email,
            subtotal=Decimal('100.00'),
            shipping_cost=Decimal('10.00'),
            tax=Decimal('18.00'),
            discount=Decimal('0.00'),
            total=Decimal('128.00'),
            shipping_address={
                'first_name': 'Test',
                'last_name': 'User',
                'email': 'test@example.com',
                'phone': '1234567890',
                'street': '123 Test St',
                'city': 'Test City',
                'state': 'Test State',
                'postal_code': '12345',
                'country': 'USA'
            }
        )
    
    def test_order_creation(self):
        """Test order creation."""
        self.assertEqual(self.order.order_number, 'ORD-20240101-ABC123')
        self.assertEqual(self.order.order_status, 'pending')
        self.assertEqual(self.order.payment_status, 'pending')
    
    def test_order_is_cancellable(self):
        """Test order cancellable property."""
        self.assertTrue(self.order.is_cancellable)
        self.order.order_status = 'shipped'
        self.assertFalse(self.order.is_cancellable)


class CouponModelTests(TestCase):
    """Tests for the Coupon model."""
    
    def setUp(self):
        self.coupon = Coupon.objects.create(
            code='SAVE10',
            description='10% off',
            discount_type='percentage',
            discount_value=Decimal('10.00'),
            min_order_value=Decimal('50.00'),
            max_discount=Decimal('100.00'),
            usage_limit=100,
            per_user_limit=2,
            valid_until='2099-12-31T23:59:59Z'
        )
    
    def test_coupon_creation(self):
        """Test coupon creation."""
        self.assertEqual(self.coupon.code, 'SAVE10')
        self.assertTrue(self.coupon.is_valid)
    
    def test_coupon_discount_calculation(self):
        """Test coupon discount calculation."""
        discount = self.coupon.calculate_discount(Decimal('100.00'))
        self.assertEqual(discount, 10)
    
    def test_coupon_max_discount(self):
        """Test coupon max discount cap."""
        discount = self.coupon.calculate_discount(Decimal('2000.00'))
        # 10% of 2000 = 200, but max is 100
        self.assertEqual(discount, 100)


class HealthCheckTests(APITestCase):
    """Tests for health check endpoints."""
    
    def test_health_check(self):
        """Test health check endpoint."""
        response = self.client.get('/health/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
    
    def test_liveness_check(self):
        """Test liveness check endpoint."""
        response = self.client.get('/alive/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)


class RateLimitingTests(APITestCase):
    """Tests for rate limiting functionality."""
    
    def test_rate_limit_headers(self):
        """Test that rate limiting is applied."""
        # Make multiple requests
        for _ in range(5):
            response = self.client.get('/api/v1/products/')
        # Should still work within limits
        self.assertEqual(response.status_code, status.HTTP_200_OK)


class APIDocsTests(APITestCase):
    """Tests for API documentation endpoints."""
    
    def test_schema_endpoint(self):
        """Test OpenAPI schema endpoint."""
        response = self.client.get('/api/schema/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
    
    def test_swagger_ui(self):
        """Test Swagger UI endpoint."""
        response = self.client.get('/api/docs/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
    
    def test_redoc(self):
        """Test ReDoc endpoint."""
        response = self.client.get('/api/redoc/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)


class SecurityTests(TestCase):
    """Tests for security features."""
    
    def setUp(self):
        self.client = Client()
    
    def test_security_headers(self):
        """Test security headers in response."""
        response = self.client.get('/')
        self.assertIn('X-Content-Type-Options', response.headers)
        self.assertIn('X-Frame-Options', response.headers)
    
    def test_csrf_protection(self):
        """Test CSRF protection on POST requests."""
        response = self.client.post('/accounts/login/', {})
        # Should redirect or show CSRF error
        self.assertIn(response.status_code, [302, 403])
