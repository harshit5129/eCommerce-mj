"""
Custom throttling classes for the E-Commerce API.
"""

from rest_framework.throttling import AnonRateThrottle, UserRateThrottle


class AnonBurstRateThrottle(AnonRateThrottle):
    """
    Throttle class for anonymous users with burst rate limiting.
    Used to prevent rapid-fire requests from unauthenticated users.
    """
    scope = 'anon_burst'
    
    def get_rate(self):
        return '60/minute'


class AnonSustainedRateThrottle(AnonRateThrottle):
    """
    Throttle class for anonymous users with sustained rate limiting.
    Limits overall API usage for anonymous users.
    """
    scope = 'anon_sustained'
    
    def get_rate(self):
        return '1000/day'


class UserBurstRateThrottle(UserRateThrottle):
    """
    Throttle class for authenticated users with burst rate limiting.
    """
    scope = 'user_burst'
    
    def get_rate(self):
        return '300/minute'


class UserSustainedRateThrottle(UserRateThrottle):
    """
    Throttle class for authenticated users with sustained rate limiting.
    """
    scope = 'user_sustained'
    
    def get_rate(self):
        return '10000/day'


class AuthRateThrottle(AnonRateThrottle):
    """
    Strict throttling for authentication endpoints (login, register, password reset).
    Helps prevent brute force attacks.
    """
    scope = 'auth'
    
    def get_rate(self):
        return '10/minute'


class PasswordResetRateThrottle(AnonRateThrottle):
    """
    Rate limiting for password reset endpoints.
    Prevents email flooding.
    """
    scope = 'password_reset'
    
    def get_rate(self):
        return '3/hour'


class OrderCreationRateThrottle(UserRateThrottle):
    """
    Rate limiting for order creation to prevent abuse.
    """
    scope = 'order_creation'
    
    def get_rate(self):
        return '20/hour'


class SearchRateThrottle(AnonRateThrottle):
    """
    Rate limiting for search endpoints to prevent resource exhaustion.
    """
    scope = 'search'
    
    def get_rate(self):
        return '30/minute'


class StaffUserRateThrottle(UserRateThrottle):
    """
    Higher rate limits for staff/admin users.
    """
    scope = 'staff'
    
    def get_rate(self):
        return '1000/minute'
    
    def allow_request(self, request, view):
        # Allow higher limits for staff
        if request.user.is_staff or request.user.is_superuser:
            return True
        return super().allow_request(request, view)
