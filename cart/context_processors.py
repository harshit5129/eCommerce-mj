from django.shortcuts import get_object_or_404
from users.mongo_models import User


def cart(request):
    """
    Context processor to make cart available in all templates.
    Retrieves cart from session or database for authenticated users.
    """
    cart_items = []
    cart_total = 0
    cart_count = 0
    
    if request.session.get('cart'):
        cart_items = request.session.get('cart', [])
        cart_count = sum(item.get('quantity', 1) for item in cart_items)
        cart_total = sum(
            item.get('product_price', 0) * item.get('quantity', 1) 
            for item in cart_items
        )
    
    if request.user.is_authenticated:
        try:
            from bson import ObjectId
            user_id = request.session.get('user_id')
            
            # Try to get user by MongoDB ObjectId
            try:
                user = User.objects.get(id=ObjectId(user_id))
            except:
                # Fallback: try to get by email
                user_email = request.session.get('user_email')
                if user_email:
                    user = User.objects.get(email=user_email)
                else:
                    user = None
            
            if user and user.addresses:
                db_cart = getattr(user, 'cart_items', [])
                if db_cart:
                    cart_items = [item.to_dict() for item in db_cart]
                    cart_count = sum(item.quantity for item in db_cart)
                    cart_total = sum(item.total for item in db_cart)
        except Exception:
            pass
    
    return {
        'cart_items': cart_items,
        'cart_total': cart_total,
        'cart_count': cart_count,
    }
