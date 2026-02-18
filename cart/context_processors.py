from django.shortcuts import get_object_or_404
from products.models import Product


def cart(request):
    """
    Context processor to make cart available in all templates.
    Retrieves cart from session or database for authenticated users.
    """
    cart_items = []
    cart_total = 0
    cart_count = 0
    
    # Get cart from session
    if request.session.get('cart'):
        cart_items = request.session.get('cart', [])
        cart_count = sum(item.get('quantity', 1) for item in cart_items)
        cart_total = sum(
            item.get('product_price', 0) * item.get('quantity', 1) 
            for item in cart_items
        )
    
    # If user is authenticated, also check database cart
    if request.user.is_authenticated:
        try:
            from users.models import CartItem
            db_cart_items = CartItem.objects.filter(user=request.user).select_related()
            
            if db_cart_items.exists():
                # Use database cart items
                cart_items = []
                for item in db_cart_items:
                    cart_items.append({
                        'product_id': item.product_id,
                        'product_slug': None,  # Will need to fetch
                        'product_name': item.product_name,
                        'product_price': float(item.product_price),
                        'product_image': item.product_image,
                        'quantity': item.quantity,
                    })
                
                cart_count = sum(item['quantity'] for item in cart_items)
                cart_total = sum(item['product_price'] * item['quantity'] for item in cart_items)
        except Exception:
            pass
    
    return {
        'cart_items': cart_items,
        'cart_total': cart_total,
        'cart_count': cart_count,
    }


def wishlist(request):
    """
    Context processor to make wishlist count available in all templates.
    """
    wishlist_count = 0
    
    if request.user.is_authenticated:
        try:
            from products.models import Wishlist
            wishlist_obj = Wishlist.objects.filter(
                user_id=str(request.user.id)
            ).first()
            
            if wishlist_obj:
                wishlist_count = wishlist_obj.products.count()
        except Exception:
            pass
    
    return {
        'wishlist_count': wishlist_count,
    }
