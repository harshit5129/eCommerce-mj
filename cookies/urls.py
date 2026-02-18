from django.urls import path
from cookies.views import CookieConsentView, CookiePreferencesView

urlpatterns = [
    path('consent/', CookieConsentView.as_view(), name='cookie_consent'),
    path('preferences/', CookiePreferencesView.as_view(), name='cookie_preferences'),
]
