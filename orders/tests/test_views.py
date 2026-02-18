from django.test import TestCase, Client
from django.urls import reverse
from orders.models import Order, OrderItem, ShippingAddress
from products.models import Product, Category
from users.mongo_models import User
import json


class OrderModelTests(TestCase):
    """Tests for Order model."""
    
    def setUp(self):
        self.user = User(
            email='test@example.com',
            username='testuser'
        )
        self.user.save()
        
        self.category = Category(name='Electronics', slug='electronics')
        
        self.product = Product(
            name='Test Product',
            slug='test-product',
            sku='TEST-001',
            price=99.99,
            category=self.category,
            is_active=True,
            stock_quantity=10,
        )
        self.product.save()
    
    def test_create_order(self):
        """Test creating a new order."""
        address = ShippingAddress(
            first_name='Test',
            last_name='User',
            email='test@example.com',
            street='123 Main St',
            city='New York',
            state='NY',
            postal_code='10001',
            country='USA'
        )
        
        order = Order(
            order_number='ORD-20240101-TEST01',
            user_id=str(self.user.id),
            user_email='test@example.com',
            items=[
                OrderItem(
                    product_id=str(self.product.id),
                    product_name='Test Product',
                    price=99.99,
                    quantity=2
                )
            ],
            subtotal=199.98,
            shipping_cost=9.99,
            tax=16.00,
            total=225.97,
            shipping_address=address,
        )
        order.save()
        
        self.assertEqual(order.order_number, 'ORD-20240101-TEST01')
        self.assertEqual(order.item_count, 2)
        self.assertEqual(order.total, 225.97)
    
    def test_order_cancellable(self):
        """Test order cancellable property."""
        address = ShippingAddress(
            first_name='Test',
            last_name='User',
            email='test@example.com',
            street='123 Main St',
            city='New York',
            state='NY',
            postal_code='10001',
            country='USA'
        )
        
        order = Order(
            order_number='ORD-20240101-TEST02',
            user_id=str(self.user.id),
            user_email='test@example.com',
            items=[],
            subtotal=0,
            shipping_cost=0,
            tax=0,
            total=0,
            shipping_address=address,
            order_status='pending',
        )
        
        self.assertTrue(order.is_cancellable)
        
        order.order_status = 'delivered'
        self.assertFalse(order.is_cancellable)


class OrderViewTests(TestCase):
    """Tests for order views."""
    
    def setUp(self):
        self.client = Client()
        self.checkout_url = reverse('checkout')
        
        self.user = User(
            email='test@example.com',
            username='testuser'
        )
        self.user.set_password('testpass123')
        self.user.save()
        
        self.client.post(reverse('login'), {
            'email': 'test@example.com',
            'password': 'testpass123',
        })
        
        self.category = Category(name='Electronics', slug='electronics')
        
        self.product = Product(
            name='Test Product',
            slug='test-product',
            sku='TEST-001',
            price=99.99,
            category=self.category,
            is_active=True,
            stock_quantity=10,
        )
        self.product.save()
    
    def test_checkout_page_requires_items(self):
        """Test checkout page with empty cart."""
        response = self.client.get(self.checkout_url)
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('cart'))
    
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
