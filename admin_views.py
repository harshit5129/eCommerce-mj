from django.shortcuts import render, redirect
from django.views import View
from django.contrib import messages
from django.http import JsonResponse
import json

from users.mongo_models import User
from products.models import Product
from orders.models import Order


class AdminDashboardView(View):
    """Admin dashboard view."""
    
    template_name = 'admin/dashboard.html'
    
    def get(self, request):
        total_users = User.objects.count()
        total_products = Product.objects.count()
        total_orders = Order.objects.count()
        
        # Calculate revenue
        orders = Order.objects()
        total_revenue = sum(order.total for order in orders)
        
        # Recent orders
        recent_orders = Order.objects().order_by('-created_at')[:5]
        
        # Low stock products
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
    
    def get(self, request):
        users = User.objects().order_by('-date_joined')
        return render(request, self.template_name, {'users': users})


class AdminUserEditView(View):
    """Edit user."""
    
    template_name = 'admin/users/edit.html'
    
    def get(self, request, user_id):
        from bson import ObjectId
        try:
            user = User.objects.get(id=ObjectId(user_id))
            return render(request, self.template_name, {'user': user})
        except:
            messages.error(request, 'User not found')
            return redirect('admin_users')
    
    def post(self, request, user_id):
        from bson import ObjectId
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
            messages.success(request, 'User updated successfully')
            return redirect('admin_users')
        except Exception as e:
            messages.error(request, f'Error: {str(e)}')
            return redirect('admin_users')


class AdminUserDeleteView(View):
    """Delete user."""
    
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
    
    def get(self, request):
        products = Product.objects().order_by('-created_at')
        return render(request, self.template_name, {'products': products})


class AdminProductCreateView(View):
    """Create new product."""
    
    template_name = 'admin/products/form.html'
    
    def get(self, request):
        return render(request, self.template_name, {'product': None, 'action': 'Create'})
    
    def post(self, request):
        try:
            category_data = {
                'name': request.POST.get('category_name', ''),
                'slug': request.POST.get('category_slug', '')
            }
            
            product = Product(
                name=request.POST.get('name'),
                slug=request.POST.get('slug'),
                sku=request.POST.get('sku'),
                description=request.POST.get('description', ''),
                short_description=request.POST.get('short_description', ''),
                price=float(request.POST.get('price', 0)),
                compare_price=float(request.POST.get('compare_price', 0)) if request.POST.get('compare_price') else None,
                category=category_data if category_data['name'] else None,
                tags=request.POST.get('tags', '').split(',') if request.POST.get('tags') else [],
                stock_quantity=int(request.POST.get('stock_quantity', 0)),
                track_inventory=request.POST.get('track_inventory') == 'on',
                is_active=request.POST.get('is_active') == 'on',
                is_featured=request.POST.get('is_featured') == 'on',
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
            
            category_data = {
                'name': request.POST.get('category_name', ''),
                'slug': request.POST.get('category_slug', '')
            }
            
            product.name = request.POST.get('name')
            product.slug = request.POST.get('slug')
            product.sku = request.POST.get('sku')
            product.description = request.POST.get('description', '')
            product.short_description = request.POST.get('short_description', '')
            product.price = float(request.POST.get('price', 0))
            product.compare_price = float(request.POST.get('compare_price', 0)) if request.POST.get('compare_price') else None
            product.category = category_data if category_data['name'] else None
            product.tags = request.POST.get('tags', '').split(',') if request.POST.get('tags') else []
            product.stock_quantity = int(request.POST.get('stock_quantity', 0))
            product.track_inventory = request.POST.get('track_inventory') == 'on'
            product.is_active = request.POST.get('is_active') == 'on'
            product.is_featured = request.POST.get('is_featured') == 'on'
            
            product.save()
            messages.success(request, 'Product updated successfully')
            return redirect('admin_products')
        except Exception as e:
            messages.error(request, f'Error: {str(e)}')
            return redirect('admin_products')


class AdminProductDeleteView(View):
    """Delete product."""
    
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
    
    def get(self, request, order_number):
        order = Order.objects(order_number=order_number).first()
        if not order:
            messages.error(request, 'Order not found')
            return redirect('admin_orders')
        return render(request, self.template_name, {'order': order})


class AdminOrderUpdateView(View):
    """Update order status."""
    
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
