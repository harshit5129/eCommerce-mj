"""
Custom exception handlers and error utilities for the E-Commerce API.
"""

import logging
import traceback
from django.http import JsonResponse
from django.core.exceptions import PermissionDenied, ValidationError
from django.http import Http404
from rest_framework.views import exception_handler as drf_exception_handler
from rest_framework.response import Response
from rest_framework import status
from rest_framework.exceptions import (
    APIException,
    Throttled,
    ValidationError as DRFValidationError,
    AuthenticationFailed,
    NotAuthenticated,
    PermissionDenied as DRFPermissionDenied,
    NotFound,
)

logger = logging.getLogger(__name__)


def custom_exception_handler(exc, context):
    """
    Custom exception handler for DRF that provides consistent error responses.
    """
    # Call REST framework's default exception handler first
    response = drf_exception_handler(exc, context)
    
    if response is not None:
        # Customize the response format
        custom_response = {
            'success': False,
            'error': {},
            'status_code': response.status_code,
        }
        
        # Handle different error types
        if isinstance(exc, DRFValidationError):
            custom_response['error'] = {
                'type': 'validation_error',
                'message': 'Validation failed',
                'details': response.data,
            }
        elif isinstance(exc, NotAuthenticated):
            custom_response['error'] = {
                'type': 'authentication_error',
                'message': 'Authentication required',
                'details': None,
            }
        elif isinstance(exc, AuthenticationFailed):
            custom_response['error'] = {
                'type': 'authentication_error',
                'message': 'Invalid credentials',
                'details': None,
            }
        elif isinstance(exc, DRFPermissionDenied):
            custom_response['error'] = {
                'type': 'permission_error',
                'message': 'Permission denied',
                'details': None,
            }
        elif isinstance(exc, NotFound):
            custom_response['error'] = {
                'type': 'not_found',
                'message': 'Resource not found',
                'details': None,
            }
        elif isinstance(exc, Throttled):
            custom_response['error'] = {
                'type': 'throttled',
                'message': 'Request was throttled',
                'details': {
                    'wait_seconds': exc.wait,
                },
            }
        else:
            import settings as django_settings
            if django_settings.DEBUG:
                custom_response['error'] = {
                    'type': 'error',
                    'message': str(exc) if str(exc) else 'An error occurred',
                    'details': response.data if response.data else None,
                }
            else:
                custom_response['error'] = {
                    'type': 'error',
                    'message': 'An error occurred',
                    'details': None,
                }
        
        response.data = custom_response
    
    # Log the exception
    if response and response.status_code >= 400:
        request = context.get('request')
        view = context.get('view')
        
        logger.error(
            f"API Exception: {exc.__class__.__name__} - {str(exc)}\n"
            f"View: {view.__class__.__name__ if view else 'Unknown'}\n"
            f"Path: {request.path if request else 'Unknown'}\n"
            f"Method: {request.method if request else 'Unknown'}\n"
            f"Status: {response.status_code}"
        )
    
    return response


class ECommerceAPIException(APIException):
    """
    Base exception for E-Commerce API with consistent error format.
    """
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = 'An error occurred.'
    default_code = 'error'
    
    def __init__(self, detail=None, code=None, **kwargs):
        super().__init__(detail, code)
        self.extra = kwargs


class InsufficientStockError(ECommerceAPIException):
    """Raised when product stock is insufficient."""
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = 'Insufficient stock available.'
    default_code = 'insufficient_stock'


class PaymentError(ECommerceAPIException):
    """Raised when payment processing fails."""
    status_code = status.HTTP_402_PAYMENT_REQUIRED
    default_detail = 'Payment processing failed.'
    default_code = 'payment_error'


class CouponError(ECommerceAPIException):
    """Raised when coupon validation fails."""
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = 'Invalid coupon.'
    default_code = 'coupon_error'


class CartError(ECommerceAPIException):
    """Raised when cart operation fails."""
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = 'Cart operation failed.'
    default_code = 'cart_error'


class OrderError(ECommerceAPIException):
    """Raised when order operation fails."""
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = 'Order operation failed.'
    default_code = 'order_error'


def handle_uncaught_exception(request, exception):
    """
    Handle uncaught exceptions in Django views.
    """
    logger.critical(
        f"Uncaught Exception: {exception.__class__.__name__}\n"
        f"Path: {request.path}\n"
        f"Method: {request.method}\n"
        f"Traceback: {traceback.format_exc()}"
    )
    
    # Return a generic error response
    return JsonResponse({
        'success': False,
        'error': {
            'type': 'server_error',
            'message': 'An unexpected error occurred. Please try again later.',
            'details': None,
        },
        'status_code': 500,
    }, status=500)


def handle_404_error(request, exception):
    """
    Handle 404 Not Found errors.
    """
    if request.path.startswith('/api/'):
        return JsonResponse({
            'success': False,
            'error': {
                'type': 'not_found',
                'message': 'The requested resource was not found.',
                'details': {'path': request.path},
            },
            'status_code': 404,
        }, status=404)
    
    # For non-API requests, let Django handle it normally
    from django.views.defaults import page_not_found
    return page_not_found(request, exception)


def handle_500_error(request):
    """
    Handle 500 Internal Server Error.
    """
    if request.path.startswith('/api/'):
        return JsonResponse({
            'success': False,
            'error': {
                'type': 'server_error',
                'message': 'An internal server error occurred.',
                'details': None,
            },
            'status_code': 500,
        }, status=500)
    
    from django.views.defaults import server_error
    return server_error(request)


def handle_403_error(request, exception):
    """
    Handle 403 Forbidden errors.
    """
    if request.path.startswith('/api/'):
        return JsonResponse({
            'success': False,
            'error': {
                'type': 'forbidden',
                'message': 'You do not have permission to access this resource.',
                'details': None,
            },
            'status_code': 403,
        }, status=403)
    
    from django.views.defaults import permission_denied
    return permission_denied(request, exception)


def handle_400_error(request, exception):
    """
    Handle 400 Bad Request errors.
    """
    if request.path.startswith('/api/'):
        return JsonResponse({
            'success': False,
            'error': {
                'type': 'bad_request',
                'message': 'Bad request.',
                'details': str(exception) if exception else None,
            },
            'status_code': 400,
        }, status=400)
    
    from django.views.defaults import bad_request
    return bad_request(request, exception)
