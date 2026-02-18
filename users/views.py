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
import jwt
import os

from users.mongo_models import User as MongoUser
from users.models import DjangoUser
from users.forms import UserRegistrationForm, UserLoginForm, UserProfileForm


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
            mongo_user = MongoUser.objects(email=email).first()
            if mongo_user:
                token = generate_token(mongo_user)
                reset_url = f"{settings.SITE_URL}/accounts/password/reset/confirm/{token}/"
                
                send_mail(
                    subject=f'Password Reset - {settings.SITE_NAME}',
                    message=f'''
Hello {mongo_user.first_name or mongo_user.username},

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
            
            mongo_user = MongoUser.objects(id=user_id).first()
            if not mongo_user:
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
            
            mongo_user = MongoUser.objects(id=user_id).first()
            if not mongo_user:
                messages.error(request, 'Invalid reset link.')
                return redirect('password_reset')
            
            password = request.POST.get('password', '')
            confirm_password = request.POST.get('confirm_password', '')
            
            if not password or len(password) < 8:
                messages.error(request, 'Password must be at least 8 characters.')
                return render(request, self.template_name, {'token': token, 'valid': True})
            
            if password != confirm_password:
                messages.error(request, 'Passwords do not match.')
                return render(request, self.template_name, {'token': token, 'valid': True})
            
            mongo_user.set_password(password)
            mongo_user.save()
            
            try:
                django_user = DjangoUser.objects.get(email=mongo_user.email)
                django_user.set_password(password)
                django_user.save()
            except DjangoUser.DoesNotExist:
                pass
            
            messages.success(request, 'Your password has been reset successfully. Please login.')
            return redirect('password_reset_complete')
            
        except jwt.ExpiredSignatureError:
            messages.error(request, 'Reset link has expired. Please request a new one.')
            return redirect('password_reset')
        except jwt.InvalidTokenError:
            messages.error(request, 'Invalid reset link.')
            return redirect('password_reset')


class PasswordResetCompleteView(View):
    """Password reset complete view."""
    
    template_name = 'users/password_reset_complete.html'
    
    def get(self, request):
        return render(request, self.template_name)


def generate_token(user):
    """Generate JWT token for user."""
    payload = {
        'user_id': str(user.id),
        'email': user.email,
        'username': user.username,
        'exp': datetime.utcnow() + timedelta(minutes=settings.JWT_ACCESS_TOKEN_LIFETIME),
        'iat': datetime.utcnow()
    }
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def sync_users(email, username, first_name='', last_name='', password=None, is_active=True):
    """Sync Django user with MongoDB user."""
    # Create or get Django user
    django_user, created = DjangoUser.objects.get_or_create(
        email=email,
        defaults={
            'username': username,
            'first_name': first_name,
            'last_name': last_name,
        }
    )
    
    if password:
        django_user.set_password(password)
        django_user.save()
    
    # Create or get MongoDB user
    mongo_user = MongoUser.objects(email=email).first()
    if not mongo_user:
        mongo_user = MongoUser(
            email=email,
            username=username,
            first_name=first_name,
            last_name=last_name,
            is_active=is_active,
        )
        if password:
            mongo_user.set_password(password)
        mongo_user.save()
    
    return django_user, mongo_user


class RegisterView(View):
    """User registration view."""
    
    template_name = 'users/register.html'
    
    def get(self, request):
        if request.session.get('user_id'):
            return redirect('home')
        form = UserRegistrationForm()
        return render(request, self.template_name, {'form': form})
    
    def post(self, request):
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            # Sync both users
            django_user, mongo_user = sync_users(
                email=form.cleaned_data['email'],
                username=form.cleaned_data['username'],
                first_name=form.cleaned_data['first_name'],
                last_name=form.cleaned_data['last_name'],
                password=form.cleaned_data['password'],
            )
            
            messages.success(request, 'Registration successful! Please login.')
            return redirect('login')
        
        return render(request, self.template_name, {'form': form})


class LoginView(View):
    """User login view."""
    
    template_name = 'users/login.html'
    
    def get(self, request):
        if request.session.get('user_id'):
            return redirect('home')
        form = UserLoginForm()
        return render(request, self.template_name, {'form': form})
    
    def post(self, request):
        form = UserLoginForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email']
            password = form.cleaned_data['password']
            
            try:
                # Try Django auth first
                django_user = DjangoUser.objects.get(email=email)
                if django_user.check_password(password):
                    if not django_user.is_active:
                        messages.error(request, 'Account is disabled.')
                        return render(request, self.template_name, {'form': form})
                    
                    # Get MongoDB user for session
                    mongo_user = MongoUser.objects(email=email).first()
                    
                    # Use MongoDB user ID in session (if exists), otherwise use Django ID as fallback
                    if mongo_user:
                        request.session['user_id'] = str(mongo_user.id)
                        token = generate_token(mongo_user)
                        request.session['token'] = token
                        mongo_user.last_login = datetime.utcnow()
                        mongo_user.save()
                    else:
                        request.session['user_id'] = str(django_user.id)
                    
                    request.session['user_email'] = django_user.email
                    request.session['username'] = django_user.username
                    
                    messages.success(request, f'Welcome back, {django_user.first_name or django_user.username}!')
                    
                    # Login Django user
                    auth_login(request, django_user)
                    
                    next_url = request.GET.get('next', 'home')
                    return redirect(next_url)
                else:
                    messages.error(request, 'Invalid email or password.')
            except DjangoUser.DoesNotExist:
                # Try MongoDB user as fallback
                try:
                    mongo_user = MongoUser.objects.get(email=email)
                    if mongo_user.check_password(password):
                        if not mongo_user.is_active:
                            messages.error(request, 'Account is disabled.')
                            return render(request, self.template_name, {'form': form})
                        
                        # Create Django user
                        django_user = DjangoUser.objects.create_user(
                            email=email,
                            username=mongo_user.username,
                            password=password,
                            first_name=mongo_user.first_name,
                            last_name=mongo_user.last_name,
                        )
                        
                        request.session['user_id'] = str(mongo_user.id)
                        request.session['user_email'] = mongo_user.email
                        request.session['username'] = mongo_user.username
                        
                        token = generate_token(mongo_user)
                        request.session['token'] = token
                        
                        mongo_user.last_login = datetime.utcnow()
                        mongo_user.save()
                        
                        auth_login(request, django_user)
                        
                        messages.success(request, f'Welcome back, {mongo_user.first_name or mongo_user.username}!')
                        
                        next_url = request.GET.get('next', 'home')
                        return redirect(next_url)
                    else:
                        messages.error(request, 'Invalid email or password.')
                except MongoUser.DoesNotExist:
                    messages.error(request, 'Invalid email or password.')
        
        return render(request, self.template_name, {'form': form})


class LogoutView(View):
    """User logout view."""
    
    def get(self, request):
        auth_logout(request)
        request.session.flush()
        messages.success(request, 'You have been logged out.')
        return redirect('login')


class ProfileView(View):
    """User profile view."""
    
    template_name = 'users/profile.html'
    
    @method_decorator(login_required, name='dispatch')
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)
    
    def get(self, request):
        if not request.session.get('user_id'):
            messages.warning(request, 'Please login to view your profile.')
            return redirect('login')
        
        try:
            # Try to get by MongoDB ObjectId first
            from bson import ObjectId
            try:
                mongo_user = MongoUser.objects.get(id=ObjectId(request.session.get('user_id')))
            except:
                # Fallback: try to get by email
                user_email = request.session.get('user_email')
                if user_email:
                    mongo_user = MongoUser.objects.get(email=user_email)
                else:
                    raise MongoUser.DoesNotExist()
            
            return render(request, self.template_name, {'user': mongo_user})
        except (MongoUser.DoesNotExist, Exception):
            messages.error(request, 'User not found.')
            return redirect('login')
    
    def post(self, request):
        if not request.session.get('user_id'):
            return redirect('login')
        
        try:
            from bson import ObjectId
            try:
                mongo_user = MongoUser.objects.get(id=ObjectId(request.session.get('user_id')))
            except:
                user_email = request.session.get('user_email')
                if user_email:
                    mongo_user = MongoUser.objects.get(email=user_email)
                else:
                    raise MongoUser.DoesNotExist()
            form = UserProfileForm(request.POST)
            
            if form.is_valid():
                mongo_user.first_name = form.cleaned_data['first_name']
                mongo_user.last_name = form.cleaned_data['last_name']
                mongo_user.phone = form.cleaned_data['phone']
                mongo_user.save()
                
                # Update Django user too
                try:
                    django_user = DjangoUser.objects.get(email=mongo_user.email)
                    django_user.first_name = form.cleaned_data['first_name']
                    django_user.last_name = form.cleaned_data['last_name']
                    django_user.save()
                except DjangoUser.DoesNotExist:
                    pass
                
                messages.success(request, 'Profile updated successfully!')
            
            return render(request, self.template_name, {'user': mongo_user, 'form': form})
        except MongoUser.DoesNotExist:
            messages.error(request, 'User not found.')
            return redirect('login')
