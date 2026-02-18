from datetime import datetime, timedelta
from django.shortcuts import render, redirect
from django.contrib import messages
from django.views import View
from django.contrib.auth import login as auth_login, logout as auth_logout
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.core.mail import send_mail
from django.conf import settings
from django.utils.crypto import get_random_string
from django.views.decorators.csrf import csrf_protect
from django.utils.decorators import method_decorator
from django.http import JsonResponse
import jwt
import os
import logging
import re

from users.models import User
from users.forms import UserRegistrationForm, UserLoginForm, UserProfileForm

logger = logging.getLogger(__name__)


def is_safe_url(url, allowed_hosts=None):
    """Validate that URL is safe for redirect."""
    if not url:
        return False
    # Only allow relative URLs or same-domain URLs
    if url.startswith('/') and not url.startswith('//'):
        return True
    return False


def generate_token(user):
    """Generate JWT token for password reset."""
    payload = {
        'user_id': str(user.id),
        'email': user.email,
        'exp': datetime.utcnow() + timedelta(hours=1),
        'iat': datetime.utcnow()
    }
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


class PasswordResetView(View):
    """Password reset request view."""
    
    template_name = 'users/password_reset.html'
    
    def get(self, request):
        return render(request, self.template_name)
    
    def post(self, request):
        email = request.POST.get('email', '').strip()
        
        if not email:
            messages.error(request, 'Please enter your email address.')
            return render(request, self.template_name)
        
        try:
            user = User.objects.filter(email=email).first()
            if user:
                token = generate_token(user)
                reset_url = f"{settings.SITE_URL}/accounts/password/reset/confirm/{token}/"
                
                send_mail(
                    subject=f'Password Reset - {settings.SITE_NAME}',
                    message=f'''
Hello {user.first_name or user.username},

You requested a password reset for your account.

Click the link below to reset your password:
{reset_url}

This link will expire in 1 hour.

If you didn't request this, please ignore this email.

Thanks,
{settings.SITE_NAME} Team
''',
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[email],
                    fail_silently=True,
                )
            
            messages.success(request, 'If an account exists with that email, you will receive a password reset link.')
            return redirect('password_reset_done')
            
        except Exception as e:
            logger.error(f"Password reset error: {e}", exc_info=True)
            messages.error(request, 'An error occurred. Please try again.')
            return render(request, self.template_name)


class PasswordResetDoneView(View):
    """Password reset email sent confirmation."""
    
    template_name = 'users/password_reset_done.html'
    
    def get(self, request):
        return render(request, self.template_name)


class PasswordResetConfirmView(View):
    """Password reset confirmation view."""
    
    template_name = 'users/password_reset_confirm.html'
    
    def get(self, request, token):
        try:
            payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
            user_id = payload.get('user_id')
            
            try:
                user = User.objects.get(id=user_id)
            except User.DoesNotExist:
                messages.error(request, 'Invalid reset link.')
                return redirect('password_reset')
            
            return render(request, self.template_name, {'token': token, 'valid': True})
            
        except jwt.ExpiredSignatureError:
            messages.error(request, 'Reset link has expired. Please request a new one.')
            return redirect('password_reset')
        except jwt.InvalidTokenError:
            messages.error(request, 'Invalid reset link.')
            return redirect('password_reset')
    
    def post(self, request, token):
        try:
            payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
            user_id = payload.get('user_id')
            
            try:
                user = User.objects.get(id=user_id)
            except User.DoesNotExist:
                messages.error(request, 'Invalid reset link.')
                return redirect('password_reset')
            
            password = request.POST.get('password', '').strip()
            password_confirm = request.POST.get('password_confirm', '').strip()
            
            if not password or len(password) < 8:
                messages.error(request, 'Password must be at least 8 characters.')
                return render(request, self.template_name, {'token': token, 'valid': True})
            
            if password != password_confirm:
                messages.error(request, 'Passwords do not match.')
                return render(request, self.template_name, {'token': token, 'valid': True})
            
            user.set_password(password)
            user.save()
            
            messages.success(request, 'Password reset successful. Please login with your new password.')
            return redirect('login')
            
        except jwt.ExpiredSignatureError:
            messages.error(request, 'Reset link has expired.')
            return redirect('password_reset')
        except jwt.InvalidTokenError:
            messages.error(request, 'Invalid reset link.')
            return redirect('password_reset')


class PasswordResetCompleteView(View):
    """Password reset complete view."""
    
    template_name = 'users/password_reset_complete.html'
    
    def get(self, request):
        return render(request, self.template_name)


class LoginView(View):
    """User login view."""
    
    template_name = 'users/login.html'
    
    def get(self, request):
        if request.user.is_authenticated:
            return redirect('home')
        form = UserLoginForm()
        return render(request, self.template_name, {'form': form})
    
    def post(self, request):
        form = UserLoginForm(request.POST)
        
        if form.is_valid():
            email = form.cleaned_data.get('email')
            password = form.cleaned_data.get('password')
            
            try:
                user = User.objects.get(email=email)
                if user.check_password(password):
                    if user.is_active:
                        # Regenerate session to prevent session fixation
                        old_session = request.session.get('cart', [])
                        request.session.cycle_key()
                        if old_session:
                            request.session['cart'] = old_session
                            request.session.modified = True
                        
                        auth_login(request, user)
                        messages.success(request, f'Welcome back, {user.first_name or user.username}!')
                        
                        # Safe redirect validation
                        next_url = request.GET.get('next')
                        if next_url and is_safe_url(next_url):
                            return redirect(next_url)
                        return redirect('home')
                    else:
                        messages.error(request, 'Your account is disabled.')
                else:
                    messages.error(request, 'Invalid email or password.')
            except User.DoesNotExist:
                messages.error(request, 'Invalid email or password.')
        
        return render(request, self.template_name, {'form': form})


class RegisterView(View):
    """User registration view."""
    
    template_name = 'users/signup.html'
    
    def get(self, request):
        if request.user.is_authenticated:
            return redirect('home')
        form = UserRegistrationForm()
        return render(request, self.template_name, {'form': form})
    
    def post(self, request):
        form = UserRegistrationForm(request.POST)
        
        if form.is_valid():
            try:
                user = User.objects.create_user(
                    email=form.cleaned_data.get('email'),
                    username=form.cleaned_data.get('username'),
                    password=form.cleaned_data.get('password'),
                    first_name=form.cleaned_data.get('first_name', ''),
                    last_name=form.cleaned_data.get('last_name', '')
                )
                
                auth_login(request, user)
                messages.success(request, 'Account created successfully!')
                return redirect('home')
                
            except Exception as e:
                logger.error(f"Registration error: {e}", exc_info=True)
                messages.error(request, 'An error occurred. Please try again.')
        
        return render(request, self.template_name, {'form': form})


@method_decorator(csrf_protect, name='dispatch')
class LogoutView(View):
    """User logout view - POST only for security."""
    
    def post(self, request):
        # Preserve cart before logout
        cart = request.session.get('cart', [])
        
        auth_logout(request)
        
        # Restore cart for guest session
        request.session['cart'] = cart
        request.session.modified = True
        
        messages.success(request, 'You have been logged out.')
        return redirect('home')
    
    def get(self, request):
        # Redirect GET requests to home with message
        messages.warning(request, 'Please use the logout button to log out.')
        return redirect('home')


@method_decorator(login_required, name='dispatch')
class ProfileView(View):
    """User profile view."""
    
    template_name = 'users/profile.html'
    
    def get(self, request):
        form = UserProfileForm(user=request.user)
        return render(request, self.template_name, {'form': form})
    
    def post(self, request):
        form = UserProfileForm(request.POST, user=request.user)
        
        if form.is_valid():
            form.save()
            messages.success(request, 'Profile updated successfully!')
            return redirect('profile')
        
        return render(request, self.template_name, {'form': form})


@method_decorator(login_required, name='dispatch')
class OrderHistoryView(View):
    """User order history view."""
    
    template_name = 'users/order_history.html'
    
    def get(self, request):
        from orders.models import Order
        orders = Order.objects.filter(user_id=str(request.user.id)).order_by('-created_at')
        return render(request, self.template_name, {'orders': orders})
