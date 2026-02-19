from django.test import TestCase, Client
from django.urls import reverse
from users.models import User
import json


class UserModelTests(TestCase):
    """Tests for User model."""
    
    def setUp(self):
        self.client = Client()
    
    def test_create_user(self):
        """Test creating a new user."""
        user = User.objects.create_user(
            email='test@example.com',
            username='testuser',
            password='testpass123',
            first_name='Test',
            last_name='User'
        )
        
        self.assertEqual(user.email, 'test@example.com')
        self.assertTrue(user.check_password('testpass123'))
        self.assertFalse(user.check_password('wrongpass'))
    
    def test_user_str(self):
        """Test user string representation."""
        user = User(email='test@example.com', username='testuser')
        self.assertEqual(str(user), 'test@example.com')


class AuthenticationViewTests(TestCase):
    """Tests for authentication views."""
    
    def setUp(self):
        self.client = Client()
        self.register_url = reverse('register')
        self.login_url = reverse('login')
        self.logout_url = reverse('logout')
        
        self.user = User.objects.create_user(
            email='test@example.com',
            username='testuser',
            password='testpass123',
            first_name='Test',
            last_name='User'
        )
    
    def test_register_get(self):
        """Test register page loads."""
        response = self.client.get(self.register_url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'users/register.html')
    
    def test_register_post_success(self):
        """Test successful user registration."""
        response = self.client.post(self.register_url, {
            'email': 'newuser@example.com',
            'username': 'newuser',
            'first_name': 'New',
            'last_name': 'User',
            'password': 'newpass123',
            'confirm_password': 'newpass123',
        })
        self.assertEqual(response.status_code, 302)
    
    def test_register_post_password_mismatch(self):
        """Test registration with mismatched passwords."""
        response = self.client.post(self.register_url, {
            'email': 'newuser@example.com',
            'username': 'newuser',
            'first_name': 'New',
            'last_name': 'User',
            'password': 'newpass123',
            'confirm_password': 'differentpass',
        })
        self.assertEqual(response.status_code, 200)
    
    def test_login_get(self):
        """Test login page loads."""
        response = self.client.get(self.login_url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'users/login.html')
    
    def test_login_success(self):
        """Test successful login."""
        response = self.client.post(self.login_url, {
            'email': 'test@example.com',
            'password': 'testpass123',
        })
        self.assertEqual(response.status_code, 302)
    
    def test_login_invalid_credentials(self):
        """Test login with invalid credentials."""
        response = self.client.post(self.login_url, {
            'email': 'test@example.com',
            'password': 'wrongpass',
        })
        self.assertEqual(response.status_code, 200)
    
    def test_logout(self):
        """Test logout."""
        self.client.post(self.login_url, {
            'email': 'test@example.com',
            'password': 'testpass123',
        })
        response = self.client.post(self.logout_url)
        self.assertEqual(response.status_code, 302)
