from django.core.cache import cache
from products.models import Product, Wishlist


def cart(request):
    """
    Context processor to make cart available in all templates.
    Optimized to avoid database queries on every request.
    """
    cart_items = request.session.get('cart', [])
    
    if not cart_items:
        return {
            'cart_items': [],
            'cart_total': 0,
            'cart_count': 0,
        }
    
    cart_count = sum(item.get('quantity', 1) for item in cart_items)
    cart_total = sum(
        item.get('product_price', 0) * item.get('quantity', 1) 
        for item in cart_items
    )
    
    return {
        'cart_items': cart_items,
        'cart_total': cart_total,
        'cart_count': cart_count,
    }


def wishlist(request):
    """
    Context processor to make wishlist count available in all templates.
    Uses caching to avoid database queries on every request.
    """
    if not request.user.is_authenticated:
        return {'wishlist_count': 0}
    
    user_id = str(request.user.id)
    cache_key = f'wishlist_count:{user_id}'
    
    # Try to get from cache first
    cached_count = cache.get(cache_key)
    if cached_count is not None:
        return {'wishlist_count': cached_count}
    
    # Query database only if not in cache
    try:
        wishlist_obj = Wishlist.objects.filter(user_id=user_id).first()
        count = wishlist_obj.products.count() if wishlist_obj else 0
    except Exception:
        count = 0
    
    # Cache for 60 seconds
    cache.set(cache_key, count, 60)
    
    return {'wishlist_count': count}
