from django.urls import path
from analytics.views import TrackPageViewView, TrackEventView, AnalyticsDashboardView, GetAnalyticsCSRFView

urlpatterns = [
    path('csrf/', GetAnalyticsCSRFView.as_view(), name='analytics_csrf'),
    path('pageview/', TrackPageViewView.as_view(), name='track_pageview'),
    path('event/', TrackEventView.as_view(), name='track_event'),
    path('dashboard/', AnalyticsDashboardView.as_view(), name='analytics_dashboard'),
]
