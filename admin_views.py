from django.shortcuts import render, redirect
from django.views import View
from django.contrib import messages
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required, user_passes_test
from django.utils.decorators import method_decorator
from django.core.paginator import Paginator
from django.core.exceptions import PermissionDenied, ValidationError
from django.conf import settings
from django.db import models
from datetime import datetime, timedelta
from django.utils import timezone
import json
import logging
import os
import uuid
import re

from users.models import User
from products.models import Product, Category, ProductImage
from orders.models import Order
from offers.models import Coupon, LimitedOffer, ProductReview, CouponUsage

logger = logging.getLogger(__name__)

# Valid status choices
VALID_ORDER_STATUSES = ['pending', 'processing', 'shipped', 'delivered', 'cancelled', 'refunded']
VALID_PRODUCT_STATUSES = ['active', 'draft', 'archived']

# Allowed image extensions
ALLOWED_IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.gif', '.webp'}
MAX_IMAGE_SIZE = 5 * 1024 * 1024  # 5MB


def is_staff_user(user):
    """Check if user is staff."""
    return user.is_authenticated and (user.is_staff or user.is_superuser)


def is_superuser(user):
    """Check if user is superuser."""
    return user.is_authenticated and user.is_superuser


def log_admin_action(request, action, model, object_id=None, changes=None):
    """Log admin actions for audit trail."""
    try:
        from users.models import AdminAuditLog
        
        AdminAuditLog.objects.create(
            user_id=str(request.user.id),
            user_email=request.user.email,
            action=action,
            model=model,
            object_id=str(object_id) if object_id else None,
            changes=changes or {},
            ip_address=request.META.get('REMOTE_ADDR', '')
        )
    except Exception as e:
        logger.error(f"Failed to log admin action: {e}")


class AdminDashboardView(View):
    """Admin dashboard view - with optimized aggregations."""
    
    template_name = 'admin/dashboard.html'
    
    @method_decorator(login_required)
    @method_decorator(user_passes_test(is_staff_user, login_url='/accounts/login/'))
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)
    
    def get(self, request):
        total_users = User.objects.count()
        total_products = Product.objects.count()
        total_orders = Order.objects.count()
        
        # Optimized revenue calculation using aggregation
        revenue_result = Order.objects.aggregate(total=models.Sum('total'))
        total_revenue = revenue_result['total'] or 0
        
        recent_orders = Order.objects.order_by('-created_at')[:5]
        low_stock = Product.objects.filter(track_inventory=True, stock_quantity__lte=10)[:5]
        
        context = {
            'total_users': total_users,
            'total_products': total_products,
            'total_orders': total_orders,
            'total_revenue': total_revenue,
            'recent_orders': recent_orders,
            'low_stock': low_stock,
        }
        return render(request, self.template_name, context)


class AdminUserListView(View):
    """List all users - with pagination."""
    
    template_name = 'admin/users/list.html'
    
    @method_decorator(login_required)
    @method_decorator(user_passes_test(is_staff_user, login_url='/accounts/login/'))
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)
    
    def get(self, request):
        users_list = User.objects.order_by('-date_joined')
        
        paginator = Paginator(users_list, 50)
        page = request.GET.get('page', 1)
        users = paginator.get_page(page)
        
        return render(request, self.template_name, {'users': users})


class AdminUserCreateView(View):
    """Create new user - with privilege escalation protection."""
    
    template_name = 'admin/users/edit.html'
    
    @method_decorator(login_required)
    @method_decorator(user_passes_test(is_staff_user, login_url='/accounts/login/'))
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)
    
    def get(self, request):
        return render(request, self.template_name, {'user': None, 'action': 'Create'})
    
    def post(self, request):
        try:
            email = request.POST.get('email', '').strip().lower()
            username = request.POST.get('username', '').strip()
            password = request.POST.get('password', '').strip()
            
            if not email or not username or not password:
                messages.error(request, 'Email, username, and password are required')
                return render(request, self.template_name, {'user': None, 'action': 'Create'})
            
            # Email format validation
            email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
            if not re.match(email_pattern, email):
                messages.error(request, 'Invalid email format')
                return render(request, self.template_name, {'user': None, 'action': 'Create'})
            
            # Password strength validation
            if len(password) < 8:
                messages.error(request, 'Password must be at least 8 characters long')
                return render(request, self.template_name, {'user': None, 'action': 'Create'})
            
            # Check for existing users
            if User.objects.filter(email=email).exists():
                messages.error(request, 'Email already registered')
                return render(request, self.template_name, {'user': None, 'action': 'Create'})
            
            if User.objects.filter(username=username).exists():
                messages.error(request, 'Username already taken')
                return render(request, self.template_name, {'user': None, 'action': 'Create'})
            
            # PRIVILEGE ESCALATION PROTECTION
            is_staff = request.POST.get('is_staff') == 'on'
            is_superuser = request.POST.get('is_superuser') == 'on'
            
            # Only superusers can create superusers
            if is_superuser and not request.user.is_superuser:
                raise PermissionDenied("Only superusers can create superuser accounts")
            
            # Only staff can create staff
            if is_staff and not request.user.is_staff:
                raise PermissionDenied("Only staff can create staff accounts")
            
            # Create user
            user = User.objects.create_user(
                email=email,
                username=username,
                password=password,
                first_name=request.POST.get('first_name', '')[:50],
                last_name=request.POST.get('last_name', '')[:50],
                phone=request.POST.get('phone', '')[:20],
                is_active=request.POST.get('is_active') == 'on',
                is_staff=is_staff,
                is_superuser=is_superuser,
            )
            
            # Log the action
            log_admin_action(request, 'CREATE', 'User', str(user.id), {
                'email': email,
                'is_staff': is_staff,
                'is_superuser': is_superuser
            })
            
            messages.success(request, 'User created successfully')
            return redirect('admin_users')
            
        except PermissionDenied as e:
            messages.error(request, str(e))
            return render(request, self.template_name, {'user': None, 'action': 'Create'})
        except Exception as e:
            logger.error(f"User creation failed: {e}", exc_info=True)
            messages.error(request, 'An error occurred while creating the user')
            return render(request, self.template_name, {'user': None, 'action': 'Create'})


class AdminUserEditView(View):
    """Edit user - with privilege escalation protection."""
    
    template_name = 'admin/users/edit.html'
    
    @method_decorator(login_required)
    @method_decorator(user_passes_test(is_staff_user, login_url='/accounts/login/'))
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)
    
    def get(self, request, user_id):
        try:
            user = User.objects.get(id=user_id)
            return render(request, self.template_name, {'user': user, 'action': 'Edit'})
        except User.DoesNotExist:
            messages.error(request, 'User not found')
            return redirect('admin_users')
    
    def post(self, request, user_id):
        try:
            user = User.objects.get(id=user_id)
            
            # PRIVILEGE ESCALATION PROTECTION
            # Users cannot modify their own admin status
            if str(user.id) == str(request.user.id):
                is_staff = user.is_staff
                is_superuser = user.is_superuser
            else:
                is_staff = request.POST.get('is_staff') == 'on'
                is_superuser = request.POST.get('is_superuser') == 'on'
                
                # Only superusers can create/modify superusers
                if is_superuser and not request.user.is_superuser:
                    raise PermissionDenied("Only superusers can assign superuser privileges")
            
            # Track changes for audit log
            changes = {
                'first_name': {'old': user.first_name, 'new': request.POST.get('first_name', '')[:50]},
                'last_name': {'old': user.last_name, 'new': request.POST.get('last_name', '')[:50]},
                'is_active': {'old': user.is_active, 'new': request.POST.get('is_active') == 'on'},
            }
            
            user.first_name = request.POST.get('first_name', '')[:50]
            user.last_name = request.POST.get('last_name', '')[:50]
            user.phone = request.POST.get('phone', '')[:20]
            user.is_active = request.POST.get('is_active') == 'on'
            user.is_staff = is_staff
            user.is_superuser = is_superuser
            
            new_password = request.POST.get('password', '').strip()
            if new_password:
                if len(new_password) < 8:
                    messages.error(request, 'Password must be at least 8 characters long')
                    return redirect('admin_users')
                user.set_password(new_password)
                changes['password'] = {'old': '***', 'new': '***'}
            
            user.save()
            
            # Log the action
            log_admin_action(request, 'UPDATE', 'User', str(user.id), changes)
            
            messages.success(request, 'User updated successfully')
            return redirect('admin_users')
            
        except PermissionDenied as e:
            messages.error(request, str(e))
            return redirect('admin_users')
        except User.DoesNotExist:
            messages.error(request, 'User not found')
            return redirect('admin_users')
        except Exception as e:
            logger.error(f"User update failed: {e}", exc_info=True)
            messages.error(request, 'An error occurred while updating the user')
            return redirect('admin_users')


class AdminUserDeleteView(View):
    """Delete user - with protection against self-deletion and audit logging."""
    
    @method_decorator(login_required)
    @method_decorator(user_passes_test(is_staff_user, login_url='/accounts/login/'))
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)
    
    def post(self, request, user_id):
        try:
            user = User.objects.get(id=user_id)
            
            # Prevent self-deletion
            if str(user.id) == str(request.user.id):
                messages.error(request, 'You cannot delete your own account')
                return redirect('admin_users')
            
            # Only superusers can delete superusers
            if user.is_superuser and not request.user.is_superuser:
                raise PermissionDenied("Only superusers can delete superuser accounts")
            
            email = user.email
            user.delete()
            
            # Log the action
            log_admin_action(request, 'DELETE', 'User', str(user_id), {'email': email})
            
            messages.success(request, 'User deleted successfully')
        except PermissionDenied as e:
            messages.error(request, str(e))
        except User.DoesNotExist:
            messages.error(request, 'User not found')
        except Exception as e:
            logger.error(f"User deletion failed: {e}", exc_info=True)
            messages.error(request, 'An error occurred while deleting the user')
        
        return redirect('admin_users')


class AdminProductListView(View):
    """List all products - with pagination."""
    
    template_name = 'admin/products/list.html'
    
    @method_decorator(login_required)
    @method_decorator(user_passes_test(is_staff_user, login_url='/accounts/login/'))
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)
    
    def get(self, request):
        products_list = Product.objects.select_related('category').order_by('-created_at')
        
        paginator = Paginator(products_list, 50)
        page = request.GET.get('page', 1)
        products = paginator.get_page(page)
        
        return render(request, self.template_name, {'products': products})


class AdminProductCreateView(View):
    """Create new product."""

    template_name = 'admin/products/form.html'

    @method_decorator(login_required)
    @method_decorator(user_passes_test(is_staff_user, login_url='/accounts/login/'))
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)

    def get(self, request):
        categories = Category.objects.filter(is_active=True)
        return render(request, self.template_name, {'product': None, 'action': 'Create', 'categories': categories})

    def post(self, request):
        try:
            name = request.POST.get('name', '').strip()
            slug = request.POST.get('slug', '').strip()
            sku = request.POST.get('sku', '').strip()

            if not name or not slug or not sku:
                messages.error(request, 'Name, slug, and SKU are required')
                categories = Category.objects.filter(is_active=True)
                return render(request, self.template_name, {'product': None, 'action': 'Create', 'categories': categories})

            # Check for duplicates
            if Product.objects.filter(sku=sku).exists():
                messages.error(request, 'SKU already exists')
                categories = Category.objects.filter(is_active=True)
                return render(request, self.template_name, {'product': None, 'action': 'Create', 'categories': categories})

            if Product.objects.filter(slug=slug).exists():
                messages.error(request, 'Slug already exists')
                categories = Category.objects.filter(is_active=True)
                return render(request, self.template_name, {'product': None, 'action': 'Create', 'categories': categories})

            # Get category
            category = None
            category_id = request.POST.get('category')
            if category_id:
                try:
                    category = Category.objects.get(id=int(category_id))
                except (ValueError, Category.DoesNotExist):
                    pass

            # Parse price
            MAX_PRICE = 999999999999.99  # max for DecimalField(max_digits=12, decimal_places=2)
            try:
                price = float(request.POST.get('price', 0))
                if price < 0:
                    raise ValueError("Price cannot be negative")
                if price > MAX_PRICE:
                    raise ValueError(f"Price cannot exceed {MAX_PRICE:,.2f}")
            except ValueError as e:
                messages.error(request, f'Invalid price: {str(e)}')
                categories = Category.objects.filter(is_active=True)
                return render(request, self.template_name, {'product': None, 'action': 'Create', 'categories': categories})

            # Parse compare_price
            compare_price = None
            if request.POST.get('compare_price'):
                try:
                    compare_price = float(request.POST.get('compare_price', 0))
                    if compare_price > MAX_PRICE:
                        raise ValueError(f"Compare price cannot exceed {MAX_PRICE:,.2f}")
                except ValueError as e:
                    messages.error(request, f'Invalid compare price: {str(e)}')
                    categories = Category.objects.filter(is_active=True)
                    return render(request, self.template_name, {'product': None, 'action': 'Create', 'categories': categories})

            product = Product.objects.create(
                name=name[:255],
                slug=slug[:255],
                sku=sku[:100],
                description=request.POST.get('description', ''),
                short_description=request.POST.get('short_description', '')[:500],
                price=price,
                compare_price=compare_price,
                category=category,
                tags=[t.strip()[:50] for t in request.POST.get('tags', '').split(',') if t.strip()][:20],
                stock_quantity=max(0, int(request.POST.get('stock_quantity', 0))),
                track_inventory=request.POST.get('track_inventory') == 'on',
                is_active=request.POST.get('is_active') == 'on',
                is_featured=request.POST.get('is_featured') == 'on',
                product_status=request.POST.get('product_status', 'active'),
            )

            # Handle images - first image is primary by default
            new_images = request.FILES.getlist('images')
            if new_images:
                for i, image_file in enumerate(new_images):
                    ProductImage.objects.create(
                        product=product,
                        image=image_file,
                        alt_text=product.name,
                        is_primary=(i == 0),
                        sort_order=i
                    )

            # Log the action
            log_admin_action(request, 'CREATE', 'Product', str(product.id), {
                'name': name,
                'sku': sku,
                'images_count': len(new_images)
            })

            messages.success(request, 'Product created successfully')
            return redirect('admin_products')

        except Exception as e:
            logger.error(f"Product creation failed: {e}", exc_info=True)
            messages.error(request, 'An error occurred while creating the product')
            categories = Category.objects.filter(is_active=True)
            return render(request, self.template_name, {'product': None, 'action': 'Create', 'categories': categories})


class AdminProductEditView(View):
    """Edit product."""

    template_name = 'admin/products/form.html'

    @method_decorator(login_required)
    @method_decorator(user_passes_test(is_staff_user, login_url='/accounts/login/'))
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)

    def get(self, request, product_id):
        try:
            product = Product.objects.get(id=product_id)
            categories = Category.objects.filter(is_active=True)
            return render(request, self.template_name, {'product': product, 'action': 'Edit', 'categories': categories})
        except Product.DoesNotExist:
            messages.error(request, 'Product not found')
            return redirect('admin_products')

    def post(self, request, product_id):
        try:
            product = Product.objects.get(id=product_id)

            # Track changes
            changes = {
                'name': {'old': product.name, 'new': request.POST.get('name', '').strip()[:255]},
            }

            # Get category
            category = None
            category_id = request.POST.get('category')
            if category_id:
                try:
                    category = Category.objects.get(id=int(category_id))
                except (ValueError, Category.DoesNotExist):
                    pass

            # Parse price
            try:
                price = float(request.POST.get('price', 0))
                if price < 0:
                    raise ValueError("Price cannot be negative")
            except ValueError:
                messages.error(request, 'Invalid price')
                return redirect('admin_products')

            product.name = request.POST.get('name', '').strip()[:255]
            product.slug = request.POST.get('slug', '').strip()[:255]
            product.sku = request.POST.get('sku', '').strip()[:100]
            product.description = request.POST.get('description', '')
            product.short_description = request.POST.get('short_description', '')[:500]
            product.price = price
            product.compare_price = float(request.POST.get('compare_price', 0)) if request.POST.get('compare_price') else None
            product.category = category
            product.tags = [t.strip()[:50] for t in request.POST.get('tags', '').split(',') if t.strip()][:20]
            product.stock_quantity = max(0, int(request.POST.get('stock_quantity', 0)))
            product.track_inventory = request.POST.get('track_inventory') == 'on'
            product.is_active = request.POST.get('is_active') == 'on'
            product.is_featured = request.POST.get('is_featured') == 'on'
            product.product_status = request.POST.get('product_status', 'active')

            product.save()

            # Handle new images
            new_images = request.FILES.getlist('images')
            if new_images:
                existing_count = product.images.count()
                for i, image_file in enumerate(new_images):
                    img = ProductImage.objects.create(
                        product=product,
                        image=image_file,
                        alt_text=product.name,
                        is_primary=(existing_count == 0 and i == 0),
                        sort_order=existing_count + i
                    )

            # Log the action
            log_admin_action(request, 'UPDATE', 'Product', str(product.id), changes)

            messages.success(request, 'Product updated successfully')
            return redirect('admin_products')

        except Product.DoesNotExist:
            messages.error(request, 'Product not found')
            return redirect('admin_products')
        except Exception as e:
            logger.error(f"Product update failed: {e}", exc_info=True)
            messages.error(request, 'An error occurred while updating the product')
            return redirect('admin_products')


class AdminProductDeleteView(View):
    """Soft delete product."""
    
    @method_decorator(login_required)
    @method_decorator(user_passes_test(is_staff_user, login_url='/accounts/login/'))
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)
    
    def post(self, request, product_id):
        try:
            product = Product.objects.get(id=product_id)
            
            # Soft delete
            product.is_active = False
            product.product_status = 'archived'
            product.save()
            
            # Log the action
            log_admin_action(request, 'DELETE', 'Product', str(product.id), {
                'name': product.name,
                'sku': product.sku
            })
            
            messages.success(request, 'Product deactivated successfully')
        except Product.DoesNotExist:
            messages.error(request, 'Product not found')
        except Exception as e:
            logger.error(f"Product deletion failed: {e}", exc_info=True)
            messages.error(request, 'An error occurred while deactivating the product')
        
        return redirect('admin_products')


class AdminOrderListView(View):
    """List all orders - with pagination and status validation."""
    
    template_name = 'admin/orders/list.html'
    
    @method_decorator(login_required)
    @method_decorator(user_passes_test(is_staff_user, login_url='/accounts/login/'))
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)
    
    def get(self, request):
        status_filter = request.GET.get('status', '').lower()
        
        # Validate status filter
        if status_filter and status_filter not in VALID_ORDER_STATUSES:
            status_filter = ''
        
        if status_filter:
            orders = Order.objects.filter(order_status=status_filter).order_by('-created_at')
        else:
            orders = Order.objects.order_by('-created_at')
        
        # Paginate
        paginator = Paginator(orders, 50)
        page = request.GET.get('page', 1)
        orders_page = paginator.get_page(page)
        
        return render(request, self.template_name, {
            'orders': orders_page, 
            'status_filter': status_filter,
            'valid_statuses': VALID_ORDER_STATUSES
        })


class AdminOrderDetailView(View):
    """Order detail view."""
    
    template_name = 'admin/orders/detail.html'
    
    @method_decorator(login_required)
    @method_decorator(user_passes_test(is_staff_user, login_url='/accounts/login/'))
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)
    
    def get(self, request, order_number):
        try:
            order = Order.objects.get(order_number=order_number)
        except Order.DoesNotExist:
            messages.error(request, 'Order not found')
            return redirect('admin_orders')
        return render(request, self.template_name, {'order': order})


class AdminOrderUpdateView(View):
    """Update order status - with validation."""
    
    @method_decorator(login_required)
    @method_decorator(user_passes_test(is_staff_user, login_url='/accounts/login/'))
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)
    
    def post(self, request, order_number):
        try:
            data = json.loads(request.body)
            new_status = data.get('status', '').lower()
            
            # Validate status
            if new_status not in VALID_ORDER_STATUSES:
                return JsonResponse({'error': 'Invalid order status'}, status=400)
            
            try:
                order = Order.objects.get(order_number=order_number)
            except Order.DoesNotExist:
                return JsonResponse({'error': 'Order not found'}, status=404)
            
            old_status = order.order_status
            order.order_status = new_status
            order.save()
            
            # Log the action
            log_admin_action(request, 'UPDATE', 'Order', order_number, {
                'status': {'old': old_status, 'new': new_status}
            })
            
            return JsonResponse({'success': True, 'message': 'Order updated'})
        except json.JSONDecodeError:
            return JsonResponse({'error': 'Invalid JSON'}, status=400)
        except Exception as e:
            logger.error(f"Order update failed: {e}", exc_info=True)
            return JsonResponse({'error': 'An error occurred'}, status=500)


class AdminCouponListView(View):
    """List all coupons - with pagination."""
    
    template_name = 'admin/coupons/list.html'
    
    @method_decorator(login_required)
    @method_decorator(user_passes_test(is_staff_user, login_url='/accounts/login/'))
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)
    
    def get(self, request):
        coupons = Coupon.objects.order_by('-created_at')
        
        paginator = Paginator(coupons, 50)
        page = request.GET.get('page', 1)
        coupons_page = paginator.get_page(page)
        
        return render(request, self.template_name, {'coupons': coupons_page})


class AdminCouponCreateView(View):
    """Create new coupon."""
    
    template_name = 'admin/coupons/form.html'
    
    @method_decorator(login_required)
    @method_decorator(user_passes_test(is_staff_user, login_url='/accounts/login/'))
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)
    
    def get(self, request):
        return render(request, self.template_name, {'coupon': None, 'action': 'Create'})
    
    def post(self, request):
        try:
            code = request.POST.get('code', '').strip().upper()
            
            if not code:
                messages.error(request, 'Coupon code is required')
                return render(request, self.template_name, {'coupon': None, 'action': 'Create'})
            
            # Check for duplicate code
            if Coupon.objects.filter(code=code).exists():
                messages.error(request, 'Coupon code already exists')
                return render(request, self.template_name, {'coupon': None, 'action': 'Create'})
            
            valid_until = request.POST.get('valid_until')
            if valid_until:
                valid_until = datetime.strptime(valid_until, '%Y-%m-%dT%H:%M')
            else:
                valid_until = timezone.now() + timedelta(days=30)
            
            # Validate discount value
            try:
                discount_value = float(request.POST.get('discount_value', 0))
                if discount_value <= 0:
                    raise ValueError()
            except ValueError:
                messages.error(request, 'Invalid discount value')
                return render(request, self.template_name, {'coupon': None, 'action': 'Create'})
            
            coupon = Coupon.objects.create(
                code=code[:50],
                description=request.POST.get('description', '')[:200],
                discount_type=request.POST.get('discount_type', 'percentage'),
                discount_value=discount_value,
                min_order_value=max(0, float(request.POST.get('min_order_value', 0))),
                max_discount=max(0, float(request.POST.get('max_discount', 0))),
                usage_limit=max(0, int(request.POST.get('usage_limit', 0))),
                per_user_limit=max(1, int(request.POST.get('per_user_limit', 1))),
                valid_until=valid_until,
                is_active=request.POST.get('is_active') == 'on',
                is_first_order_only=request.POST.get('is_first_order_only') == 'on',
            )
            
            # Log the action
            log_admin_action(request, 'CREATE', 'Coupon', str(coupon.id), {'code': code})
            
            messages.success(request, 'Coupon created successfully')
            return redirect('admin_coupons')
            
        except Exception as e:
            logger.error(f"Coupon creation failed: {e}", exc_info=True)
            messages.error(request, 'An error occurred while creating the coupon')
            return render(request, self.template_name, {'coupon': None, 'action': 'Create'})


class AdminCouponEditView(View):
    """Edit coupon."""
    
    template_name = 'admin/coupons/form.html'
    
    @method_decorator(login_required)
    @method_decorator(user_passes_test(is_staff_user, login_url='/accounts/login/'))
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)
    
    def get(self, request, coupon_id):
        try:
            coupon = Coupon.objects.get(id=coupon_id)
            return render(request, self.template_name, {'coupon': coupon, 'action': 'Edit'})
        except Coupon.DoesNotExist:
            messages.error(request, 'Coupon not found')
            return redirect('admin_coupons')
    
    def post(self, request, coupon_id):
        try:
            coupon_id = int(coupon_id)
            coupon = Coupon.objects.get(id=coupon_id)
            
            valid_until = request.POST.get('valid_until')
            if valid_until:
                coupon.valid_until = datetime.strptime(valid_until, '%Y-%m-%dT%H:%M')
            
            new_code = request.POST.get('code', '').strip().upper()
            if new_code != coupon.code and Coupon.objects.filter(code=new_code).exists():
                messages.error(request, 'Coupon code already exists')
                return redirect('admin_coupons')
            
            coupon.code = new_code[:50]
            coupon.description = request.POST.get('description', '')[:200]
            coupon.discount_type = request.POST.get('discount_type', 'percentage')
            coupon.discount_value = max(0, float(request.POST.get('discount_value', 0)))
            coupon.min_order_value = max(0, float(request.POST.get('min_order_value', 0)))
            coupon.max_discount = max(0, float(request.POST.get('max_discount', 0)))
            coupon.usage_limit = max(0, int(request.POST.get('usage_limit', 0)))
            coupon.per_user_limit = max(1, int(request.POST.get('per_user_limit', 1)))
            coupon.is_active = request.POST.get('is_active') == 'on'
            coupon.is_first_order_only = request.POST.get('is_first_order_only') == 'on'
            
            coupon.save()
            
            log_admin_action(request, 'UPDATE', 'Coupon', str(coupon.id), {'code': coupon.code})
            
            messages.success(request, 'Coupon updated successfully')
            return redirect('admin_coupons')
            
        except (ValueError, Coupon.DoesNotExist):
            messages.error(request, 'Coupon not found')
            return redirect('admin_coupons')
        except Exception as e:
            logger.error(f"Coupon update failed: {e}", exc_info=True)
            messages.error(request, 'An error occurred while updating the coupon')
            return redirect('admin_coupons')


class AdminProductStatusUpdateView(View):
    """Quick update product status - with validation."""
    
    @method_decorator(login_required)
    @method_decorator(user_passes_test(is_staff_user, login_url='/accounts/login/'))
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)
    
    def post(self, request, product_id):
        try:
            product_id = int(product_id)
            product = Product.objects.get(id=product_id)
            
            data = json.loads(request.body)
            changes = {}
            
            if 'product_status' in data:
                if data['product_status'] in VALID_PRODUCT_STATUSES:
                    changes['product_status'] = {'old': product.product_status, 'new': data['product_status']}
                    product.product_status = data['product_status']
            
            if 'is_active' in data:
                changes['is_active'] = {'old': product.is_active, 'new': data['is_active']}
                product.is_active = data['is_active']
            
            if 'is_featured' in data:
                changes['is_featured'] = {'old': product.is_featured, 'new': data['is_featured']}
                product.is_featured = data['is_featured']
            
            product.save()
            
            if changes:
                log_admin_action(request, 'UPDATE', 'Product', str(product.id), changes)
            
            return JsonResponse({'success': True, 'message': 'Product status updated'})
            
        except (ValueError, Product.DoesNotExist):
            return JsonResponse({'error': 'Invalid product ID'}, status=400)
        except json.JSONDecodeError:
            return JsonResponse({'error': 'Invalid JSON'}, status=400)
        except Exception as e:
            logger.error(f"Product status update failed: {e}", exc_info=True)
            return JsonResponse({'error': 'An error occurred'}, status=500)


class AdminReviewListView(View):
    """List all reviews - with pagination."""
    
    template_name = 'admin/reviews/list.html'
    
    @method_decorator(login_required)
    @method_decorator(user_passes_test(is_staff_user, login_url='/accounts/login/'))
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)
    
    def get(self, request):
        reviews_list = ProductReview.objects.order_by('-created_at')
        
        paginator = Paginator(reviews_list, 50)
        page = request.GET.get('page', 1)
        reviews = paginator.get_page(page)
        
        return render(request, self.template_name, {'reviews': reviews})


class AdminReviewApproveView(View):
    """Approve or reject a review - with validation."""
    
    @method_decorator(login_required)
    @method_decorator(user_passes_test(is_staff_user, login_url='/accounts/login/'))
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)
    
    def post(self, request, review_id):
        try:
            review_id = int(review_id)
            review = ProductReview.objects.get(id=review_id)
            old_status = review.is_approved
            review.is_approved = not review.is_approved
            review.save()
            
            log_admin_action(request, 'UPDATE', 'ProductReview', str(review.id), {
                'is_approved': {'old': old_status, 'new': review.is_approved}
            })
            
            return JsonResponse({'success': True, 'is_approved': review.is_approved})
        except (ValueError, ProductReview.DoesNotExist):
            return JsonResponse({'error': 'Invalid review ID'}, status=404)
        except Exception as e:
            logger.error(f"Review approval failed: {e}", exc_info=True)
            return JsonResponse({'error': 'An error occurred'}, status=500)


class AdminOfferListView(View):
    """List all limited time offers - with pagination."""
    
    template_name = 'admin/offers/list.html'
    
    @method_decorator(login_required)
    @method_decorator(user_passes_test(is_staff_user, login_url='/accounts/login/'))
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)
    
    def get(self, request):
        offers_list = LimitedOffer.objects.order_by('-created_at')
        
        paginator = Paginator(offers_list, 50)
        page = request.GET.get('page', 1)
        offers = paginator.get_page(page)
        
        return render(request, self.template_name, {'offers': offers})


class AdminOfferCreateView(View):
    """Create new offer."""
    
    template_name = 'admin/offers/form.html'
    
    @method_decorator(login_required)
    @method_decorator(user_passes_test(is_staff_user, login_url='/accounts/login/'))
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)
    
    def get(self, request):
        products = Product.objects.filter(is_active=True)[:50]
        return render(request, self.template_name, {'offer': None, 'action': 'Create', 'products': products})
    
    def post(self, request):
        try:
            name = request.POST.get('name', '').strip()
            if not name:
                messages.error(request, 'Offer name is required')
                return redirect('admin_offers')
            
            starts_at = request.POST.get('starts_at')
            ends_at = request.POST.get('ends_at')
            
            if starts_at:
                starts_at = datetime.strptime(starts_at, '%Y-%m-%dT%H:%M')
            else:
                starts_at = timezone.now()
            
            if ends_at:
                ends_at = datetime.strptime(ends_at, '%Y-%m-%dT%H:%M')
            else:
                ends_at = timezone.now() + timedelta(days=7)
            
            if ends_at <= starts_at:
                messages.error(request, 'End date must be after start date')
                return redirect('admin_offers')
            
            product_ids = request.POST.getlist('product_ids')
            
            offer = LimitedOffer.objects.create(
                name=name[:100],
                slug=request.POST.get('slug', '')[:100] or f"offer-{uuid.uuid4().hex[:8]}",
                description=request.POST.get('description', '')[:500],
                offer_type=request.POST.get('offer_type', 'flash_sale'),
                product_ids=product_ids[:100],
                discount_type=request.POST.get('discount_type', 'percentage'),
                discount_value=max(0, float(request.POST.get('discount_value', 0))),
                starts_at=starts_at,
                ends_at=ends_at,
                banner_text=request.POST.get('banner_text', '')[:100],
                is_active=request.POST.get('is_active') == 'on',
                show_countdown=request.POST.get('show_countdown') == 'on',
            )
            
            log_admin_action(request, 'CREATE', 'LimitedOffer', str(offer.id), {'name': name})
            
            messages.success(request, 'Offer created successfully')
            return redirect('admin_offers')
            
        except Exception as e:
            logger.error(f"Offer creation failed: {e}", exc_info=True)
            messages.error(request, 'An error occurred while creating the offer')
            return redirect('admin_offers')


class AdminOfferEditView(View):
    """Edit offer."""
    
    template_name = 'admin/offers/form.html'
    
    @method_decorator(login_required)
    @method_decorator(user_passes_test(is_staff_user, login_url='/accounts/login/'))
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)
    
    def get(self, request, offer_id):
        try:
            offer_id = int(offer_id)
            offer = LimitedOffer.objects.get(id=offer_id)
            products = Product.objects.filter(is_active=True)[:50]
            return render(request, self.template_name, {'offer': offer, 'action': 'Edit', 'products': products})
        except (ValueError, LimitedOffer.DoesNotExist):
            messages.error(request, 'Offer not found')
            return redirect('admin_offers')
    
    def post(self, request, offer_id):
        try:
            offer_id = int(offer_id)
            offer = LimitedOffer.objects.get(id=offer_id)
            
            starts_at = request.POST.get('starts_at')
            ends_at = request.POST.get('ends_at')
            
            if starts_at:
                offer.starts_at = datetime.strptime(starts_at, '%Y-%m-%dT%H:%M')
            if ends_at:
                offer.ends_at = datetime.strptime(ends_at, '%Y-%m-%dT%H:%M')
            
            if offer.ends_at <= offer.starts_at:
                messages.error(request, 'End date must be after start date')
                return redirect('admin_offers')
            
            offer.name = request.POST.get('name', '').strip()[:100]
            if request.POST.get('slug'):
                offer.slug = request.POST.get('slug', '')[:100]
            offer.description = request.POST.get('description', '')[:500]
            offer.offer_type = request.POST.get('offer_type', 'flash_sale')
            offer.product_ids = request.POST.getlist('product_ids')[:100]
            offer.discount_type = request.POST.get('discount_type', 'percentage')
            offer.discount_value = max(0, float(request.POST.get('discount_value', 0)))
            offer.banner_text = request.POST.get('banner_text', '')[:100]
            offer.is_active = request.POST.get('is_active') == 'on'
            offer.show_countdown = request.POST.get('show_countdown') == 'on'
            
            offer.save()
            
            log_admin_action(request, 'UPDATE', 'LimitedOffer', str(offer.id), {'name': offer.name})
            
            messages.success(request, 'Offer updated successfully')
            return redirect('admin_offers')
            
        except (ValueError, LimitedOffer.DoesNotExist):
            messages.error(request, 'Offer not found')
            return redirect('admin_offers')
        except Exception as e:
            logger.error(f"Offer update failed: {e}", exc_info=True)
            messages.error(request, 'An error occurred while updating the offer')
            return redirect('admin_offers')


class AdminOfferDeleteView(View):
    """Delete offer."""
    
    @method_decorator(login_required)
    @method_decorator(user_passes_test(is_staff_user, login_url='/accounts/login/'))
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)
    
    def post(self, request, offer_id):
        try:
            offer_id = int(offer_id)
            offer = LimitedOffer.objects.get(id=offer_id)
            name = offer.name
            offer.delete()
            
            log_admin_action(request, 'DELETE', 'LimitedOffer', str(offer_id), {'name': name})
            
            messages.success(request, 'Offer deleted successfully')
        except (ValueError, LimitedOffer.DoesNotExist):
            messages.error(request, 'Offer not found')
        except Exception as e:
            logger.error(f"Offer deletion failed: {e}", exc_info=True)
            messages.error(request, 'An error occurred while deleting the offer')
        
        return redirect('admin_offers')


class AdminCouponDeleteView(View):
    """Delete coupon."""
    
    @method_decorator(login_required)
    @method_decorator(user_passes_test(is_staff_user, login_url='/accounts/login/'))
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)
    
    def post(self, request, coupon_id):
        try:
            coupon = Coupon.objects.get(id=coupon_id)
            code = coupon.code
            coupon.delete()
            
            # Log the action
            log_admin_action(request, 'DELETE', 'Coupon', str(coupon_id), {'code': code})
            
            messages.success(request, 'Coupon deleted successfully')
        except Coupon.DoesNotExist:
            messages.error(request, 'Coupon not found')
        except Exception as e:
            logger.error(f"Coupon deletion failed: {e}", exc_info=True)
            messages.error(request, 'An error occurred while deleting the coupon')
        
        return redirect('admin_coupons')


class AdminReviewExportView(View):
    """Export reviews to CSV."""
    
    @method_decorator(login_required)
    @method_decorator(user_passes_test(is_staff_user, login_url='/accounts/login/'))
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)
    
    def get(self, request):
        import csv
        from django.http import HttpResponse
        
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="reviews_export.csv"'
        
        writer = csv.writer(response)
        writer.writerow([
            'ID', 'Product ID', 'User Name', 'User Email', 'Rating',
            'Title', 'Review', 'Verified Purchase', 'Approved',
            'Helpful Count', 'Created At'
        ])
        
        reviews = ProductReview.objects.all().order_by('-created_at')
        for review in reviews:
            writer.writerow([
                review.id,
                review.product_id,
                review.user_name,
                review.user_email,
                review.rating,
                review.title,
                review.review[:500] if review.review else '',
                review.is_verified_purchase,
                review.is_approved,
                review.helpful_count,
                review.created_at.strftime('%Y-%m-%d %H:%M:%S') if review.created_at else '',
            ])
        
        log_admin_action(request, 'EXPORT', 'ProductReview', None, {'count': reviews.count()})
        
        return response


class AdminNotificationListView(View):
    """Get notifications for admin."""
    
    @method_decorator(login_required)
    @method_decorator(user_passes_test(is_staff_user, login_url='/accounts/login/'))
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)
    
    def get(self, request):
        from users.models import Notification
        
        notifications = Notification.objects.all()[:20]
        unread_count = Notification.objects.filter(is_read=False).count()
        
        data = {
            'notifications': [
                {
                    'id': n.id,
                    'title': n.title,
                    'message': n.message,
                    'type': n.notification_type,
                    'link': n.link,
                    'is_read': n.is_read,
                    'created_at': n.created_at.strftime('%Y-%m-%d %H:%M')
                }
                for n in notifications
            ],
            'unread_count': unread_count
        }
        return JsonResponse(data)


class AdminNotificationMarkReadView(View):
    """Mark notification as read."""
    
    @method_decorator(login_required)
    @method_decorator(user_passes_test(is_staff_user, login_url='/accounts/login/'))
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)
    
    def post(self, request, notification_id):
        from users.models import Notification
        
        try:
            notification = Notification.objects.get(id=notification_id)
            notification.is_read = True
            notification.save()
            return JsonResponse({'success': True})
        except Notification.DoesNotExist:
            return JsonResponse({'error': 'Notification not found'}, status=404)


class AdminNotificationMarkAllReadView(View):
    """Mark all notifications as read."""
    
    @method_decorator(login_required)
    @method_decorator(user_passes_test(is_staff_user, login_url='/accounts/login/'))
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)
    
    def post(self, request):
        from users.models import Notification
        Notification.objects.filter(is_read=False).update(is_read=True)
        return JsonResponse({'success': True})


class AdminProductImageDeleteView(View):
    """Delete a product image."""
    
    @method_decorator(login_required)
    @method_decorator(user_passes_test(is_staff_user, login_url='/accounts/login/'))
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)
    
    def post(self, request, image_id):
        try:
            image_id = int(image_id)
            image = ProductImage.objects.get(id=image_id)
            product_id = image.product.id
            was_primary = image.is_primary
            
            image.image.delete(save=False)
            image.delete()
            
            if was_primary:
                next_image = ProductImage.objects.filter(product_id=product_id).first()
                if next_image:
                    next_image.is_primary = True
                    next_image.save()
            
            log_admin_action(request, 'DELETE', 'ProductImage', str(image_id), {
                'product_id': product_id
            })
            
            return JsonResponse({'success': True, 'message': 'Image deleted'})
        except (ValueError, ProductImage.DoesNotExist):
            return JsonResponse({'error': 'Image not found'}, status=404)
        except Exception as e:
            logger.error(f"Image deletion failed: {e}", exc_info=True)
            return JsonResponse({'error': 'An error occurred'}, status=500)


class AdminProductImageSetPrimaryView(View):
    """Set a product image as primary."""
    
    @method_decorator(login_required)
    @method_decorator(user_passes_test(is_staff_user, login_url='/accounts/login/'))
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)
    
    def post(self, request, image_id):
        try:
            image_id = int(image_id)
            image = ProductImage.objects.get(id=image_id)
            
            ProductImage.objects.filter(product=image.product).update(is_primary=False)
            
            image.is_primary = True
            image.save()
            
            log_admin_action(request, 'UPDATE', 'ProductImage', str(image_id), {
                'is_primary': True
            })
            
            return JsonResponse({'success': True, 'message': 'Primary image updated'})
        except (ValueError, ProductImage.DoesNotExist):
            return JsonResponse({'error': 'Image not found'}, status=404)
        except Exception as e:
            logger.error(f"Set primary image failed: {e}", exc_info=True)
            return JsonResponse({'error': 'An error occurred'}, status=500)


class AdminSetupView(View):
    """Admin setup page for environment variables."""
    
    template_name = 'admin/setup.html'
    
    DEFAULT_SETTINGS = [
        {'key': 'SECRET_KEY', 'description': 'Django secret key for security', 'setting_type': 'password', 'category': 'security', 'is_required': True},
        {'key': 'DEBUG', 'description': 'Enable debug mode (True/False)', 'setting_type': 'boolean', 'category': 'general', 'is_required': True},
        {'key': 'ALLOWED_HOSTS', 'description': 'Comma-separated list of allowed hosts', 'setting_type': 'string', 'category': 'security', 'is_required': True},
        {'key': 'DB_NAME', 'description': 'Database name', 'setting_type': 'string', 'category': 'database', 'is_required': True},
        {'key': 'DB_USER', 'description': 'Database username', 'setting_type': 'string', 'category': 'database', 'is_required': True},
        {'key': 'DB_PASSWORD', 'description': 'Database password', 'setting_type': 'password', 'category': 'database', 'is_required': True},
        {'key': 'DB_HOST', 'description': 'Database host', 'setting_type': 'string', 'category': 'database', 'is_required': True},
        {'key': 'DB_PORT', 'description': 'Database port', 'setting_type': 'integer', 'category': 'database', 'is_required': False},
        {'key': 'REDIS_URL', 'description': 'Redis connection URL', 'setting_type': 'url', 'category': 'redis', 'is_required': False},
        {'key': 'EMAIL_HOST', 'description': 'SMTP server host', 'setting_type': 'string', 'category': 'email', 'is_required': False},
        {'key': 'EMAIL_PORT', 'description': 'SMTP server port', 'setting_type': 'integer', 'category': 'email', 'is_required': False},
        {'key': 'EMAIL_USE_TLS', 'description': 'Use TLS for email (True/False)', 'setting_type': 'boolean', 'category': 'email', 'is_required': False},
        {'key': 'EMAIL_HOST_USER', 'description': 'SMTP username', 'setting_type': 'email', 'category': 'email', 'is_required': False},
        {'key': 'EMAIL_HOST_PASSWORD', 'description': 'SMTP password', 'setting_type': 'password', 'category': 'email', 'is_required': False},
        {'key': 'RAZORPAY_KEY_ID', 'description': 'Razorpay Key ID', 'setting_type': 'string', 'category': 'payment', 'is_required': False},
        {'key': 'RAZORPAY_KEY_SECRET', 'description': 'Razorpay Key Secret', 'setting_type': 'password', 'category': 'payment', 'is_required': False},
        {'key': 'GOOGLE_CLIENT_ID', 'description': 'Google OAuth Client ID', 'setting_type': 'string', 'category': 'social', 'is_required': False},
        {'key': 'GOOGLE_CLIENT_SECRET', 'description': 'Google OAuth Client Secret', 'setting_type': 'password', 'category': 'social', 'is_required': False},
        {'key': 'CLOUDINARY_CLOUD_NAME', 'description': 'Cloudinary Cloud Name', 'setting_type': 'string', 'category': 'storage', 'is_required': False},
        {'key': 'CLOUDINARY_API_KEY', 'description': 'Cloudinary API Key', 'setting_type': 'string', 'category': 'storage', 'is_required': False},
        {'key': 'CLOUDINARY_API_SECRET', 'description': 'Cloudinary API Secret', 'setting_type': 'password', 'category': 'storage', 'is_required': False},
        {'key': 'SITE_NAME', 'description': 'Website name', 'setting_type': 'string', 'category': 'general', 'is_required': False},
        {'key': 'SITE_URL', 'description': 'Website URL', 'setting_type': 'url', 'category': 'general', 'is_required': False},
        {'key': 'JWT_SECRET_KEY', 'description': 'JWT secret key', 'setting_type': 'password', 'category': 'security', 'is_required': False},
        {'key': 'CORS_ALLOWED_ORIGINS', 'description': 'Comma-separated CORS origins', 'setting_type': 'string', 'category': 'security', 'is_required': False},
        {'key': 'CSRF_TRUSTED_ORIGINS', 'description': 'Comma-separated CSRF trusted origins', 'setting_type': 'string', 'category': 'security', 'is_required': False},
    ]
    
    @method_decorator(login_required)
    @method_decorator(user_passes_test(is_superuser, login_url='/accounts/login/'))
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)
    
    def get(self, request):
        from core.models import SiteConfiguration
        
        settings_by_category = {}
        for setting in self.DEFAULT_SETTINGS:
            category = setting['category']
            if category not in settings_by_category:
                settings_by_category[category] = []
            
            try:
                config = SiteConfiguration.objects.get(key=setting['key'])
                setting['value'] = config.value
                setting['exists'] = True
            except SiteConfiguration.DoesNotExist:
                setting['value'] = os.getenv(setting['key'], '')
                setting['exists'] = False
            
            settings_by_category[category].append(setting)
        
        context = {
            'settings_by_category': settings_by_category,
        }
        return render(request, self.template_name, context)
    
    def post(self, request):
        from core.models import SiteConfiguration
        
        updated_count = 0
        for key in request.POST:
            if key in [s['key'] for s in self.DEFAULT_SETTINGS]:
                value = request.POST.get(key, '').strip()
                setting_info = next((s for s in self.DEFAULT_SETTINGS if s['key'] == key), None)
                
                SiteConfiguration.objects.update_or_create(
                    key=key,
                    defaults={
                        'value': value,
                        'description': setting_info.get('description', '') if setting_info else '',
                        'setting_type': setting_info.get('setting_type', 'string') if setting_info else 'string',
                        'category': setting_info.get('category', 'general') if setting_info else 'general',
                        'is_secret': setting_info.get('setting_type') == 'password' if setting_info else False,
                        'is_required': setting_info.get('is_required', False) if setting_info else False,
                    }
                )
                updated_count += 1
        
        log_admin_action(request, 'UPDATE', 'SiteConfiguration', changes={'updated_count': updated_count})
        messages.success(request, f'Settings updated successfully! {updated_count} settings saved.')
        return redirect('admin_setup')


class AdminSetupTestView(View):
    """Test configuration settings."""
    
    @method_decorator(login_required)
    @method_decorator(user_passes_test(is_superuser, login_url='/accounts/login/'))
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)
    
    def post(self, request):
        from core.models import SiteConfiguration
        import smtplib
        from django.core.mail import get_connection
        
        test_type = request.POST.get('test_type')
        results = {'success': False, 'message': ''}
        
        try:
            if test_type == 'database':
                from django.db import connection
                with connection.cursor() as cursor:
                    cursor.execute('SELECT 1')
                results = {'success': True, 'message': 'Database connection successful!'}
                
            elif test_type == 'redis':
                redis_url = SiteConfiguration.get('REDIS_URL') or os.getenv('REDIS_URL', '')
                if redis_url:
                    import redis as redis_client
                    r = redis_client.from_url(redis_url)
                    r.ping()
                    results = {'success': True, 'message': 'Redis connection successful!'}
                else:
                    results = {'success': False, 'message': 'Redis URL not configured'}
                    
            elif test_type == 'email':
                email_host = SiteConfiguration.get('EMAIL_HOST') or os.getenv('EMAIL_HOST', '')
                email_port = int(SiteConfiguration.get('EMAIL_PORT') or os.getenv('EMAIL_PORT', '587'))
                email_user = SiteConfiguration.get('EMAIL_HOST_USER') or os.getenv('EMAIL_HOST_USER', '')
                email_password = SiteConfiguration.get('EMAIL_HOST_PASSWORD') or os.getenv('EMAIL_HOST_PASSWORD', '')
                email_use_tls = SiteConfiguration.get('EMAIL_USE_TLS') or os.getenv('EMAIL_USE_TLS', 'True') == 'True'
                
                if email_host and email_user:
                    with smtplib.SMTP(email_host, email_port) as server:
                        if email_use_tls:
                            server.starttls()
                        server.login(email_user, email_password)
                    results = {'success': True, 'message': 'Email connection successful!'}
                else:
                    results = {'success': False, 'message': 'Email settings not configured'}
                    
            elif test_type == 'razorpay':
                key_id = SiteConfiguration.get('RAZORPAY_KEY_ID') or os.getenv('RAZORPAY_KEY_ID', '')
                key_secret = SiteConfiguration.get('RAZORPAY_KEY_SECRET') or os.getenv('RAZORPAY_KEY_SECRET', '')
                
                if key_id and key_secret:
                    import razorpay
                    client = razorpay.Client(auth=(key_id, key_secret))
                    client.payment.all({'count': 1})
                    results = {'success': True, 'message': 'Razorpay connection successful!'}
                else:
                    results = {'success': False, 'message': 'Razorpay settings not configured'}
                    
        except Exception as e:
            results = {'success': False, 'message': f'Connection failed: {str(e)}'}
        
        return JsonResponse(results)


class AdminSetupExportView(View):
    """Export settings to .env file format."""
    
    @method_decorator(login_required)
    @method_decorator(user_passes_test(is_superuser, login_url='/accounts/login/'))
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)
    
    def get(self, request):
        from core.models import SiteConfiguration
        from django.http import HttpResponse
        
        settings = SiteConfiguration.objects.all()
        env_content = "# Environment Variables - Generated from Admin Setup\n"
        env_content += f"# Generated on {timezone.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
        
        for setting in settings:
            env_content += f"# {setting.description}\n"
            if setting.is_secret:
                env_content += f"{setting.key}=*****\n"
            else:
                env_content += f"{setting.key}={setting.value}\n"
            env_content += "\n"
        
        response = HttpResponse(env_content, content_type='text/plain')
        response['Content-Disposition'] = 'attachment; filename=".env.example"'
        return response


class AdminHeroImageView(View):
    """Manage hero images."""
    
    template_name = 'admin/hero/list.html'
    
    @method_decorator(login_required)
    @method_decorator(user_passes_test(is_staff_user, login_url='/accounts/login/'))
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)
    
    def get(self, request):
        from core.models import HeroImage
        hero_images = HeroImage.objects.all()
        return render(request, self.template_name, {'hero_images': hero_images})


class AdminHeroImageCreateView(View):
    """Create hero image."""
    
    template_name = 'admin/hero/form.html'
    
    @method_decorator(login_required)
    @method_decorator(user_passes_test(is_staff_user, login_url='/accounts/login/'))
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)
    
    def get(self, request):
        return render(request, self.template_name, {'hero_image': None, 'action': 'Create'})
    
    def post(self, request):
        from core.models import HeroImage
        
        try:
            title = request.POST.get('title', '').strip()[:100]
            subtitle = request.POST.get('subtitle', '').strip()[:200]
            button_text = request.POST.get('button_text', '').strip()[:50]
            button_link = request.POST.get('button_link', '').strip()[:255]
            sort_order = int(request.POST.get('sort_order', 0))
            is_active = request.POST.get('is_active') == 'on'
            
            if not title:
                messages.error(request, 'Title is required')
                return render(request, self.template_name, {'hero_image': None, 'action': 'Create'})
            
            if 'image' not in request.FILES:
                messages.error(request, 'Image is required')
                return render(request, self.template_name, {'hero_image': None, 'action': 'Create'})
            
            hero_image = HeroImage.objects.create(
                title=title,
                subtitle=subtitle,
                image=request.FILES['image'],
                mobile_image=request.FILES.get('mobile_image'),
                button_text=button_text,
                button_link=button_link,
                sort_order=sort_order,
                is_active=is_active
            )
            
            log_admin_action(request, 'CREATE', 'HeroImage', str(hero_image.id), {
                'title': title
            })
            
            messages.success(request, 'Hero image created successfully')
            return redirect('admin_hero_images')
            
        except Exception as e:
            logger.error(f"Hero image creation failed: {e}", exc_info=True)
            messages.error(request, f'Error: {str(e)}')
            return render(request, self.template_name, {'hero_image': None, 'action': 'Create'})


class AdminHeroImageEditView(View):
    """Edit hero image."""
    
    template_name = 'admin/hero/form.html'
    
    @method_decorator(login_required)
    @method_decorator(user_passes_test(is_staff_user, login_url='/accounts/login/'))
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)
    
    def get(self, request, hero_id):
        from core.models import HeroImage
        try:
            hero_image = HeroImage.objects.get(id=hero_id)
            return render(request, self.template_name, {'hero_image': hero_image, 'action': 'Edit'})
        except HeroImage.DoesNotExist:
            messages.error(request, 'Hero image not found')
            return redirect('admin_hero_images')
    
    def post(self, request, hero_id):
        from core.models import HeroImage
        
        try:
            hero_image = HeroImage.objects.get(id=hero_id)
            
            hero_image.title = request.POST.get('title', '').strip()[:100]
            hero_image.subtitle = request.POST.get('subtitle', '').strip()[:200]
            hero_image.button_text = request.POST.get('button_text', '').strip()[:50]
            hero_image.button_link = request.POST.get('button_link', '').strip()[:255]
            hero_image.sort_order = int(request.POST.get('sort_order', 0))
            hero_image.is_active = request.POST.get('is_active') == 'on'
            
            if 'image' in request.FILES:
                hero_image.image = request.FILES['image']
            if 'mobile_image' in request.FILES:
                hero_image.mobile_image = request.FILES['mobile_image']
            
            hero_image.save()
            
            log_admin_action(request, 'UPDATE', 'HeroImage', str(hero_image.id))
            messages.success(request, 'Hero image updated successfully')
            return redirect('admin_hero_images')
            
        except HeroImage.DoesNotExist:
            messages.error(request, 'Hero image not found')
            return redirect('admin_hero_images')
        except Exception as e:
            logger.error(f"Hero image update failed: {e}", exc_info=True)
            messages.error(request, f'Error: {str(e)}')
            return redirect('admin_hero_images')


class AdminHeroImageDeleteView(View):
    """Delete hero image."""
    
    @method_decorator(login_required)
    @method_decorator(user_passes_test(is_staff_user, login_url='/accounts/login/'))
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)
    
    def post(self, request, hero_id):
        from core.models import HeroImage
        
        try:
            hero_image = HeroImage.objects.get(id=hero_id)
            hero_image.image.delete(save=False)
            if hero_image.mobile_image:
                hero_image.mobile_image.delete(save=False)
            hero_image.delete()
            
            log_admin_action(request, 'DELETE', 'HeroImage', str(hero_id))
            return JsonResponse({'success': True})
        except HeroImage.DoesNotExist:
            return JsonResponse({'error': 'Not found'}, status=404)


class AdminSocialLinksView(View):
    """Manage social links."""
    
    template_name = 'admin/social/list.html'
    
    @method_decorator(login_required)
    @method_decorator(user_passes_test(is_staff_user, login_url='/accounts/login/'))
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)
    
    def get(self, request):
        from core.models import SocialLink
        social_links = SocialLink.objects.all()
        return render(request, self.template_name, {'social_links': social_links})
    
    def post(self, request):
        from core.models import SocialLink
        
        try:
            platform = request.POST.get('platform', '').strip()
            url = request.POST.get('url', '').strip()
            sort_order = int(request.POST.get('sort_order', 0))
            is_active = request.POST.get('is_active') == 'on'
            
            if not platform or not url:
                return JsonResponse({'error': 'Platform and URL are required'}, status=400)
            
            SocialLink.objects.update_or_create(
                platform=platform,
                defaults={
                    'url': url,
                    'sort_order': sort_order,
                    'is_active': is_active
                }
            )
            
            return JsonResponse({'success': True})
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)


class AdminSocialLinkDeleteView(View):
    """Delete social link."""
    
    @method_decorator(login_required)
    @method_decorator(user_passes_test(is_staff_user, login_url='/accounts/login/'))
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)
    
    def post(self, request, link_id):
        from core.models import SocialLink
        
        try:
            SocialLink.objects.get(id=link_id).delete()
            return JsonResponse({'success': True})
        except SocialLink.DoesNotExist:
            return JsonResponse({'error': 'Not found'}, status=404)
