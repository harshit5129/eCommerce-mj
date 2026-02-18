from django.urls import path
from pages.views import (
    TermsView, PrivacyView, RefundView, HelpView, ContactView, AboutView
)

urlpatterns = [
    path('terms/', TermsView.as_view(), name='terms'),
    path('privacy/', PrivacyView.as_view(), name='privacy'),
    path('refund/', RefundView.as_view(), name='refund'),
    path('help/', HelpView.as_view(), name='help'),
    path('contact/', ContactView.as_view(), name='contact'),
    path('about/', AboutView.as_view(), name='about'),
]
