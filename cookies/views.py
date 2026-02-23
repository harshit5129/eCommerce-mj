from django.shortcuts import render, redirect
from django.views import View
from django.http import JsonResponse
from django.contrib import messages
from django.utils import timezone
from django.views.decorators.csrf import ensure_csrf_cookie
from django.utils.decorators import method_decorator
import json
import logging

logger = logging.getLogger(__name__)


class GetCSRFTokenView(View):
    """Get CSRF token for frontend JavaScript requests."""
    
    @method_decorator(ensure_csrf_cookie)
    def get(self, request):
        return JsonResponse({'success': True})


class CookieConsentView(View):
    """Handle cookie consent."""
    
    def post(self, request):
        try:
            data = json.loads(request.body)
            consent = data.get('consent', {})
            
            request.session['cookie_consent'] = {
                'necessary': True,
                'analytics': consent.get('analytics', False),
                'marketing': consent.get('marketing', False),
                'timestamp': timezone.now().isoformat()
            }
            request.session.modified = True
            
            return JsonResponse({
                'success': True,
                'message': 'Cookie preferences saved'
            })
        except json.JSONDecodeError:
            return JsonResponse({
                'success': False,
                'error': 'Invalid JSON data'
            }, status=400)
        except Exception as e:
            logger.error(f"Cookie consent error: {e}", exc_info=True)
            return JsonResponse({
                'success': False,
                'error': 'An error occurred'
            }, status=500)


class CookiePreferencesView(View):
    """View and update cookie preferences."""
    
    template_name = 'cookies/preferences.html'
    
    def get(self, request):
        preferences = request.session.get('cookie_consent', {
            'necessary': True,
            'analytics': False,
            'marketing': False,
        })
        
        return render(request, self.template_name, {
            'preferences': preferences
        })
    
    def post(self, request):
        preferences = {
            'necessary': True,
            'analytics': request.POST.get('analytics') == 'on',
            'marketing': request.POST.get('marketing') == 'on',
            'timestamp': timezone.now().isoformat()
        }
        
        request.session['cookie_consent'] = preferences
        request.session.modified = True
        
        messages.success(request, 'Cookie preferences updated successfully!')
        return redirect('cookie_preferences')
