from django.test import TestCase, Client
from django.urls import reverse
from orders.models import Order, OrderItem
from products.models import Product, Category
from users.models import User
import json


class OrderModelTests(TestCase):
    """Tests for Order model."""
    
    def setUp(self):
        self.user = User.objects.create_user(
            email='test@example.com',
            username='testuser',
            password='testpass123'
        )
        
        self.category = Category.objects.create(name='Electronics', slug='electronics')
        
        self.product = Product.objects.create(
            name='Test Product',
            slug='test-product',
            sku='TEST-001',
            price=99.99,
            category=self.category,
            is_active=True,
            stock_quantity=10,
        )
    
    def test_create_order(self):
        """Test creating a new order."""
        order = Order.objects.create(
            order_number='ORD-20240101-TEST01',
            user_id=str(self.user.id),
            user_email='test@example.com',
            subtotal=199.98,
            shipping_cost=9.99,
            tax=16.00,
            total=225.97,
            shipping_address={
                'first_name': 'Test',
                'last_name': 'User',
                'email': 'test@example.com',
                'street': '123 Main St',
                'city': 'New York',
                'state': 'NY',
                'postal_code': '10001',
                'country': 'USA'
            },
        )
        
        OrderItem.objects.create(
            order=order,
            product_id=self.product.id,
            product_name='Test Product',
            price=99.99,
            quantity=2
        )
        
        self.assertEqual(order.order_number, 'ORD-20240101-TEST01')
        self.assertEqual(order.item_count, 2)
        self.assertEqual(order.total, 225.97)
    
    def test_order_cancellable(self):
        """Test order cancellable property."""
        order = Order.objects.create(
            order_number='ORD-20240101-TEST02',
            user_id=str(self.user.id),
            user_email='test@example.com',
            subtotal=0,
            shipping_cost=0,
            tax=0,
            total=0,
            shipping_address={},
            order_status='pending',
        )
        
        self.assertTrue(order.is_cancellable)
        
        order.order_status = 'delivered'
        order.save()
        self.assertFalse(order.is_cancellable)


class OrderViewTests(TestCase):
    """Tests for order views."""
    
    def setUp(self):
        self.client = Client()
        self.checkout_url = reverse('checkout')
        
        self.user = User.objects.create_user(
            email='test@example.com',
            username='testuser',
            password='testpass123'
        )
        
        self.client.login(username='test@example.com', password='testpass123')
        
        self.category = Category.objects.create(name='Electronics', slug='electronics')
        
        self.product = Product.objects.create(
            name='Test Product',
            slug='test-product',
            sku='TEST-001',
            price=99.99,
            category=self.category,
            is_active=True,
            stock_quantity=10,
        )
    
    def test_checkout_page_requires_items(self):
        """Test checkout page with empty cart."""
        response = self.client.get(self.checkout_url)
        self.assertEqual(response.status_code, 302)
    
    def test_checkout_page_with_items(self):
        """Test checkout page with cart items."""
        self.client.post(
            '/cart/add/',
            data=json.dumps({
                'product_id': str(self.product.id),
                'quantity': 2
            }),
            content_type='application/json'
        )
        
        response = self.client.get(self.checkout_url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'orders/checkout.html')
    
    def test_order_history_requires_login(self):
        """Test order history requires login."""
        self.client.logout()
        response = self.client.get(reverse('order_history'))
        self.assertEqual(response.status_code, 302)
    
    def test_order_history_page(self):
        """Test order history page."""
        response = self.client.get(reverse('order_history'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'orders/order_history.html')
