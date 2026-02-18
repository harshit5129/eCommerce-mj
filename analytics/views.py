from django.shortcuts import render, redirect
from django.views import View
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from datetime import datetime
import json

from products.models import Product
from orders.models import Order


class AnalyticsEvent:
    """Simple analytics event storage using MongoDB."""
    
    @staticmethod
    def track(event_type, data, request=None):
        """Track an analytics event."""
        from mongoengine import Document, StringField, DictField, DateTimeField
        
        class Event(Document):
            event_type = StringField(required=True)
            data = DictField(default=dict)
            session_id = StringField()
            user_id = StringField()
            user_agent = StringField()
            ip_address = StringField()
            created_at = DateTimeField(default=datetime.utcnow)
            
            meta = {'collection': 'analytics_events'}
        
        event = Event(
            event_type=event_type,
            data=data,
        )
        
        if request:
            event.session_id = request.session.session_key or request.session.get('user_id', 'anonymous')
            event.user_id = str(request.session.get('user_id', 'anonymous'))
            event.user_agent = request.META.get('HTTP_USER_AGENT', '')[:500]
            event.ip_address = request.META.get('REMOTE_ADDR', '')
            
            if not request.session.session_key:
                request.session.create()
        
        try:
            event.save()
            return True
        except:
            return False


@csrf_exempt
def track_page_view(request):
    """Track a page view."""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            AnalyticsEvent.track('page_view', {
                'path': data.get('path', ''),
                'title': data.get('title', ''),
                'referrer': data.get('referrer', ''),
            }, request)
            return JsonResponse({'success': True})
        except:
            return JsonResponse({'success': False}, status=400)
    return JsonResponse({'error': 'Invalid method'}, status=405)


@csrf_exempt
def track_event(request):
    """Track a custom event."""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            AnalyticsEvent.track(
                data.get('event_type', 'custom'),
                data.get('data', {}),
                request
            )
            return JsonResponse({'success': True})
        except:
            return JsonResponse({'success': False}, status=400)
    return JsonResponse({'error': 'Invalid method'}, status=405)


class AnalyticsDashboardView(View):
    """Admin analytics dashboard."""
    
    template_name = 'admin/analytics/dashboard.html'
    
    def get(self, request):
        from pymongo import MongoClient
        
        client = MongoClient('localhost', 27017)
        db = client['ecomm_db']
        
        events = db.analytics_events
        
        total_page_views = events.count_documents({'event_type': 'page_view'})
        
        pipeline = [
            {'$match': {'event_type': 'page_view'}},
            {'$group': {'_id': '$data.path', 'count': {'$sum': 1}}},
            {'$sort': {'count': -1}},
            {'$limit': 10}
        ]
        top_pages_raw = list(events.aggregate(pipeline))
        top_pages = [{'path': p['_id'], 'count': p['count']} for p in top_pages_raw]
        
        pipeline = [
            {'$match': {'event_type': 'page_view'}},
            {'$group': {
                '_id': {
                    'year': {'$year': '$created_at'},
                    'month': {'$month': '$created_at'},
                    'day': {'$dayOfMonth': '$created_at'}
                },
                'count': {'$sum': 1}
            }},
            {'$sort': {'_id': -1}},
            {'$limit': 30}
        ]
        daily_views_raw = list(events.aggregate(pipeline))
        daily_views = [
            {
                'day': d['_id'].get('day', 1),
                'month': d['_id'].get('month', 1),
                'count': d['count']
            }
            for d in daily_views_raw
        ]
        
        pipeline = [
            {'$match': {'event_type': {'$ne': 'page_view'}}},
            {'$group': {'_id': '$event_type', 'count': {'$sum': 1}}},
            {'$sort': {'count': -1}}
        ]
        event_counts_raw = list(events.aggregate(pipeline))
        event_counts = [{'name': e['_id'], 'count': e['count']} for e in event_counts_raw]
        
        total_events = events.count_documents({})
        
        context = {
            'total_page_views': total_page_views,
            'total_events': total_events,
            'top_pages': top_pages,
            'daily_views': daily_views,
            'event_counts': event_counts,
        }
        
        return render(request, self.template_name, context)
