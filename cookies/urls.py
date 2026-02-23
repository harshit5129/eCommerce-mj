from django.urls import path
from cookies.views import CookieConsentView, CookiePreferencesView, GetCSRFTokenView

urlpatterns = [
    path('csrf/', GetCSRFTokenView.as_view(), name='get_csrf'),
    path('consent/', CookieConsentView.as_view(), name='cookie_consent'),
    path('preferences/', CookiePreferencesView.as_view(), name='cookie_preferences'),
]
