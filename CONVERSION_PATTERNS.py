"""
Example conversion pattern from MongoEngine to Django ORM.

This file shows the key differences and patterns for migrating views.
"""

# PATTERN 1: ObjectId Validation
# ===============================

# OLD (MongoDB):
from bson import ObjectId
from bson.errors import InvalidId

def validate_object_id(id_string):
    if not id_string:
        return None
    try:
        return ObjectId(id_string)
    except (InvalidId, TypeError):
        return None

# NEW (PostgreSQL):
def validate_id(id_string):
    """Validate that ID is a valid integer."""
    if not id_string:
        return None
    try:
        return int(id_string)
    except (ValueError, TypeError):
        return None


# PATTERN 2: Query Objects
# ========================

# OLD (MongoDB):
from users.mongo_models import User
user = User.objects(email='test@example.com').first()
users = User.objects().order_by('-date_joined')[:10]

# NEW (PostgreSQL):
from users.models import User
user = User.objects.filter(email='test@example.com').first()
users = User.objects.order_by('-date_joined')[:10]


# PATTERN 3: Get by ID
# =====================

# OLD (MongoDB):
from bson import ObjectId
user = User.objects.get(id=ObjectId(user_id))

# NEW (PostgreSQL):
user = User.objects.get(id=int(user_id))


# PATTERN 4: Filter and Count
# ============================

# OLD (MongoDB):
from orders.models import Order
total_orders = Order.objects.count()
pending_orders = Order.objects(order_status='pending').count()

# NEW (PostgreSQL):
from orders.models import Order
total_orders = Order.objects.count()
pending_orders = Order.objects.filter(order_status='pending').count()


# PATTERN 5: Aggregation (Dashboard Revenue)
# ==========================================

# OLD (MongoDB):
orders = Order.objects()
total_revenue = sum(order.total for order in orders)

# NEW (PostgreSQL):
from django.db.models import Sum
total_revenue = Order.objects.aggregate(total=Sum('total'))['total'] or 0


# PATTERN 6: Related Objects (Order Items)
# ========================================

# OLD (MongoDB - Embedded):
order = Order.objects.get(id=order_id)
items = order.items  # Embedded documents

# NEW (PostgreSQL - ForeignKey):
order = Order.objects.get(id=order_id)
items = order.items.all()  # Related objects


# PATTERN 7: Create Document
# ===========================

# OLD (MongoDB):
from offers.models import Coupon
coupon = Coupon(
    code='SAVE10',
    discount_value=10.00,
    is_active=True
)
coupon.save()

# NEW (PostgreSQL):
from offers.models import Coupon
coupon = Coupon.objects.create(
    code='SAVE10',
    discount_value=10.00,
    is_active=True
)


# PATTERN 8: Update Document
# ===========================

# OLD (MongoDB):
product = Product.objects.get(id=product_id)
product.stock_quantity -= 1
product.save()

# NEW (PostgreSQL):
# Option 1: Instance update
product = Product.objects.get(id=product_id)
product.stock_quantity -= 1
product.save()

# Option 2: Atomic update (better for race conditions)
from django.db.models import F
Product.objects.filter(id=product_id).update(stock_quantity=F('stock_quantity') - 1)


# PATTERN 9: Delete Document
# ===========================

# OLD (MongoDB):
product = Product.objects.get(id=product_id)
product.delete()

# NEW (PostgreSQL):
# Option 1: Instance delete
product = Product.objects.get(id=product_id)
product.delete()

# Option 2: QuerySet delete
Product.objects.filter(id=product_id).delete()


# PATTERN 10: JSON Field Access
# ==============================

# OLD (MongoDB - Native):
order = Order.objects.get(id=order_id)
address = order.shipping_address.street

# NEW (PostgreSQL - JSONField):
order = Order.objects.get(id=order_id)
address = order.shipping_address['street']


# PATTERN 11: Many to Many
# =========================

# OLD (MongoDB - Array of references):
wishlist = Wishlist.objects(user_id=user_id).first()
product_ids = wishlist.product_ids

# NEW (PostgreSQL - ManyToManyField):
wishlist = Wishlist.objects.filter(user_id=user_id).first()
if wishlist:
    products = wishlist.products.all()  # QuerySet of Product objects


# PATTERN 12: Search
# =================

# OLD (MongoDB - Text search):
products = Product.objects(__raw__={'$text': {'$search': search_term}})

# NEW (PostgreSQL - Django ORM):
from django.db.models import Q
products = Product.objects.filter(
    Q(name__icontains=search_term) | 
    Q(description__icontains=search_term)
)

# Or with PostgreSQL full-text search (requires setup):
from django.contrib.postgres.search import SearchVector
products = Product.objects.annotate(
    search=SearchVector('name', 'description')
).filter(search=search_term)


# COMPLETE EXAMPLE: Order Creation
# =================================

# OLD (MongoDB):
def create_order(request):
    data = json.loads(request.body)
    
    order_items = []
    for item in cart:
        order_items.append(OrderItem(
            product_id=item['product_id'],
            product_name=item['product_name'],
            price=item['price'],
            quantity=item['quantity']
        ))
        
        product = Product.objects(id=item['product_id']).first()
        if product and product.track_inventory:
            product.stock_quantity -= item['quantity']
            product.save()
    
    order = Order(
        order_number=generate_order_number(),
        user_id=user_id,
        items=order_items,  # Embedded
        total=calculate_total(),
        shipping_address=ShippingAddress(**address_data)  # Embedded
    )
    order.save()


# NEW (PostgreSQL):
def create_order(request):
    from django.db import transaction
    
    data = json.loads(request.body)
    
    with transaction.atomic():
        # Create order first
        order = Order.objects.create(
            order_number=generate_order_number(),
            user_id=user_id,
            total=calculate_total(),
            shipping_address=address_data  # JSONField
        )
        
        # Create order items
        for item in cart:
            OrderItem.objects.create(
                order=order,
                product_id=item['product_id'],
                product_name=item['product_name'],
                price=item['price'],
                quantity=item['quantity']
            )
            
            # Update inventory atomically
            from django.db.models import F
            Product.objects.filter(
                id=item['product_id'],
                track_inventory=True
            ).update(stock_quantity=F('stock_quantity') - item['quantity'])


# QUICK REFERENCE: Common Query Translations
# ==========================================

# .first()
# MongoDB: User.objects(email='test').first()
# PostgreSQL: User.objects.filter(email='test').first()

# .count()
# MongoDB: Order.objects(order_status='pending').count()
# PostgreSQL: Order.objects.filter(order_status='pending').count()

# .exists()
# MongoDB: bool(User.objects(email='test').first())
# PostgreSQL: User.objects.filter(email='test').exists()

# .order_by()
# MongoDB: Order.objects().order_by('-created_at')
# PostgreSQL: Order.objects.order_by('-created_at')

# slicing [:10]
# MongoDB: Product.objects()[:10]
# PostgreSQL: Product.objects.all()[:10]

# aggregate
# MongoDB: sum(order.total for order in Order.objects())
# PostgreSQL: Order.objects.aggregate(Sum('total'))

# distinct
# MongoDB: Order.objects.distinct('user_email')
# PostgreSQL: Order.objects.values('user_email').distinct()
