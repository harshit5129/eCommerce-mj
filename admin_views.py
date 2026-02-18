from django.shortcuts import render, redirect
from django.views import View
from django.contrib import messages
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required, user_passes_test
from django.utils.decorators import method_decorator
import json
from datetime import datetime, timedelta

from users.mongo_models import User
from products.models import Product
from orders.models import Order
from offers.models import Coupon, LimitedOffer, ProductReview


def is_staff_user(user):
    """Check if user is staff."""
    return user.is_authenticated and (user.is_staff or user.is_superuser)


class AdminDashboardView(View):
    """Admin dashboard view."""
    
    template_name = 'admin/dashboard.html'
    
    @method_decorator(login_required)
    @method_decorator(user_passes_test(is_staff_user, login_url='/accounts/login/'))
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)
    
    def get(self, request):
        total_users = User.objects.count()
        total_products = Product.objects.count()
        total_orders = Order.objects.count()
        
        orders = Order.objects()
        total_revenue = sum(order.total for order in orders)
        
        recent_orders = Order.objects().order_by('-created_at')[:5]
        
        low_stock = Product.objects(track_inventory=True, stock_quantity__lte=10)[:5]
        
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
    """List all users."""
    
    template_name = 'admin/users/list.html'
    
    @method_decorator(login_required)
    @method_decorator(user_passes_test(is_staff_user, login_url='/accounts/login/'))
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)
    
    def get(self, request):
        users = User.objects().order_by('-date_joined')
        return render(request, self.template_name, {'users': users})


class AdminUserCreateView(View):
    """Create new user."""
    
    template_name = 'admin/users/edit.html'
    
    @method_decorator(login_required)
    @method_decorator(user_passes_test(is_staff_user, login_url='/accounts/login/'))
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)
    
    def get(self, request):
        return render(request, self.template_name, {'user': None, 'action': 'Create'})
    
    def post(self, request):
        from users.models import DjangoUser
        from users.mongo_models import User as MongoUser
        
        try:
            email = request.POST.get('email', '').strip()
            username = request.POST.get('username', '').strip()
            password = request.POST.get('password', '').strip()
            
            if not email or not username or not password:
                messages.error(request, 'Email, username, and password are required')
                return render(request, self.template_name, {'user': None, 'action': 'Create'})
            
            if MongoUser.objects(email=email).first():
                messages.error(request, 'Email already registered')
                return render(request, self.template_name, {'user': None, 'action': 'Create'})
            
            if MongoUser.objects(username=username).first():
                messages.error(request, 'Username already taken')
                return render(request, self.template_name, {'user': None, 'action': 'Create'})
            
            mongo_user = MongoUser(
                email=email,
                username=username,
                first_name=request.POST.get('first_name', ''),
                last_name=request.POST.get('last_name', ''),
                phone=request.POST.get('phone', ''),
                is_active=request.POST.get('is_active') == 'on',
                is_staff=request.POST.get('is_staff') == 'on',
                is_superuser=request.POST.get('is_superuser') == 'on',
            )
            mongo_user.set_password(password)
            mongo_user.save()
            
            django_user = DjangoUser.objects.create_user(
                email=email,
                username=username,
                password=password,
                first_name=request.POST.get('first_name', ''),
                last_name=request.POST.get('last_name', ''),
                is_active=request.POST.get('is_active') == 'on',
                is_staff=request.POST.get('is_staff') == 'on',
                is_superuser=request.POST.get('is_superuser') == 'on',
            )
            
            messages.success(request, 'User created successfully')
            return redirect('admin_users')
        except Exception as e:
            messages.error(request, f'Error: {str(e)}')
            return render(request, self.template_name, {'user': None, 'action': 'Create'})


class AdminUserEditView(View):
    """Edit user."""
    
    template_name = 'admin/users/edit.html'
    
    @method_decorator(login_required)
    @method_decorator(user_passes_test(is_staff_user, login_url='/accounts/login/'))
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)
    
    def get(self, request, user_id):
        from bson import ObjectId
        try:
            user = User.objects.get(id=ObjectId(user_id))
            return render(request, self.template_name, {'user': user, 'action': 'Edit'})
        except:
            messages.error(request, 'User not found')
            return redirect('admin_users')
    
    def post(self, request, user_id):
        from bson import ObjectId
        from users.models import DjangoUser
        
        try:
            user = User.objects.get(id=ObjectId(user_id))
            user.first_name = request.POST.get('first_name', '')
            user.last_name = request.POST.get('last_name', '')
            user.phone = request.POST.get('phone', '')
            user.is_active = request.POST.get('is_active') == 'on'
            user.is_staff = request.POST.get('is_staff') == 'on'
            user.is_superuser = request.POST.get('is_superuser') == 'on'
            
            new_password = request.POST.get('password', '').strip()
            if new_password:
                user.set_password(new_password)
            
            user.save()
            
            try:
                django_user = DjangoUser.objects.get(email=user.email)
                django_user.first_name = user.first_name
                django_user.last_name = user.last_name
                django_user.is_active = user.is_active
                django_user.is_staff = user.is_staff
                django_user.is_superuser = user.is_superuser
                if new_password:
                    django_user.set_password(new_password)
                django_user.save()
            except DjangoUser.DoesNotExist:
                pass
            
            messages.success(request, 'User updated successfully')
            return redirect('admin_users')
        except Exception as e:
            messages.error(request, f'Error: {str(e)}')
            return redirect('admin_users')


class AdminUserDeleteView(View):
    """Delete user."""
    
    @method_decorator(login_required)
    @method_decorator(user_passes_test(is_staff_user, login_url='/accounts/login/'))
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)
    
    def post(self, request, user_id):
        from bson import ObjectId
        try:
            user = User.objects.get(id=ObjectId(user_id))
            user.delete()
            messages.success(request, 'User deleted successfully')
        except:
            messages.error(request, 'User not found')
        return redirect('admin_users')


class AdminProductListView(View):
    """List all products."""
    
    template_name = 'admin/products/list.html'
    
    @method_decorator(login_required)
    @method_decorator(user_passes_test(is_staff_user, login_url='/accounts/login/'))
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)
    
    def get(self, request):
        products = Product.objects().order_by('-created_at')
        return render(request, self.template_name, {'products': products})


class AdminProductCreateView(View):
    """Create new product."""
    
    template_name = 'admin/products/form.html'
    
    @method_decorator(login_required)
    @method_decorator(user_passes_test(is_staff_user, login_url='/accounts/login/'))
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)
    
    def get(self, request):
        return render(request, self.template_name, {'product': None, 'action': 'Create'})
    
    def post(self, request):
        try:
            from products.models import Category, ProductImage
            
            category_data = None
            if request.POST.get('category_name'):
                category_data = Category(
                    name=request.POST.get('category_name'),
                    slug=request.POST.get('category_slug', request.POST.get('category_name', '').lower().replace(' ', '-'))
                )
            
            images = []
            for img_url in request.POST.getlist('existing_images'):
                images.append(ProductImage(
                    url=img_url,
                    alt_text=request.POST.get('name', 'Product'),
                    is_primary=False
                ))
            
            uploaded_files = request.FILES.getlist('images')
            primary_new = request.POST.get('primary_image_new')
            
            for i, img_file in enumerate(uploaded_files):
                import os
                import uuid
                from django.conf import settings
                
                ext = os.path.splitext(img_file.name)[1]
                filename = f"{uuid.uuid4()}{ext}"
                filepath = os.path.join(settings.MEDIA_ROOT, 'products', filename)
                os.makedirs(os.path.dirname(filepath), exist_ok=True)
                
                with open(filepath, 'wb+') as destination:
                    for chunk in img_file.chunks():
                        destination.write(chunk)
                
                image_url = f"{settings.MEDIA_URL}products/{filename}"
                images.append(ProductImage(
                    url=image_url,
                    alt_text=request.POST.get('name', 'Product'),
                    is_primary=(primary_new and int(primary_new) == i and len(images) == 0)
                ))
            
            primary_idx = request.POST.get('primary_image')
            if primary_idx:
                for i, img in enumerate(images):
                    img.is_primary = (str(i) == primary_idx)
            elif images:
                images[0].is_primary = True
            
            product = Product(
                name=request.POST.get('name'),
                slug=request.POST.get('slug'),
                sku=request.POST.get('sku'),
                description=request.POST.get('description', ''),
                short_description=request.POST.get('short_description', ''),
                price=float(request.POST.get('price', 0)),
                compare_price=float(request.POST.get('compare_price', 0)) if request.POST.get('compare_price') else None,
                category=category_data,
                tags=[t.strip() for t in request.POST.get('tags', '').split(',') if t.strip()],
                stock_quantity=int(request.POST.get('stock_quantity', 0)),
                track_inventory=request.POST.get('track_inventory') == 'on',
                is_active=request.POST.get('is_active') == 'on',
                is_featured=request.POST.get('is_featured') == 'on',
                product_status=request.POST.get('product_status', 'active'),
                weight=float(request.POST.get('weight', 0)) if request.POST.get('weight') else None,
                images=images,
            )
            product.save()
            messages.success(request, 'Product created successfully')
            return redirect('admin_products')
        except Exception as e:
            messages.error(request, f'Error: {str(e)}')
            return render(request, self.template_name, {'product': None, 'action': 'Create'})


class AdminProductEditView(View):
    """Edit product."""
    
    template_name = 'admin/products/form.html'
    
    @method_decorator(login_required)
    @method_decorator(user_passes_test(is_staff_user, login_url='/accounts/login/'))
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)
    
    def get(self, request, product_id):
        from bson import ObjectId
        try:
            product = Product.objects.get(id=ObjectId(product_id))
            return render(request, self.template_name, {'product': product, 'action': 'Edit'})
        except:
            messages.error(request, 'Product not found')
            return redirect('admin_products')
    
    def post(self, request, product_id):
        from bson import ObjectId
        try:
            product = Product.objects.get(id=ObjectId(product_id))
            
            from products.models import Category, ProductImage
            import os
            import uuid
            from django.conf import settings
            
            category_data = None
            if request.POST.get('category_name'):
                category_data = Category(
                    name=request.POST.get('category_name'),
                    slug=request.POST.get('category_slug', request.POST.get('category_name', '').lower().replace(' ', '-'))
                )
            
            images = []
            existing_urls = request.POST.getlist('existing_images')
            for img in product.images:
                if img.url in existing_urls:
                    images.append(img)
            
            uploaded_files = request.FILES.getlist('images')
            primary_new = request.POST.get('primary_image_new')
            
            for i, img_file in enumerate(uploaded_files):
                ext = os.path.splitext(img_file.name)[1]
                filename = f"{uuid.uuid4()}{ext}"
                filepath = os.path.join(settings.MEDIA_ROOT, 'products', filename)
                os.makedirs(os.path.dirname(filepath), exist_ok=True)
                
                with open(filepath, 'wb+') as destination:
                    for chunk in img_file.chunks():
                        destination.write(chunk)
                
                image_url = f"{settings.MEDIA_URL}products/{filename}"
                images.append(ProductImage(
                    url=image_url,
                    alt_text=request.POST.get('name', 'Product'),
                    is_primary=False
                ))
            
            primary_idx = request.POST.get('primary_image')
            if primary_idx:
                for i, img in enumerate(images):
                    img.is_primary = (str(i) == primary_idx)
            elif images and not any(img.is_primary for img in images):
                images[0].is_primary = True
            
            product.name = request.POST.get('name')
            product.slug = request.POST.get('slug')
            product.sku = request.POST.get('sku')
            product.description = request.POST.get('description', '')
            product.short_description = request.POST.get('short_description', '')
            product.price = float(request.POST.get('price', 0))
            product.compare_price = float(request.POST.get('compare_price', 0)) if request.POST.get('compare_price') else None
            product.category = category_data
            product.tags = [t.strip() for t in request.POST.get('tags', '').split(',') if t.strip()]
            product.stock_quantity = int(request.POST.get('stock_quantity', 0))
            product.track_inventory = request.POST.get('track_inventory') == 'on'
            product.is_active = request.POST.get('is_active') == 'on'
            product.is_featured = request.POST.get('is_featured') == 'on'
            product.product_status = request.POST.get('product_status', 'active')
            product.weight = float(request.POST.get('weight', 0)) if request.POST.get('weight') else None
            product.images = images
            
            product.save()
            messages.success(request, 'Product updated successfully')
            return redirect('admin_products')
        except Exception as e:
            messages.error(request, f'Error: {str(e)}')
            return redirect('admin_products')


class AdminProductDeleteView(View):
    """Delete product."""
    
    @method_decorator(login_required)
    @method_decorator(user_passes_test(is_staff_user, login_url='/accounts/login/'))
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)
    
    def post(self, request, product_id):
        from bson import ObjectId
        try:
            product = Product.objects.get(id=ObjectId(product_id))
            product.delete()
            messages.success(request, 'Product deleted successfully')
        except:
            messages.error(request, 'Product not found')
        return redirect('admin_products')


class AdminOrderListView(View):
    """List all orders."""
    
    template_name = 'admin/orders/list.html'
    
    @method_decorator(login_required)
    @method_decorator(user_passes_test(is_staff_user, login_url='/accounts/login/'))
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)
    
    def get(self, request):
        status_filter = request.GET.get('status', '')
        if status_filter:
            orders = Order.objects(order_status=status_filter).order_by('-created_at')
        else:
            orders = Order.objects().order_by('-created_at')
        return render(request, self.template_name, {'orders': orders, 'status_filter': status_filter})


class AdminOrderDetailView(View):
    """Order detail view."""
    
    template_name = 'admin/orders/detail.html'
    
    @method_decorator(login_required)
    @method_decorator(user_passes_test(is_staff_user, login_url='/accounts/login/'))
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)
    
    def get(self, request, order_number):
        order = Order.objects(order_number=order_number).first()
        if not order:
            messages.error(request, 'Order not found')
            return redirect('admin_orders')
        return render(request, self.template_name, {'order': order})


class AdminOrderUpdateView(View):
    """Update order status."""
    
    @method_decorator(login_required)
    @method_decorator(user_passes_test(is_staff_user, login_url='/accounts/login/'))
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)
    
    def post(self, request, order_number):
        try:
            data = json.loads(request.body)
            order = Order.objects(order_number=order_number).first()
            if order:
                order.order_status = data.get('status', order.order_status)
                order.save()
                return JsonResponse({'success': True, 'message': 'Order updated'})
            return JsonResponse({'error': 'Order not found'}, status=404)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)


class AdminProductStatusUpdateView(View):
    """Quick update product status."""
    
    @method_decorator(login_required)
    @method_decorator(user_passes_test(is_staff_user, login_url='/accounts/login/'))
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)
    
    def post(self, request, product_id):
        from bson import ObjectId
        try:
            data = json.loads(request.body)
            product = Product.objects.get(id=ObjectId(product_id))
            
            if 'product_status' in data:
                product.product_status = data['product_status']
            if 'is_active' in data:
                product.is_active = data['is_active']
            if 'is_featured' in data:
                product.is_featured = data['is_featured']
            
            product.save()
            return JsonResponse({'success': True, 'message': 'Product status updated'})
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)


class AdminCouponListView(View):
    """List all coupons."""
    
    template_name = 'admin/coupons/list.html'
    
    @method_decorator(login_required)
    @method_decorator(user_passes_test(is_staff_user, login_url='/accounts/login/'))
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)
    
    def get(self, request):
        coupons = Coupon.objects().order_by('-created_at')
        return render(request, self.template_name, {'coupons': coupons})


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
            from datetime import datetime
            
            valid_until = request.POST.get('valid_until')
            if valid_until:
                valid_until = datetime.strptime(valid_until, '%Y-%m-%dT%H:%M')
            else:
                valid_until = datetime.utcnow() + timedelta(days=30)
            
            coupon = Coupon(
                code=request.POST.get('code', '').upper(),
                description=request.POST.get('description', ''),
                discount_type=request.POST.get('discount_type', 'percentage'),
                discount_value=float(request.POST.get('discount_value', 0)),
                min_order_value=float(request.POST.get('min_order_value', 0)),
                max_discount=float(request.POST.get('max_discount', 0)),
                usage_limit=int(request.POST.get('usage_limit', 0)),
                per_user_limit=int(request.POST.get('per_user_limit', 1)),
                valid_until=valid_until,
                is_active=request.POST.get('is_active') == 'on',
                is_first_order_only=request.POST.get('is_first_order_only') == 'on',
            )
            coupon.save()
            messages.success(request, 'Coupon created successfully')
            return redirect('admin_coupons')
        except Exception as e:
            messages.error(request, f'Error: {str(e)}')
            return render(request, self.template_name, {'coupon': None, 'action': 'Create'})


class AdminCouponEditView(View):
    """Edit coupon."""
    
    template_name = 'admin/coupons/form.html'
    
    @method_decorator(login_required)
    @method_decorator(user_passes_test(is_staff_user, login_url='/accounts/login/'))
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)
    
    def get(self, request, coupon_id):
        from bson import ObjectId
        try:
            coupon = Coupon.objects.get(id=ObjectId(coupon_id))
            return render(request, self.template_name, {'coupon': coupon, 'action': 'Edit'})
        except:
            messages.error(request, 'Coupon not found')
            return redirect('admin_coupons')
    
    def post(self, request, coupon_id):
        from bson import ObjectId
        try:
            coupon = Coupon.objects.get(id=ObjectId(coupon_id))
            
            valid_until = request.POST.get('valid_until')
            if valid_until:
                coupon.valid_until = datetime.strptime(valid_until, '%Y-%m-%dT%H:%M')
            
            coupon.code = request.POST.get('code', '').upper()
            coupon.description = request.POST.get('description', '')
            coupon.discount_type = request.POST.get('discount_type', 'percentage')
            coupon.discount_value = float(request.POST.get('discount_value', 0))
            coupon.min_order_value = float(request.POST.get('min_order_value', 0))
            coupon.max_discount = float(request.POST.get('max_discount', 0))
            coupon.usage_limit = int(request.POST.get('usage_limit', 0))
            coupon.per_user_limit = int(request.POST.get('per_user_limit', 1))
            coupon.is_active = request.POST.get('is_active') == 'on'
            coupon.is_first_order_only = request.POST.get('is_first_order_only') == 'on'
            
            coupon.save()
            messages.success(request, 'Coupon updated successfully')
            return redirect('admin_coupons')
        except Exception as e:
            messages.error(request, f'Error: {str(e)}')
            return redirect('admin_coupons')


class AdminCouponDeleteView(View):
    """Delete coupon."""
    
    @method_decorator(login_required)
    @method_decorator(user_passes_test(is_staff_user, login_url='/accounts/login/'))
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)
    
    def post(self, request, coupon_id):
        from bson import ObjectId
        try:
            coupon = Coupon.objects.get(id=ObjectId(coupon_id))
            coupon.delete()
            messages.success(request, 'Coupon deleted successfully')
        except:
            messages.error(request, 'Coupon not found')
        return redirect('admin_coupons')


class AdminOfferListView(View):
    """List all limited time offers."""
    
    template_name = 'admin/offers/list.html'
    
    @method_decorator(login_required)
    @method_decorator(user_passes_test(is_staff_user, login_url='/accounts/login/'))
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)
    
    def get(self, request):
        offers = LimitedOffer.objects().order_by('-created_at')
        return render(request, self.template_name, {'offers': offers})


class AdminOfferCreateView(View):
    """Create new offer."""
    
    template_name = 'admin/offers/form.html'
    
    @method_decorator(login_required)
    @method_decorator(user_passes_test(is_staff_user, login_url='/accounts/login/'))
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)
    
    def get(self, request):
        products = Product.objects(is_active=True)[:50]
        return render(request, self.template_name, {'offer': None, 'action': 'Create', 'products': products})
    
    def post(self, request):
        try:
            from datetime import datetime
            import uuid
            
            starts_at = request.POST.get('starts_at')
            ends_at = request.POST.get('ends_at')
            
            if starts_at:
                starts_at = datetime.strptime(starts_at, '%Y-%m-%dT%H:%M')
            else:
                starts_at = datetime.utcnow()
            
            if ends_at:
                ends_at = datetime.strptime(ends_at, '%Y-%m-%dT%H:%M')
            else:
                ends_at = datetime.utcnow() + timedelta(days=7)
            
            product_ids = request.POST.getlist('product_ids')
            
            offer = LimitedOffer(
                name=request.POST.get('name'),
                slug=request.POST.get('slug') or f"offer-{uuid.uuid4().hex[:8]}",
                description=request.POST.get('description', ''),
                offer_type=request.POST.get('offer_type', 'flash_sale'),
                product_ids=product_ids,
                discount_type=request.POST.get('discount_type', 'percentage'),
                discount_value=float(request.POST.get('discount_value', 0)),
                starts_at=starts_at,
                ends_at=ends_at,
                banner_text=request.POST.get('banner_text', ''),
                is_active=request.POST.get('is_active') == 'on',
                show_countdown=request.POST.get('show_countdown') == 'on',
            )
            offer.save()
            messages.success(request, 'Offer created successfully')
            return redirect('admin_offers')
        except Exception as e:
            messages.error(request, f'Error: {str(e)}')
            return redirect('admin_offers')


class AdminOfferEditView(View):
    """Edit offer."""
    
    template_name = 'admin/offers/form.html'
    
    @method_decorator(login_required)
    @method_decorator(user_passes_test(is_staff_user, login_url='/accounts/login/'))
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)
    
    def get(self, request, offer_id):
        from bson import ObjectId
        try:
            offer = LimitedOffer.objects.get(id=ObjectId(offer_id))
            products = Product.objects(is_active=True)[:50]
            return render(request, self.template_name, {'offer': offer, 'action': 'Edit', 'products': products})
        except:
            messages.error(request, 'Offer not found')
            return redirect('admin_offers')
    
    def post(self, request, offer_id):
        from bson import ObjectId
        try:
            offer = LimitedOffer.objects.get(id=ObjectId(offer_id))
            
            starts_at = request.POST.get('starts_at')
            ends_at = request.POST.get('ends_at')
            
            if starts_at:
                offer.starts_at = datetime.strptime(starts_at, '%Y-%m-%dT%H:%M')
            if ends_at:
                offer.ends_at = datetime.strptime(ends_at, '%Y-%m-%dT%H:%M')
            
            offer.name = request.POST.get('name')
            if request.POST.get('slug'):
                offer.slug = request.POST.get('slug')
            offer.description = request.POST.get('description', '')
            offer.offer_type = request.POST.get('offer_type', 'flash_sale')
            offer.product_ids = request.POST.getlist('product_ids')
            offer.discount_type = request.POST.get('discount_type', 'percentage')
            offer.discount_value = float(request.POST.get('discount_value', 0))
            offer.banner_text = request.POST.get('banner_text', '')
            offer.is_active = request.POST.get('is_active') == 'on'
            offer.show_countdown = request.POST.get('show_countdown') == 'on'
            
            offer.save()
            messages.success(request, 'Offer updated successfully')
            return redirect('admin_offers')
        except Exception as e:
            messages.error(request, f'Error: {str(e)}')
            return redirect('admin_offers')


class AdminOfferDeleteView(View):
    """Delete offer."""
    
    @method_decorator(login_required)
    @method_decorator(user_passes_test(is_staff_user, login_url='/accounts/login/'))
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)
    
    def post(self, request, offer_id):
        from bson import ObjectId
        try:
            offer = LimitedOffer.objects.get(id=ObjectId(offer_id))
            offer.delete()
            messages.success(request, 'Offer deleted successfully')
        except:
            messages.error(request, 'Offer not found')
        return redirect('admin_offers')


class AdminReviewListView(View):
    """List all reviews."""
    
    template_name = 'admin/reviews/list.html'
    
    @method_decorator(login_required)
    @method_decorator(user_passes_test(is_staff_user, login_url='/accounts/login/'))
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)
    
    def get(self, request):
        reviews = ProductReview.objects().order_by('-created_at')
        return render(request, self.template_name, {'reviews': reviews})


class AdminReviewApproveView(View):
    """Approve or reject a review."""
    
    @method_decorator(login_required)
    @method_decorator(user_passes_test(is_staff_user, login_url='/accounts/login/'))
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)
    
    def post(self, request, review_id):
        from bson import ObjectId
        try:
            review = ProductReview.objects.get(id=ObjectId(review_id))
            review.is_approved = not review.is_approved
            review.save()
            return JsonResponse({'success': True, 'is_approved': review.is_approved})
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
