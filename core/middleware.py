import time
import logging
from django.core.cache import cache
from django.http import JsonResponse
from django.conf import settings

logger = logging.getLogger(__name__)


class RateLimitMiddleware:
    """
    Rate limiting middleware to handle high traffic.
    Supports IP-based and user-based rate limiting.
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
        self.requests_limit = getattr(settings, 'RATE_LIMIT_REQUESTS', 100)
        self.period = getattr(settings, 'RATE_LIMIT_PERIOD', 60)
    
    def __call__(self, request):
        if self._should_rate_limit(request):
            return JsonResponse({
                'error': 'Too many requests. Please try again later.',
                'retry_after': self.period
            }, status=429)
        
        response = self.get_response(request)
        return response
    
    def _should_rate_limit(self, request):
        skip_paths = ['/static/', '/media/', '/admin/', '/health/', '/favicon.ico']
        if any(request.path.startswith(p) for p in skip_paths):
            return False
        
        key = self._get_cache_key(request)
        
        request_data = cache.get(key, {'count': 0, 'first_request': time.time()})
        
        current_time = time.time()
        
        if current_time - request_data['first_request'] > self.period:
            request_data = {'count': 1, 'first_request': current_time}
        else:
            request_data['count'] += 1
        
        limit = self._get_limit_for_request(request)
        
        if request_data['count'] > limit:
            logger.warning(f"Rate limit exceeded for {key}: {request_data['count']} requests")
            return True
        
        cache.set(key, request_data, self.period + 10)
        return False
    
    def _get_cache_key(self, request):
        if request.user.is_authenticated:
            return f"rate_limit:user:{request.user.id}"
        
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0].strip()
        else:
            ip = request.META.get('REMOTE_ADDR', '127.0.0.1')
        
        return f"rate_limit:ip:{ip}"
    
    def _get_limit_for_request(self, request):
        if request.user.is_authenticated:
            return self.requests_limit * 3
        
        if request.user.is_staff:
            return self.requests_limit * 10
        
        return self.requests_limit


class RequestLoggingMiddleware:
    """
    Request logging middleware for monitoring and debugging.
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
        self.logger = logging.getLogger('django.request')
    
    def __call__(self, request):
        start_time = time.time()
        
        response = self.get_response(request)
        
        duration = time.time() - start_time
        
        if duration > 1.0:
            self.logger.warning(
                f"Slow request: {request.method} {request.path} "
                f"took {duration:.2f}s (status: {response.status_code})"
            )
        
        return response
    
    def process_exception(self, request, exception):
        self.logger.error(
            f"Exception in {request.method} {request.path}: {str(exception)}",
            exc_info=True
        )
        return None


class SecurityHeadersMiddleware:
    """
    Add security headers to all responses.
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        response = self.get_response(request)
        
        response['X-Content-Type-Options'] = 'nosniff'
        response['X-Frame-Options'] = 'DENY'
        response['X-XSS-Protection'] = '1; mode=block'
        response['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        
        if not request.is_secure():
            response['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
        
        return response


class CacheControlMiddleware:
    """
    Add cache control headers for static and media files.
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        response = self.get_response(request)
        
        if request.path.startswith('/static/') or request.path.startswith('/media/'):
            response['Cache-Control'] = 'public, max-age=31536000'
        elif request.path.startswith('/api/'):
            response['Cache-Control'] = 'no-cache, no-store, must-revalidate'
        
        return response
