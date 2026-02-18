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
        # Staff and superusers get highest limits
        if request.user.is_staff or request.user.is_superuser:
            return self.requests_limit * 10
        
        # Authenticated users get higher limits than anonymous
        if request.user.is_authenticated:
            return self.requests_limit * 3
        
        # Anonymous users get base limit
        return self.requests_limit


class AuthenticationRateLimitMiddleware:
    """
    Rate limiting specifically for authentication endpoints.
    Prevents brute force attacks on login.
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
        self.max_attempts = getattr(settings, 'LOGIN_RATE_LIMIT_ATTEMPTS', 5)
        self.lockout_period = getattr(settings, 'LOGIN_RATE_LIMIT_PERIOD', 900)  # 15 minutes
    
    def __call__(self, request):
        # Only apply to login-related paths
        if self._is_login_path(request):
            if self._is_rate_limited(request):
                if request.path.startswith('/api/'):
                    return JsonResponse({
                        'error': 'Too many login attempts. Please try again later.',
                        'retry_after': self.lockout_period
                    }, status=429)
                else:
                    from django.contrib import messages
                    messages.error(request, 'Too many login attempts. Please try again in 15 minutes.')
                    from django.shortcuts import redirect
                    return redirect('login')
        
        response = self.get_response(request)
        
        # Record failed login attempt
        if self._is_login_path(request) and request.method == 'POST':
            if response.status_code in [401, 403] or (hasattr(response, 'content') and b'error' in response.content.lower()):
                self._record_failed_attempt(request)
        
        return response
    
    def _is_login_path(self, request):
        """Check if this is a login/authentication path."""
        login_paths = [
            '/accounts/login/',
            '/accounts/signup/',
            '/api/users/login/',
            '/api/users/register/',
        ]
        return any(request.path.startswith(path) for path in login_paths)
    
    def _get_client_identifier(self, request):
        """Get unique identifier for rate limiting."""
        # Use username if available in POST data, otherwise use IP
        if request.method == 'POST':
            username = request.POST.get('email') or request.POST.get('username', '')
            if username:
                return f"auth:user:{username.lower()}"
        
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0].strip()
        else:
            ip = request.META.get('REMOTE_ADDR', '127.0.0.1')
        
        return f"auth:ip:{ip}"
    
    def _is_rate_limited(self, request):
        """Check if client is currently rate limited."""
        key = self._get_client_identifier(request)
        attempts = cache.get(key, 0)
        return attempts >= self.max_attempts
    
    def _record_failed_attempt(self, request):
        """Record a failed authentication attempt."""
        key = self._get_client_identifier(request)
        attempts = cache.get(key, 0)
        cache.set(key, attempts + 1, self.lockout_period)
        
        if attempts + 1 >= self.max_attempts:
            logger.warning(f"Rate limit activated for {key}")


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
        
        # Basic security headers
        response['X-Content-Type-Options'] = 'nosniff'
        response['X-Frame-Options'] = 'DENY'
        response['X-XSS-Protection'] = '1; mode=block'
        response['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        response['Permissions-Policy'] = 'geolocation=(), microphone=(), camera=()'
        response['Cross-Origin-Opener-Policy'] = 'same-origin'
        response['Cross-Origin-Resource-Policy'] = 'same-origin'
        
        # Content Security Policy
        csp_directives = [
            "default-src 'self'",
            "script-src 'self' https://cdn.tailwindcss.com https://code.jquery.com 'unsafe-inline'",
            "style-src 'self' https://fonts.googleapis.com 'unsafe-inline'",
            "font-src 'self' https://fonts.gstatic.com",
            "img-src 'self' data: https:",
            "connect-src 'self'",
            "frame-ancestors 'none'",
            "base-uri 'self'",
            "form-action 'self'"
        ]
        response['Content-Security-Policy'] = '; '.join(csp_directives)
        
        # HSTS - only on HTTPS connections
        if request.is_secure():
            response['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains; preload'
        
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
