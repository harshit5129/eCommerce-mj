from django.shortcuts import render, redirect
from django.views import View
from django.http import JsonResponse
from django.contrib import messages
from django.views.decorators.csrf import csrf_protect
from django.utils.decorators import method_decorator
from django.core.cache import cache
from django.db.models import Count
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


def parse_json_body(request, max_size=1024*1024):
    """Safely parse JSON request body with size limit."""
    if len(request.body) > max_size:
        raise ValueError("Request body too large")
    
    try:
        return json.loads(request.body.decode('utf-8'))
    except (json.JSONDecodeError, UnicodeDecodeError) as e:
        raise ValueError(f"Invalid JSON: {str(e)}")


@method_decorator(csrf_protect, name='dispatch')
class ApplyCouponView(View):
    """Apply coupon to cart - with race condition protection."""
    
    def post(self, request):
        try:
            data = parse_json_body(request)
            code = data.get('code', '').strip().upper()
            cart_total = float(data.get('cart_total', 0))
            user_email = request.user.email if request.user.is_authenticated else ''
            
            if not code:
                return JsonResponse({'error': 'Coupon code is required'}, status=400)
            
            if cart_total < 0:
                return JsonResponse({'error': 'Invalid cart total'}, status=400)
            
            try:
                coupon = Coupon.objects.get(code=code, is_active=True)
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
            
            # Check per-user limit
            if user_email:
                cache_key = f"coupon_check:{coupon.id}:{user_email}"
                
                user_usage = CouponUsage.objects.filter(coupon=coupon, user_email=user_email).count()
                
                if user_usage >= coupon.per_user_limit:
                    return JsonResponse({
                        'error': f'You have already used this coupon {user_usage} time(s)'
                    }, status=400)
                
                if cache.get(cache_key):
                    return JsonResponse({
                        'error': 'Coupon application in progress. Please wait.'
                    }, status=429)
                
                cache.set(cache_key, True, 300)
            
            discount = coupon.calculate_discount(cart_total)
            
            # Ensure discount doesn't exceed cart total
            discount = min(discount, cart_total)
            
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
            return JsonResponse({'error': 'Failed to apply coupon. Please try again.'}, status=500)


@method_decorator(csrf_protect, name='dispatch')
class RemoveCouponView(View):
    """Remove applied coupon."""
    
    def post(self, request):
        try:
            if 'applied_coupon' in request.session:
                coupon_code = request.session['applied_coupon'].get('code')
                user_email = request.user.email if request.user.is_authenticated else ''
                
                if user_email and coupon_code:
                    try:
                        coupon = Coupon.objects.get(code=coupon_code)
                        cache_key = f"coupon_check:{coupon.id}:{user_email}"
                        cache.delete(cache_key)
                    except Coupon.DoesNotExist:
                        pass
                
                del request.session['applied_coupon']
                request.session.modified = True
            
            return JsonResponse({'success': True})
        except Exception as e:
            logger.error(f"Coupon removal failed: {e}", exc_info=True)
            return JsonResponse({'error': 'Failed to remove coupon'}, status=500)


class ActiveOffersView(View):
    """Get all active limited time offers."""
    
    def get(self, request):
        try:
            now = timezone.now()
            offers = LimitedOffer.objects.filter(
                is_active=True,
                starts_at__lte=now,
                ends_at__gte=now
            ).order_by('-created_at')
            
            offers_data = []
            for offer in offers:
                offers_data.append({
                    'id': offer.id,
                    'name': offer.name,
                    'slug': offer.slug,
                    'description': offer.description,
                    'offer_type': offer.offer_type,
                    'discount_value': float(offer.discount_value),
                    'discount_type': offer.discount_type,
                    'time_remaining': offer.time_remaining,
                    'banner_image': offer.banner_image,
                    'banner_text': offer.banner_text,
                })
            
            return JsonResponse({'offers': offers_data})
        except Exception as e:
            logger.error(f"Failed to get active offers: {e}", exc_info=True)
            return JsonResponse({'offers': [], 'error': 'Failed to load offers'}, status=500)


@method_decorator(csrf_protect, name='dispatch')
class SubmitReviewView(View):
    """Submit a product review - with CSRF protection."""
    
    def post(self, request):
        try:
            data = parse_json_body(request)
            
            product_id = data.get('product_id')
            rating = data.get('rating')
            title = data.get('title', '').strip()[:100]
            review_text = data.get('review', '').strip()[:2000]
            pros = data.get('pros', [])[:10]
            cons = data.get('cons', [])[:10]
            
            if not request.user.is_authenticated:
                return JsonResponse({'error': 'Please login to submit a review'}, status=401)
            
            # Validate rating
            try:
                rating = int(rating)
                if not 1 <= rating <= 5:
                    raise ValueError()
            except (ValueError, TypeError):
                return JsonResponse({'error': 'Rating must be between 1 and 5'}, status=400)
            
            if not product_id:
                return JsonResponse({'error': 'Product ID is required'}, status=400)
            
            product_id = validate_id(product_id)
            if not product_id:
                return JsonResponse({'error': 'Invalid product ID'}, status=400)
            
            # Check if product exists
            from products.models import Product
            try:
                product = Product.objects.get(id=product_id, is_active=True)
            except Product.DoesNotExist:
                return JsonResponse({'error': 'Product not found'}, status=404)
            
            # Check for existing review
            existing = ProductReview.objects.filter(product_id=product_id, user_email=request.user.email).first()
            if existing:
                return JsonResponse({'error': 'You have already reviewed this product'}, status=400)
            
            # Check for verified purchase
            is_verified = False
            order_number = None
            orders = Order.objects.filter(user_id=str(request.user.id), order_status__in=['delivered', 'shipped'])
            for order in orders:
                for item in order.items.all():
                    if item.product_id == product_id:
                        is_verified = True
                        order_number = order.order_number
                        break
                if is_verified:
                    break
            
            review = ProductReview.objects.create(
                product_id=product_id,
                user_email=request.user.email,
                user_name=request.user.get_full_name() or request.user.username[:50],
                rating=rating,
                title=title,
                review=review_text,
                pros=[p[:100] for p in pros if p],
                cons=[c[:100] for c in cons if c],
                is_verified_purchase=is_verified,
                order_number=order_number
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
            return JsonResponse({'error': 'Failed to submit review. Please try again.'}, status=500)


@method_decorator(csrf_protect, name='dispatch')
class MarkReviewHelpfulView(View):
    """Mark a review as helpful - with CSRF protection."""
    
    def post(self, request):
        try:
            data = parse_json_body(request)
            review_id = data.get('review_id')
            
            if not request.user.is_authenticated:
                return JsonResponse({'error': 'Please login'}, status=401)
            
            if not review_id:
                return JsonResponse({'error': 'Review ID is required'}, status=400)
            
            review_id = validate_id(review_id)
            if not review_id:
                return JsonResponse({'error': 'Invalid review ID'}, status=400)
            
            try:
                review = ProductReview.objects.get(id=review_id)
            except ProductReview.DoesNotExist:
                return JsonResponse({'error': 'Review not found'}, status=404)
            
            # Prevent users from marking their own reviews as helpful
            if review.user_email == request.user.email:
                return JsonResponse({'error': 'You cannot mark your own review as helpful'}, status=400)
            
            if review.mark_helpful(request.user.email):
                logger.info(f"Review {review_id} marked helpful by {request.user.email}")
                return JsonResponse({
                    'success': True,
                    'helpful_count': review.helpful_count
                })
            else:
                return JsonResponse({'error': 'You already marked this review'}, status=400)
                
        except ValueError as e:
            return JsonResponse({'error': str(e)}, status=400)
        except Exception as e:
            logger.error(f"Mark helpful failed: {e}", exc_info=True)
            return JsonResponse({'error': 'Failed to mark review. Please try again.'}, status=500)


def get_product_reviews(request, product_id):
    """Get all reviews for a product."""
    try:
        product_id = validate_id(product_id)
        if not product_id:
            return JsonResponse({
                'error': 'Invalid product ID', 
                'reviews': [], 
                'total': 0, 
                'average_rating': 0, 
                'rating_distribution': {}
            }, status=400)
        
        # Check if product exists
        from products.models import Product
        try:
            Product.objects.get(id=product_id)
        except Product.DoesNotExist:
            return JsonResponse({
                'error': 'Product not found',
                'reviews': [],
                'total': 0,
                'average_rating': 0,
                'rating_distribution': {}
            }, status=404)
        
        reviews = ProductReview.objects.filter(
            product_id=product_id,
            is_approved=True
        ).order_by('-helpful_count', '-created_at')
        
        reviews_data = []
        for r in reviews:
            reviews_data.append({
                'id': r.id,
                'user_name': r.user_name,
                'rating': r.rating,
                'title': r.title,
                'review': r.review,
                'images': r.images if r.images else [],
                'is_verified': r.is_verified_purchase,
                'helpful_count': r.helpful_count,
                'pros': r.pros if r.pros else [],
                'cons': r.cons if r.cons else [],
                'created_at': r.created_at.strftime('%d %b, %Y') if r.created_at else ''
            })
        
        total = len(reviews_data)
        avg_rating = sum(r['rating'] for r in reviews_data) / total if total > 0 else 0
        
        rating_dist = {5: 0, 4: 0, 3: 0, 2: 0, 1: 0}
        for r in reviews_data:
            rating_dist[r['rating']] = rating_dist.get(r['rating'], 0) + 1
        
        return JsonResponse({
            'reviews': reviews_data,
            'total': total,
            'average_rating': round(avg_rating, 1),
            'rating_distribution': rating_dist
        })
    except Exception as e:
        logger.error(f"Failed to get product reviews: {e}", exc_info=True)
        return JsonResponse({
            'error': 'Failed to load reviews',
            'reviews': [],
            'total': 0,
            'average_rating': 0,
            'rating_distribution': {}
        }, status=500)
