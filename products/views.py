from django.shortcuts import render, redirect
from django.contrib import messages
from django.views import View
from django.http import Http404, JsonResponse
from products.models import Product, Category, Wishlist
import math
import re
import json


class HomeView(View):
    """Home page with featured products."""
    
    template_name = 'products/home.html'
    
    def get(self, request):
        featured_products = Product.objects(is_featured=True, is_active=True)[:8]
        latest_products = Product.objects(is_active=True).order_by('-created_at')[:12]
        
        categories = self._get_unique_categories()
        
        context = {
            'featured_products': featured_products,
            'latest_products': latest_products,
            'categories': categories,
        }
        return render(request, self.template_name, context)
    
    def _get_unique_categories(self):
        products = Product.objects(is_active=True, category__exists=True)
        categories = {}
        for product in products:
            if product.category and product.category.slug:
                categories[product.category.slug] = product.category.name
        return [{'slug': k, 'name': v} for k, v in categories.items()]


class ProductListView(View):
    """Product listing page with filtering and search."""
    
    template_name = 'products/product_list.html'
    
    def get(self, request):
        page = int(request.GET.get('page', 1))
        per_page = 12
        category = request.GET.get('category')
        search = request.GET.get('search', '').strip()
        sort = request.GET.get('sort', '-created_at')
        min_price = request.GET.get('min_price')
        max_price = request.GET.get('max_price')
        
        products = Product.objects(is_active=True)
        
        if category:
            products = products(category__slug=category)
        
        if search:
            search_regex = re.compile(re.escape(search), re.IGNORECASE)
            products = products(
                __raw__={
                    '$or': [
                        {'name': {'$regex': search_regex}},
                        {'description': {'$regex': search_regex}},
                        {'tags': {'$regex': search_regex}},
                        {'sku': {'$regex': search_regex}},
                    ]
                }
            )
        
        if min_price:
            try:
                products = products(price__gte=float(min_price))
            except ValueError:
                pass
        
        if max_price:
            try:
                products = products(price__lte=float(max_price))
            except ValueError:
                pass
        
        valid_sorts = ['-created_at', 'created_at', 'price', '-price', 'name', '-name']
        if sort not in valid_sorts:
            sort = '-created_at'
        
        try:
            products = products.order_by(sort)
        except Exception:
            products = products.order_by('-created_at')
        
        total_products = products.count()
        total_pages = math.ceil(total_products / per_page) if total_products > 0 else 1
        
        start = (page - 1) * per_page
        end = start + per_page
        products = products[start:end]
        
        categories = self._get_unique_categories()
        
        context = {
            'products': products,
            'page': page,
            'total_pages': total_pages,
            'total_products': total_products,
            'category': category,
            'search': search,
            'sort': sort,
            'min_price': min_price,
            'max_price': max_price,
            'categories': categories,
        }
        return render(request, self.template_name, context)
    
    def _get_unique_categories(self):
        products = Product.objects(is_active=True, category__exists=True)
        categories = {}
        for product in products:
            if product.category and product.category.slug:
                categories[product.category.slug] = product.category.name
        return [{'slug': k, 'name': v} for k, v in categories.items()]


class ProductDetailView(View):
    """Product detail page."""
    
    template_name = 'products/product_detail.html'
    
    def get(self, request, slug):
        product = Product.objects(slug=slug, is_active=True).first()
        
        if not product:
            raise Http404("Product not found")
        
        related_products = Product.objects(
            category=product.category,
            is_active=True,
            id__ne=product.id
        )[:4] if product.category else Product.objects(is_active=True, id__ne=product.id)[:4]
        
        in_wishlist = False
        user_id = request.session.get('user_id')
        user_email = request.session.get('user_email')
        
        if user_id and user_email:
            wishlist = Wishlist.objects(user_id=str(user_id)).first()
            if wishlist and wishlist.has_product(str(product.id)):
                in_wishlist = True
        
        context = {
            'product': product,
            'related_products': related_products,
            'in_wishlist': in_wishlist,
        }
        return render(request, self.template_name, context)


class WishlistView(View):
    """Wishlist page."""
    
    template_name = 'products/wishlist.html'
    
    def get(self, request):
        user_id = request.session.get('user_id')
        user_email = request.session.get('user_email')
        
        if not user_id or not user_email:
            messages.warning(request, 'Please login to view your wishlist.')
            return redirect('login')
        
        wishlist = Wishlist.objects(user_id=str(user_id)).first()
        
        products = []
        if wishlist:
            products = wishlist.products
        
        context = {
            'products': products,
            'wishlist': wishlist,
        }
        return render(request, self.template_name, context)


class WishlistToggleView(View):
    """Toggle product in wishlist (add/remove)."""
    
    def post(self, request, product_id):
        user_id = request.session.get('user_id')
        user_email = request.session.get('user_email')
        
        if not user_id or not user_email:
            return JsonResponse({'error': 'Please login to add items to wishlist'}, status=401)
        
        try:
            from bson import ObjectId
            product = Product.objects(id=ObjectId(product_id)).first()
            if not product:
                return JsonResponse({'error': 'Product not found'}, status=404)
            
            wishlist, created = Wishlist.objects.get_or_create(
                user_id=str(user_id),
                defaults={'user_email': user_email}
            )
            
            if wishlist.has_product(str(product_id)):
                wishlist.remove_product(str(product_id))
                return JsonResponse({
                    'success': True,
                    'action': 'removed',
                    'message': 'Removed from wishlist',
                    'count': len(wishlist.product_ids)
                })
            else:
                wishlist.add_product(str(product_id))
                return JsonResponse({
                    'success': True,
                    'action': 'added',
                    'message': 'Added to wishlist',
                    'count': len(wishlist.product_ids)
                })
                
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)


class WishlistRemoveView(View):
    """Remove product from wishlist."""
    
    def post(self, request, product_id):
        user_id = request.session.get('user_id')
        user_email = request.session.get('user_email')
        
        if not user_id or not user_email:
            messages.warning(request, 'Please login to manage your wishlist.')
            return redirect('login')
        
        try:
            wishlist = Wishlist.objects(user_id=str(user_id)).first()
            if wishlist:
                wishlist.remove_product(str(product_id))
                messages.success(request, 'Product removed from wishlist.')
        except Exception:
            messages.error(request, 'Error removing product from wishlist.')
        
        return redirect('wishlist')


def get_wishlist_count(request):
    """Get wishlist count for the current user."""
    user_id = request.session.get('user_id')
    if user_id:
        wishlist = Wishlist.objects(user_id=str(user_id)).first()
        if wishlist:
            return len(wishlist.product_ids)
    return 0
