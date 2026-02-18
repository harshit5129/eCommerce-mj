from django.shortcuts import render, redirect
from django.views import View
from django.http import JsonResponse
from django.contrib import messages
from datetime import datetime
import json

from offers.models import Coupon, CouponUsage, LimitedOffer, ProductReview


class ApplyCouponView(View):
    """Apply coupon to cart."""
    
    def post(self, request):
        try:
            data = json.loads(request.body)
            code = data.get('code', '').strip().upper()
            cart_total = float(data.get('cart_total', 0))
            user_email = request.session.get('user_email', '')
            
            coupon = Coupon.objects(code=code, is_active=True).first()
            
            if not coupon:
                return JsonResponse({'error': 'Invalid coupon code'}, status=400)
            
            if not coupon.is_valid:
                return JsonResponse({'error': 'This coupon has expired or reached its usage limit'}, status=400)
            
            can_use, msg = coupon.can_use(user_email)
            if not can_use:
                return JsonResponse({'error': msg}, status=400)
            
            if cart_total < coupon.min_order_value:
                return JsonResponse({
                    'error': f'Minimum order value is ₹{coupon.min_order_value:,.0f}'
                }, status=400)
            
            if user_email:
                user_usage = CouponUsage.objects(coupon_id=coupon.id, user_email=user_email).count()
                if user_usage >= coupon.per_user_limit:
                    return JsonResponse({
                        'error': f'You have already used this coupon {user_usage} time(s)'
                    }, status=400)
            
            discount = coupon.calculate_discount(cart_total)
            
            request.session['applied_coupon'] = {
                'id': str(coupon.id),
                'code': coupon.code,
                'discount': discount,
                'discount_type': coupon.discount_type,
                'discount_value': coupon.discount_value
            }
            request.session.modified = True
            
            return JsonResponse({
                'success': True,
                'message': f'Coupon applied! You save ₹{discount:,.0f}',
                'discount': discount,
                'coupon_code': coupon.code,
                'discount_type': coupon.discount_type
            })
            
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)


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
        now = datetime.utcnow()
        offers = LimitedOffer.objects(
            is_active=True,
            starts_at__lte=now,
            ends_at__gte=now
        ).order_by('-created_at')
        
        offers_data = []
        for offer in offers:
            offers_data.append({
                'id': str(offer.id),
                'name': offer.name,
                'slug': offer.slug,
                'description': offer.description,
                'offer_type': offer.offer_type,
                'discount_value': offer.discount_value,
                'discount_type': offer.discount_type,
                'time_remaining': offer.time_remaining,
                'banner_image': offer.banner_image,
                'banner_text': offer.banner_text,
            })
        
        return JsonResponse({'offers': offers_data})


class SubmitReviewView(View):
    """Submit a product review."""
    
    def post(self, request):
        try:
            data = json.loads(request.body)
            
            product_id = data.get('product_id')
            rating = int(data.get('rating', 0))
            title = data.get('title', '').strip()
            review_text = data.get('review', '').strip()
            pros = data.get('pros', [])
            cons = data.get('cons', [])
            
            user_email = request.session.get('user_email')
            user_name = request.session.get('username', 'Anonymous')
            
            if not user_email:
                return JsonResponse({'error': 'Please login to submit a review'}, status=401)
            
            if not product_id or rating < 1 or rating > 5:
                return JsonResponse({'error': 'Invalid review data'}, status=400)
            
            existing = ProductReview.objects(product_id=product_id, user_email=user_email).first()
            if existing:
                return JsonResponse({'error': 'You have already reviewed this product'}, status=400)
            
            is_verified = False
            order_number = None
            from orders.models import Order
            orders = Order.objects(user_email=user_email)
            for order in orders:
                for item in order.items:
                    if item.product_id == product_id:
                        is_verified = True
                        order_number = order.order_number
                        break
            
            review = ProductReview(
                product_id=product_id,
                user_email=user_email,
                user_name=user_name,
                rating=rating,
                title=title,
                review=review_text,
                pros=pros,
                cons=cons,
                is_verified_purchase=is_verified,
                order_number=order_number
            )
            review.save()
            
            return JsonResponse({
                'success': True,
                'message': 'Thank you for your review!',
                'is_verified': is_verified
            })
            
        except Exception as e:
            import traceback
            traceback.print_exc()
            return JsonResponse({'error': str(e)}, status=500)


class MarkReviewHelpfulView(View):
    """Mark a review as helpful."""
    
    def post(self, request):
        try:
            data = json.loads(request.body)
            review_id = data.get('review_id')
            user_email = request.session.get('user_email')
            
            if not user_email:
                return JsonResponse({'error': 'Please login'}, status=401)
            
            from bson import ObjectId
            review = ProductReview.objects.get(id=ObjectId(review_id))
            
            if review.mark_helpful(user_email):
                return JsonResponse({
                    'success': True,
                    'helpful_count': review.helpful_count
                })
            else:
                return JsonResponse({'error': 'You already marked this review'}, status=400)
                
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)


def get_product_reviews(request, product_id):
    """Get all reviews for a product."""
    from bson import ObjectId
    
    reviews = ProductReview.objects(
        product_id=ObjectId(product_id),
        is_approved=True
    ).order_by('-helpful_count', '-created_at')
    
    reviews_data = []
    for r in reviews:
        reviews_data.append({
            'id': str(r.id),
            'user_name': r.user_name,
            'rating': r.rating,
            'title': r.title,
            'review': r.review,
            'images': r.images,
            'is_verified': r.is_verified_purchase,
            'helpful_count': r.helpful_count,
            'pros': r.pros,
            'cons': r.cons,
            'created_at': r.created_at.strftime('%d %b, %Y')
        })
    
    total = len(reviews_data)
    avg_rating = sum(r['rating'] for r in reviews_data) / total if total > 0 else 0
    
    rating_dist = {'5': 0, '4': 0, '3': 0, '2': 0, '1': 0}
    for r in reviews_data:
        rating_dist[str(r['rating'])] = rating_dist.get(str(r['rating']), 0) + 1
    
    return JsonResponse({
        'reviews': reviews_data,
        'total': total,
        'average_rating': round(avg_rating, 1),
        'rating_distribution': rating_dist
    })
