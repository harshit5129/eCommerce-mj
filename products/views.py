from django.shortcuts import render, redirect
from django.contrib import messages
from django.views import View
from django.http import Http404, JsonResponse
from django.core.cache import cache
from django.db.models import Q
from django.views.decorators.csrf import csrf_protect
from django.utils.decorators import method_decorator
from products.models import Product, Category, Wishlist
from core.utils import validate_id, get_pagination_bounds
import math
import json
import logging

logger = logging.getLogger(__name__)


def get_categories_cached():
    """Get all active categories with caching."""
    cache_key = "categories_list"
    cached = cache.get(cache_key)
    if cached:
        return cached
    
    categories = list(Category.objects.filter(is_active=True).values('slug', 'name'))
    cache.set(cache_key, categories, 3600)
    return categories


def get_site_settings_cached():
    """Get site settings with caching for common values."""
    cache_key = "site_settings_common"
    cached = cache.get(cache_key)
    if cached:
        return cached
    
    from core.models import SiteSettings
    settings_obj = SiteSettings.get_settings()
    cache.set(cache_key, settings_obj, 300)
    return settings_obj


class HomeView(View):
    """Home page with featured products."""
    
    template_name = 'products/home.html'
    
    def get(self, request):
        cache_key = "home_view_data"
        cached_data = cache.get(cache_key)
        
        if cached_data:
            return render(request, self.template_name, cached_data)
        
        from core.models import HeroImage, SocialLink
        
        hero_images = list(HeroImage.objects.filter(is_active=True).order_by('sort_order')[:5])
        
        social_links = list(SocialLink.objects.filter(is_active=True).order_by('sort_order'))
        
        featured_products = list(
            Product.objects.filter(
                is_featured=True, 
                is_active=True
            ).select_related('category').prefetch_related('images')[:8]
        )
        
        latest_products = list(
            Product.objects.filter(
                is_active=True
            ).select_related('category').prefetch_related('images').order_by('-created_at')[:12]
        )
        
        categories = get_categories_cached()
        site_settings = get_site_settings_cached()
        
        context = {
            'hero_images': hero_images,
            'social_links': social_links,
            'featured_products': featured_products,
            'latest_products': latest_products,
            'categories': categories,
            'site_settings': site_settings,
        }
        
        cache.set(cache_key, context, 300)
        
        return render(request, self.template_name, context)


class ProductListView(View):
    """Product listing page with filtering and search."""
    
    template_name = 'products/product_list.html'
    
    def get(self, request):
        page = max(1, int(request.GET.get('page', 1)))
        per_page = 24
        category_slug = request.GET.get('category', '').strip()
        search = request.GET.get('search', '').strip()
        sort = request.GET.get('sort', '-created_at')
        min_price = request.GET.get('min_price', '').strip()
        max_price = request.GET.get('max_price', '').strip()
        
        # Only cache non-search queries
        if not search:
            cache_key = f"products:{category_slug}:{sort}:{min_price}:{max_price}:{page}"
            cached_data = cache.get(cache_key)
            if cached_data:
                cached_data['page'] = page
                return render(request, self.template_name, cached_data)
        
        products = Product.objects.filter(is_active=True).select_related('category')
        
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
        
        products = products.order_by(sort)
        
        # Use count() before slicing
        total_products = products.count()
        total_pages = math.ceil(total_products / per_page) if total_products > 0 else 1
        
        # Ensure page is within bounds
        page = min(page, total_pages)
        
        start = (page - 1) * per_page
        end = start + per_page
        
        # Slice after count
        products_list = list(products[start:end])
        
        categories = get_categories_cached()
        
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
        
        # Only cache non-search queries
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
                product = Product.objects.select_related('category').prefetch_related('images').get(
                    slug=slug, 
                    is_active=True
                )
            except Product.DoesNotExist:
                raise Http404("Product not found")
            
            # Get related products with limited fields
            if product.category:
                related_products = list(
                    Product.objects.filter(
                        category=product.category,
                        is_active=True
                    ).exclude(id=product.id).select_related('category')[:4]
                )
            else:
                related_products = list(
                    Product.objects.filter(
                        is_active=True
                    ).exclude(id=product.id).select_related('category')[:4]
                )
            
            cache.set(cache_key, {
                'product': product,
                'related_products': related_products
            }, 300)
        
        # Check wishlist status - cache this too
        in_wishlist = False
        if request.user.is_authenticated:
            wishlist_cache_key = f"wishlist_user:{request.user.id}:product:{product.id}"
            in_wishlist = cache.get(wishlist_cache_key)
            if in_wishlist is None:
                try:
                    wishlist = Wishlist.objects.filter(user_id=str(request.user.id)).first()
                    in_wishlist = wishlist and wishlist.has_product(product.id)
                    cache.set(wishlist_cache_key, in_wishlist, 60)
                except Exception:
                    in_wishlist = False
        
        # Get all images
        all_images = [img.image.url for img in product.images.all() if img.image]
        
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
            products = list(wishlist.products.filter(is_active=True).select_related('category'))
        
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
            product = Product.objects.get(id=product_id, is_active=True)
        except Product.DoesNotExist:
            return JsonResponse({'error': 'Product not found'}, status=404)
        
        try:
            wishlist, created = Wishlist.objects.get_or_create(
                user_id=str(request.user.id),
                defaults={'user_email': request.user.email}
            )
            
            if wishlist.has_product(product.id):
                wishlist.remove_product(product)
                count = wishlist.products.count()
                action = 'removed'
                message = 'Removed from wishlist'
            else:
                wishlist.add_product(product)
                count = wishlist.products.count()
                action = 'added'
                message = 'Added to wishlist'
            
            # Invalidate caches
            cache.delete(f'wishlist_count:{request.user.id}')
            cache.delete(f"wishlist_user:{request.user.id}:product:{product.id}")
            
            return JsonResponse({
                'success': True,
                'action': action,
                'message': message,
                'count': count
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
                    
                    # Invalidate caches
                    cache.delete(f'wishlist_count:{request.user.id}')
                    cache.delete(f"wishlist_user:{request.user.id}:product:{product.id}")
                    
                    messages.success(request, 'Product removed from wishlist.')
                except Product.DoesNotExist:
                    messages.error(request, 'Product not found.')
        except Exception as e:
            logger.error(f"Wishlist remove error: {e}", exc_info=True)
            messages.error(request, 'Error removing product from wishlist.')
        
        return redirect('wishlist')
