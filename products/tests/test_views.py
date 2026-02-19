from django.test import TestCase, Client
from django.urls import reverse
from products.models import Product, Category, ProductImage
import json


class ProductModelTests(TestCase):
    """Tests for Product model."""
    
    def setUp(self):
        self.category = Category.objects.create(name='Electronics', slug='electronics')
    
    def test_create_product(self):
        """Test creating a new product."""
        product = Product.objects.create(
            name='Test Product',
            slug='test-product',
            sku='TEST-001',
            price=99.99,
            category=self.category,
            stock_quantity=10,
        )
        
        self.assertEqual(product.name, 'Test Product')
        self.assertEqual(product.price, 99.99)
        self.assertTrue(product.in_stock)
    
    def test_product_discount(self):
        """Test product discount calculation."""
        product = Product.objects.create(
            name='Sale Product',
            slug='sale-product',
            sku='SALE-001',
            price=80.00,
            compare_price=100.00,
        )
        
        self.assertEqual(product.discount_percentage, 20.0)
    
    def test_product_out_of_stock(self):
        """Test out of stock product."""
        product = Product.objects.create(
            name='Out of Stock',
            slug='out-of-stock',
            sku='OOS-001',
            price=50.00,
            stock_quantity=0,
            track_inventory=True,
        )
        
        self.assertFalse(product.in_stock)


class ProductViewTests(TestCase):
    """Tests for product views."""
    
    def setUp(self):
        self.client = Client()
        self.home_url = reverse('home')
        self.product_list_url = reverse('product_list')
        
        self.category = Category.objects.create(name='Electronics', slug='electronics')
        
        self.product = Product.objects.create(
            name='Test Product',
            slug='test-product',
            sku='TEST-001',
            price=99.99,
            category=self.category,
            is_active=True,
        )
    
    def test_home_page(self):
        """Test home page loads."""
        response = self.client.get(self.home_url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'products/home.html')
    
    def test_product_list_page(self):
        """Test product list page loads."""
        response = self.client.get(self.product_list_url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'products/product_list.html')
    
    def test_product_list_contains_product(self):
        """Test product list contains products."""
        response = self.client.get(self.product_list_url)
        self.assertContains(response, 'Test Product')
    
    def test_product_detail_page(self):
        """Test product detail page."""
        url = reverse('product_detail', args=['test-product'])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'products/product_detail.html')
    
    def test_product_search(self):
        """Test product search."""
        response = self.client.get(self.product_list_url, {'search': 'Test'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Test Product')


class CartViewTests(TestCase):
    """Tests for cart functionality."""
    
    def setUp(self):
        self.client = Client()
        self.cart_url = reverse('cart')
        
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
    
    def test_empty_cart(self):
        """Test empty cart page."""
        response = self.client.get(self.cart_url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'cart/cart.html')
    
    def test_add_to_cart(self):
        """Test adding product to cart."""
        response = self.client.post(
            '/cart/add/',
            data=json.dumps({
                'product_id': str(self.product.id),
                'quantity': 1
            }),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)
        
        session = self.client.session
        self.assertEqual(len(session.get('cart', [])), 1)
    
    def test_add_to_cart_out_of_stock(self):
        """Test adding out of stock product to cart."""
        self.product.stock_quantity = 0
        self.product.save()
        
        response = self.client.post(
            '/cart/add/',
            data=json.dumps({
                'product_id': str(self.product.id),
                'quantity': 1
            }),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 400)
