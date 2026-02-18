from django.shortcuts import render, redirect
from django.views import View
from django.http import JsonResponse
from django.contrib import messages
from datetime import datetime
import json


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
                'timestamp': str(datetime.now())
            }
            request.session.modified = True
            
            return JsonResponse({
                'success': True,
                'message': 'Cookie preferences saved'
            })
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': str(e)
            }, status=400)


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
            'timestamp': str(datetime.now())
        }
        
        request.session['cookie_consent'] = preferences
        request.session.modified = True
        
        messages.success(request, 'Cookie preferences updated successfully!')
        return redirect('cookie_preferences')
