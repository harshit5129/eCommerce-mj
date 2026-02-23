import time
import logging
from django.core.cache import cache
from django.http import JsonResponse
from django.conf import settings

logger = logging.getLogger(__name__)


class RateLimitMiddleware:
    """
    Rate limiting middleware using sliding window algorithm.
    Optimized to minimize cache operations.
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
        self.requests_limit = getattr(settings, 'RATE_LIMIT_REQUESTS', 100)
        self.period = getattr(settings, 'RATE_LIMIT_PERIOD', 60)
    
    def __call__(self, request):
        # Skip rate limiting for static/media/health/admin paths
        skip_paths = ('/static/', '/media/', '/admin/', '/my-admin/', '/health/', '/favicon.ico')
        if request.path.startswith(skip_paths):
            return self.get_response(request)
        
        key = self._get_cache_key(request)
        
        # Get current count
        request_data = cache.get(key)
        current_time = time.time()
        
        if request_data is None:
            request_data = {'count': 1, 'first_request': current_time}
        else:
            if current_time - request_data.get('first_request', 0) > self.period:
                request_data = {'count': 1, 'first_request': current_time}
            else:
                request_data['count'] = request_data.get('count', 0) + 1
        
        limit = self._get_limit_for_request(request)
        
        if request_data['count'] > limit:
            logger.warning(f"Rate limit exceeded for {key}")
            return JsonResponse({
                'error': 'Too many requests. Please try again later.',
                'retry_after': self.period
            }, status=429)
        
        cache.set(key, request_data, self.period + 10)
        return self.get_response(request)
    
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
            if request.user.is_staff or request.user.is_superuser:
                return self.requests_limit * 10
            return self.requests_limit * 3
        return self.requests_limit


class AuthenticationRateLimitMiddleware:
    """
    Rate limiting for authentication endpoints to prevent brute force.
    """
    
    AUTH_PATHS = ('/accounts/login/', '/accounts/signup/', '/api/users/login/', '/api/users/register/')
    
    def __init__(self, get_response):
        self.get_response = get_response
        self.max_attempts = getattr(settings, 'LOGIN_RATE_LIMIT_ATTEMPTS', 5)
        self.lockout_period = getattr(settings, 'LOGIN_RATE_LIMIT_PERIOD', 900)
    
    def __call__(self, request):
        if self._is_auth_path(request) and self._is_rate_limited(request):
            if request.path.startswith('/api/'):
                return JsonResponse({
                    'error': 'Too many login attempts. Please try again later.',
                    'retry_after': self.lockout_period
                }, status=429)
            
            from django.contrib import messages
            from django.shortcuts import redirect
            messages.error(request, 'Too many login attempts. Please try again in 15 minutes.')
            return redirect('login')
        
        response = self.get_response(request)
        
        # Record failed attempt
        if self._is_auth_path(request) and request.method == 'POST':
            if response.status_code in [401, 403]:
                self._record_failed_attempt(request)
        
        return response
    
    def _is_auth_path(self, request):
        return request.path.startswith(self.AUTH_PATHS)
    
    def _get_client_identifier(self, request):
        if request.method == 'POST':
            username = request.POST.get('email') or request.POST.get('username', '')
            if username:
                return f"auth:user:{username.lower()[:50]}"
        
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0].strip()
        else:
            ip = request.META.get('REMOTE_ADDR', '127.0.0.1')
        
        return f"auth:ip:{ip}"
    
    def _is_rate_limited(self, request):
        key = self._get_client_identifier(request)
        attempts = cache.get(key, 0)
        return attempts >= self.max_attempts
    
    def _record_failed_attempt(self, request):
        key = self._get_client_identifier(request)
        attempts = cache.get(key, 0)
        cache.set(key, attempts + 1, self.lockout_period)


class RequestLoggingMiddleware:
    """Request logging for slow requests."""
    
    def __init__(self, get_response):
        self.get_response = get_response
        self.logger = logging.getLogger('django.request')
        self.slow_threshold = 1.0
    
    def __call__(self, request):
        start_time = time.time()
        response = self.get_response(request)
        duration = time.time() - start_time
        
        if duration > self.slow_threshold:
            self.logger.warning(
                f"Slow request: {request.method} {request.path} "
                f"took {duration:.2f}s (status: {response.status_code})"
            )
        
        return response


class SecurityHeadersMiddleware:
    """Add security headers to all responses."""
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        response = self.get_response(request)
        
        response['X-Content-Type-Options'] = 'nosniff'
        response['X-Frame-Options'] = 'DENY'
        response['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        response['Permissions-Policy'] = 'geolocation=(), microphone=(), camera=()'
        
        # Content Security Policy
        csp_directives = [
            "default-src 'self'",
            "script-src 'self' 'unsafe-inline' 'unsafe-eval' https://cdn.jsdelivr.net https://code.jquery.com https://checkout.razorpay.com",
            "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com https://cdn.jsdelivr.net",
            "font-src 'self' https://fonts.gstatic.com https://cdn.jsdelivr.net",
            "img-src 'self' data: https: blob:",
            "connect-src 'self' https://api.razorpay.com https://lumberjack-cdn.razorpay.com",
            "frame-src 'self' https://api.razorpay.com https://checkout.razorpay.com",
            "object-src 'none'",
            "base-uri 'self'",
            "form-action 'self'",
        ]
        response['Content-Security-Policy'] = '; '.join(csp_directives)
        
        if request.is_secure():
            response['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains; preload'
        
        return response


class CacheControlMiddleware:
    """Add cache control headers."""
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        response = self.get_response(request)
        
        if request.path.startswith(('/static/', '/media/')):
            response['Cache-Control'] = 'public, max-age=31536000'
        elif request.path.startswith('/api/'):
            response['Cache-Control'] = 'no-cache, no-store, must-revalidate'
        
        return response
