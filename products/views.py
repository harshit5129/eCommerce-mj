from django.shortcuts import render, redirect
from django.contrib import messages
from django.views import View
from django.http import Http404, JsonResponse
from django.core.cache import cache
from django.db.models import Q
from django.views.decorators.cache import cache_page
from django.views.decorators.csrf import csrf_protect
from django.utils.decorators import method_decorator
from products.models import Product, Category, Wishlist
import math
import json
import logging

logger = logging.getLogger(__name__)


def validate_id(id_string):
    """Validate that ID is a valid integer."""
    if not id_string:
        return None
    try:
        return int(id_string)
    except (ValueError, TypeError):
        return None


class HomeView(View):
    """Home page with featured products."""
    
    template_name = 'products/home.html'
    
    def get(self, request):
        cache_key = "home_view_data"
        cached_data = cache.get(cache_key)
        
        if cached_data:
            return render(request, self.template_name, cached_data)
        
        featured_products = list(Product.objects.filter(is_featured=True, is_active=True)[:8])
        latest_products = list(Product.objects.filter(is_active=True).order_by('-created_at')[:12])
        categories = self._get_categories()
        
        context = {
            'featured_products': featured_products,
            'latest_products': latest_products,
            'categories': categories,
        }
        
        cache.set(cache_key, context, 300)
        
        return render(request, self.template_name, context)
    
    def _get_categories(self):
        """Get all active categories."""
        cache_key = "categories_list"
        cached = cache.get(cache_key)
        if cached:
            return cached
        
        categories = Category.objects.filter(is_active=True)
        result = [{'slug': cat.slug, 'name': cat.name} for cat in categories]
        cache.set(cache_key, result, 3600)
        return result


class ProductListView(View):
    """Product listing page with filtering and search."""
    
    template_name = 'products/product_list.html'
    
    def get(self, request):
        page = int(request.GET.get('page', 1))
        per_page = 24
        category_slug = request.GET.get('category')
        search = request.GET.get('search', '').strip()
        sort = request.GET.get('sort', '-created_at')
        min_price = request.GET.get('min_price')
        max_price = request.GET.get('max_price')
        
        cache_key = f"products:{category_slug or 'all'}:{search}:{sort}:{min_price}:{max_price}:{page}"
        cached_data = cache.get(cache_key)
        
        if cached_data and not search:
            context = cached_data
            context['page'] = page
            return render(request, self.template_name, context)
        
        products = Product.objects.filter(is_active=True)
        
        # Filter by category
        if category_slug:
            products = products.filter(category__slug=category_slug)
        
        # Search
        if search:
            products = products.filter(
                Q(name__icontains=search) |
                Q(description__icontains=search) |
                Q(tags__icontains=search) |
                Q(sku__icontains=search)
            )
        
        # Price filters
        if min_price:
            try:
                products = products.filter(price__gte=float(min_price))
            except ValueError:
                pass
        
        if max_price:
            try:
                products = products.filter(price__lte=float(max_price))
            except ValueError:
                pass
        
        # Sorting
        valid_sorts = ['-created_at', 'created_at', 'price', '-price', 'name', '-name']
        if sort not in valid_sorts:
            sort = '-created_at'
        
        try:
            products = products.order_by(sort)
        except Exception:
            products = products.order_by('-created_at')
        
        # Pagination
        total_products = products.count()
        total_pages = math.ceil(total_products / per_page) if total_products > 0 else 1
        
        start = (page - 1) * per_page
        end = start + per_page
        
        products_list = list(products[start:end])
        
        categories = HomeView()._get_categories()
        
        context = {
            'products': products_list,
            'page': page,
            'total_pages': total_pages,
            'total_products': total_products,
            'category': category_slug,
            'search': search,
            'sort': sort,
            'min_price': min_price,
            'max_price': max_price,
            'categories': categories,
        }
        
        if not search:
            cache.set(cache_key, context, 60)
        
        return render(request, self.template_name, context)


class ProductDetailView(View):
    """Product detail page."""
    
    template_name = 'products/product_detail.html'
    
    def get(self, request, slug):
        cache_key = f"product_detail:{slug}"
        cached = cache.get(cache_key)
        
        if cached:
            product = cached['product']
            related_products = cached['related_products']
        else:
            try:
                product = Product.objects.get(slug=slug, is_active=True)
            except Product.DoesNotExist:
                raise Http404("Product not found")
            
            # Get related products
            if product.category:
                related_products = list(Product.objects.filter(
                    category=product.category,
                    is_active=True
                ).exclude(id=product.id)[:4])
            else:
                related_products = list(Product.objects.filter(
                    is_active=True
                ).exclude(id=product.id)[:4])
            
            cache.set(cache_key, {
                'product': product,
                'related_products': related_products
            }, 300)
        
        # Check wishlist status
        in_wishlist = False
        if request.user.is_authenticated:
            wishlist = Wishlist.objects.filter(user_id=str(request.user.id)).first()
            if wishlist and wishlist.has_product(product.id):
                in_wishlist = True
        
        # Get all images
        all_images = []
        images = product.images.all()
        if images:
            all_images = [img.image.url for img in images if img.image]
        
        context = {
            'product': product,
            'related_products': related_products,
            'in_wishlist': in_wishlist,
            'all_images': all_images,
        }
        return render(request, self.template_name, context)


class WishlistView(View):
    """Wishlist page."""
    
    template_name = 'products/wishlist.html'
    
    def get(self, request):
        if not request.user.is_authenticated:
            messages.warning(request, 'Please login to view your wishlist.')
            return redirect('login')
        
        wishlist = Wishlist.objects.filter(user_id=str(request.user.id)).first()
        
        products = []
        if wishlist:
            products = list(wishlist.products.filter(is_active=True))
        
        context = {
            'products': products,
            'wishlist': wishlist,
        }
        return render(request, self.template_name, context)


@method_decorator(csrf_protect, name='dispatch')
class WishlistToggleView(View):
    """Toggle product in wishlist (add/remove)."""
    
    def post(self, request, product_id):
        if not request.user.is_authenticated:
            return JsonResponse({'error': 'Please login to add items to wishlist'}, status=401)
        
        product_id = validate_id(product_id)
        if not product_id:
            return JsonResponse({'error': 'Invalid product ID'}, status=400)
        
        try:
            product = Product.objects.get(id=product_id)
        except Product.DoesNotExist:
            return JsonResponse({'error': 'Product not found'}, status=404)
        
        try:
            wishlist, created = Wishlist.objects.get_or_create(
                user_id=str(request.user.id),
                defaults={'user_email': request.user.email}
            )
            
            if wishlist.has_product(product.id):
                wishlist.remove_product(product)
                return JsonResponse({
                    'success': True,
                    'action': 'removed',
                    'message': 'Removed from wishlist',
                    'count': wishlist.products.count()
                })
            else:
                wishlist.add_product(product)
                return JsonResponse({
                    'success': True,
                    'action': 'added',
                    'message': 'Added to wishlist',
                    'count': wishlist.products.count()
                })
                
        except Exception as e:
            logger.error(f"Wishlist toggle error: {e}", exc_info=True)
            return JsonResponse({'error': 'An error occurred'}, status=500)


class WishlistRemoveView(View):
    """Remove product from wishlist."""
    
    def post(self, request, product_id):
        if not request.user.is_authenticated:
            messages.warning(request, 'Please login to manage your wishlist.')
            return redirect('login')
        
        product_id = validate_id(product_id)
        if not product_id:
            messages.error(request, 'Invalid product.')
            return redirect('wishlist')
        
        try:
            wishlist = Wishlist.objects.filter(user_id=str(request.user.id)).first()
            if wishlist:
                try:
                    product = Product.objects.get(id=product_id)
                    wishlist.remove_product(product)
                    messages.success(request, 'Product removed from wishlist.')
                except Product.DoesNotExist:
                    messages.error(request, 'Product not found.')
        except Exception as e:
            logger.error(f"Wishlist remove error: {e}", exc_info=True)
            messages.error(request, 'Error removing product from wishlist.')
        
        return redirect('wishlist')


def get_wishlist_count(request):
    """Get wishlist count for the current user."""
    if request.user.is_authenticated:
        wishlist = Wishlist.objects.filter(user_id=str(request.user.id)).first()
        if wishlist:
            return wishlist.products.count()
    return 0
