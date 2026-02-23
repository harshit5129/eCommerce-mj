import json
import logging
from django.shortcuts import render
from django.views import View
from django.http import JsonResponse
from django.views.decorators.csrf import ensure_csrf_cookie
from django.utils.decorators import method_decorator
from django.core.cache import cache
from django.db import models
from django.conf import settings
from django.contrib.auth.decorators import login_required, user_passes_test
from django.views.decorators.csrf import csrf_protect

logger = logging.getLogger(__name__)


def is_staff_user(user):
    return user.is_authenticated and (user.is_staff or user.is_superuser)


class GetAnalyticsCSRFView(View):
    """Get CSRF token for analytics tracking."""
    
    @method_decorator(ensure_csrf_cookie)
    def get(self, request):
        return JsonResponse({'success': True})


class AnalyticsEvent:
    """Simple analytics event storage using cache/database."""
    
    @staticmethod
    def track(event_type, data, request=None):
        """Track an analytics event - stored in cache with periodic flush to database."""
        event = {
            'event_type': event_type,
            'data': data,
            'session_id': request.session.session_key if request else None,
            'user_id': str(request.user.id) if request and request.user.is_authenticated else None,
            'user_agent': request.META.get('HTTP_USER_AGENT', '')[:500] if request else None,
            'ip_address': request.META.get('REMOTE_ADDR', '') if request else None,
        }
        
        try:
            # Store in cache list (for batching)
            cache_key = 'analytics_events_pending'
            events = cache.get(cache_key, [])
            events.append(event)
            # Keep last 1000 events in cache
            if len(events) > 1000:
                events = events[-1000:]
            cache.set(cache_key, events, 86400)  # 24 hours
            
            # Increment counters
            counter_key = f'analytics:counter:{event_type}'
            cache.incr(counter_key) if cache.get(counter_key) else cache.set(counter_key, 1, 86400)
            
            return True
        except Exception as e:
            logger.error(f"Analytics tracking failed: {e}")
            return False


@method_decorator(csrf_protect, name='dispatch')
class TrackPageViewView(View):
    """Track a page view with CSRF protection."""
    
    def post(self, request):
        try:
            data = json.loads(request.body)
            AnalyticsEvent.track('page_view', {
                'path': data.get('path', '')[:500],
                'title': data.get('title', '')[:200],
                'referrer': data.get('referrer', '')[:500],
            }, request)
            return JsonResponse({'success': True})
        except Exception as e:
            logger.error(f"Page view tracking failed: {e}")
            return JsonResponse({'success': False}, status=400)


@method_decorator(csrf_protect, name='dispatch')
class TrackEventView(View):
    """Track a custom event with CSRF protection."""
    
    def post(self, request):
        try:
            data = json.loads(request.body)
            AnalyticsEvent.track(
                data.get('event_type', 'custom')[:50],
                data.get('data', {}),
                request
            )
            return JsonResponse({'success': True})
        except Exception as e:
            logger.error(f"Event tracking failed: {e}")
            return JsonResponse({'success': False}, status=400)


class AnalyticsDashboardView(View):
    """Admin analytics dashboard using cache data."""
    
    template_name = 'admin/analytics/dashboard.html'
    
    @method_decorator(login_required)
    @method_decorator(user_passes_test(is_staff_user, login_url='/accounts/login/'))
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)
    
    def get(self, request):
        total_page_views = cache.get('analytics:counter:page_view', 0)
        total_events = sum(cache.get(f'analytics:counter:{t}', 0) for t in [
            'page_view', 'add_to_cart', 'order_created', 'search'
        ])
        
        events = cache.get('analytics_events_pending', [])[-100:]
        
        path_counts = {}
        for event in events:
            if event.get('event_type') == 'page_view':
                path = event.get('data', {}).get('path', '/')
                path_counts[path] = path_counts.get(path, 0) + 1
        
        top_pages = [
            {'path': k, 'count': v}
            for k, v in sorted(path_counts.items(), key=lambda x: -x[1])[:10]
        ]
        
        event_counts = [
            {'name': t, 'count': cache.get(f'analytics:counter:{t}', 0)}
            for t in ['page_view', 'add_to_cart', 'order_created', 'search']
        ]
        
        context = {
            'total_page_views': total_page_views,
            'total_events': total_events,
            'top_pages': top_pages,
            'daily_views': [],
            'event_counts': event_counts,
        }
        
        return render(request, self.template_name, context)
