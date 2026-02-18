from django.shortcuts import render
from django.views import View
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_protect
from django.utils.decorators import method_decorator
from django.core.cache import cache
from django.utils import timezone
import json
import logging

from offers.models import Coupon, CouponUsage, LimitedOffer, ProductReview
from orders.models import Order

logger = logging.getLogger(__name__)


def validate_id(id_string):
    """Validate that ID is a valid integer."""
    if not id_string:
        return None
    try:
        return int(id_string)
    except (ValueError, TypeError):
        return None


def parse_json_body(request, max_size=1024*256):
    """Safely parse JSON request body with size limit (256KB)."""
    if len(request.body) > max_size:
        raise ValueError("Request body too large")
    
    try:
        return json.loads(request.body.decode('utf-8'))
    except (json.JSONDecodeError, UnicodeDecodeError) as e:
        raise ValueError(f"Invalid JSON: {str(e)}")


@method_decorator(csrf_protect, name='dispatch')
class ApplyCouponView(View):
    """Apply coupon to cart."""
    
    def post(self, request):
        try:
            data = parse_json_body(request)
            code = data.get('code', '').strip().upper()[:50]
            cart_total = float(data.get('cart_total', 0))
            user_email = request.user.email if request.user.is_authenticated else ''
            
            if not code:
                return JsonResponse({'error': 'Coupon code is required'}, status=400)
            
            if cart_total < 0:
                return JsonResponse({'error': 'Invalid cart total'}, status=400)
            
            # Cache coupon lookup
            cache_key = f"coupon:{code}"
            coupon_data = cache.get(cache_key)
            
            if coupon_data:
                try:
                    coupon = Coupon.objects.get(id=coupon_data['id'])
                except Coupon.DoesNotExist:
                    cache.delete(cache_key)
                    return JsonResponse({'error': 'Invalid coupon code'}, status=400)
            else:
                try:
                    coupon = Coupon.objects.get(code=code, is_active=True)
                    cache.set(cache_key, {'id': coupon.id}, 60)
                except Coupon.DoesNotExist:
                    return JsonResponse({'error': 'Invalid coupon code'}, status=400)
            
            if not coupon.is_valid:
                return JsonResponse({'error': 'This coupon has expired or reached its usage limit'}, status=400)
            
            can_use, msg = coupon.can_use(user_email)
            if not can_use:
                return JsonResponse({'error': msg}, status=400)
            
            if cart_total < float(coupon.min_order_value):
                return JsonResponse({
                    'error': f'Minimum order value is ₹{coupon.min_order_value:,.0f}'
                }, status=400)
            
            discount = min(coupon.calculate_discount(cart_total), cart_total)
            
            request.session['applied_coupon'] = {'code': coupon.code}
            request.session.modified = True
            
            logger.info(f"Coupon {coupon.code} applied by {user_email}")
            
            return JsonResponse({
                'success': True,
                'message': f'Coupon applied! You save ₹{discount:,.0f}',
                'discount': discount,
                'coupon_code': coupon.code,
                'discount_type': coupon.discount_type
            })
            
        except ValueError as e:
            return JsonResponse({'error': str(e)}, status=400)
        except Exception as e:
            logger.error(f"Coupon application failed: {e}", exc_info=True)
            return JsonResponse({'error': 'Failed to apply coupon'}, status=500)


@method_decorator(csrf_protect, name='dispatch')
class RemoveCouponView(View):
    """Remove applied coupon."""
    
    def post(self, request):
        if 'applied_coupon' in request.session:
            del request.session['applied_coupon']
            request.session.modified = True
        
        return JsonResponse({'success': True})


class ActiveOffersView(View):
    """Get all active limited time offers."""
    
    def get(self, request):
        cache_key = "active_offers"
        cached = cache.get(cache_key)
        
        if cached:
            return JsonResponse({'offers': cached})
        
        now = timezone.now()
        offers = LimitedOffer.objects.filter(
            is_active=True,
            starts_at__lte=now,
            ends_at__gte=now
        ).values(
            'id', 'name', 'slug', 'description', 'offer_type',
            'discount_value', 'discount_type', 'banner_image', 'banner_text'
        ).order_by('-created_at')[:20]
        
        offers_data = list(offers)
        cache.set(cache_key, offers_data, 60)
        
        return JsonResponse({'offers': offers_data})


@method_decorator(csrf_protect, name='dispatch')
class SubmitReviewView(View):
    """Submit a product review."""
    
    def post(self, request):
        if not request.user.is_authenticated:
            return JsonResponse({'error': 'Please login to submit a review'}, status=401)
        
        try:
            data = parse_json_body(request)
            
            product_id = validate_id(data.get('product_id'))
            if not product_id:
                return JsonResponse({'error': 'Invalid product ID'}, status=400)
            
            try:
                rating = int(data.get('rating'))
                if not 1 <= rating <= 5:
                    raise ValueError()
            except (ValueError, TypeError):
                return JsonResponse({'error': 'Rating must be between 1 and 5'}, status=400)
            
            title = data.get('title', '').strip()[:100]
            review_text = data.get('review', '').strip()[:2000]
            pros = [p[:100] for p in data.get('pros', [])[:10] if p]
            cons = [c[:100] for c in data.get('cons', [])[:10] if c]
            
            # Check if product exists
            from products.models import Product
            if not Product.objects.filter(id=product_id, is_active=True).exists():
                return JsonResponse({'error': 'Product not found'}, status=404)
            
            # Check for existing review
            if ProductReview.objects.filter(product_id=product_id, user_email=request.user.email).exists():
                return JsonResponse({'error': 'You have already reviewed this product'}, status=400)
            
            # Check for verified purchase - optimized query
            is_verified = Order.objects.filter(
                user_id=str(request.user.id),
                order_status__in=['delivered', 'shipped'],
                items__product_id=product_id
            ).exists()
            
            review = ProductReview.objects.create(
                product_id=product_id,
                user_email=request.user.email,
                user_name=request.user.get_full_name()[:50] or request.user.username[:50],
                rating=rating,
                title=title,
                review=review_text,
                pros=pros,
                cons=cons,
                is_verified_purchase=is_verified
            )
            
            logger.info(f"Review submitted by {request.user.email} for product {product_id}")
            
            return JsonResponse({
                'success': True,
                'message': 'Thank you for your review!',
                'is_verified': is_verified
            })
            
        except ValueError as e:
            return JsonResponse({'error': str(e)}, status=400)
        except Exception as e:
            logger.error(f"Review submission failed: {e}", exc_info=True)
            return JsonResponse({'error': 'Failed to submit review'}, status=500)


@method_decorator(csrf_protect, name='dispatch')
class MarkReviewHelpfulView(View):
    """Mark a review as helpful."""
    
    def post(self, request):
        if not request.user.is_authenticated:
            return JsonResponse({'error': 'Please login'}, status=401)
        
        try:
            data = parse_json_body(request)
            review_id = validate_id(data.get('review_id'))
            
            if not review_id:
                return JsonResponse({'error': 'Invalid review ID'}, status=400)
            
            try:
                review = ProductReview.objects.get(id=review_id)
            except ProductReview.DoesNotExist:
                return JsonResponse({'error': 'Review not found'}, status=404)
            
            if review.user_email == request.user.email:
                return JsonResponse({'error': 'Cannot mark your own review'}, status=400)
            
            if review.mark_helpful(request.user.email):
                return JsonResponse({
                    'success': True,
                    'helpful_count': review.helpful_count
                })
            
            return JsonResponse({'error': 'Already marked'}, status=400)
                
        except ValueError as e:
            return JsonResponse({'error': str(e)}, status=400)
        except Exception as e:
            logger.error(f"Mark helpful failed: {e}", exc_info=True)
            return JsonResponse({'error': 'Failed'}, status=500)


def get_product_reviews(request, product_id):
    """Get all reviews for a product with caching."""
    product_id = validate_id(product_id)
    if not product_id:
        return JsonResponse({'error': 'Invalid product ID', 'reviews': []}, status=400)
    
    cache_key = f"product_reviews:{product_id}"
    cached = cache.get(cache_key)
    
    if cached:
        return JsonResponse(cached)
    
    reviews = ProductReview.objects.filter(
        product_id=product_id,
        is_approved=True
    ).order_by('-helpful_count', '-created_at').values(
        'id', 'user_name', 'rating', 'title', 'review',
        'images', 'is_verified_purchase', 'helpful_count',
        'pros', 'cons', 'created_at'
    )[:50]
    
    reviews_data = []
    for r in reviews:
        reviews_data.append({
            'id': r['id'],
            'user_name': r['user_name'],
            'rating': r['rating'],
            'title': r['title'],
            'review': r['review'],
            'images': r['images'] or [],
            'is_verified': r['is_verified_purchase'],
            'helpful_count': r['helpful_count'],
            'pros': r['pros'] or [],
            'cons': r['cons'] or [],
            'created_at': r['created_at'].strftime('%d %b, %Y') if r['created_at'] else ''
        })
    
    total = len(reviews_data)
    avg_rating = sum(r['rating'] for r in reviews_data) / total if total > 0 else 0
    
    rating_dist = {5: 0, 4: 0, 3: 0, 2: 0, 1: 0}
    for r in reviews_data:
        rating_dist[r['rating']] = rating_dist.get(r['rating'], 0) + 1
    
    result = {
        'reviews': reviews_data,
        'total': total,
        'average_rating': round(avg_rating, 1),
        'rating_distribution': rating_dist
    }
    
    cache.set(cache_key, result, 60)
    
    return JsonResponse(result)
