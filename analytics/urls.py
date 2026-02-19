from django.urls import path
from analytics.views import TrackPageViewView, TrackEventView, AnalyticsDashboardView

urlpatterns = [
    path('pageview/', TrackPageViewView.as_view(), name='track_pageview'),
    path('event/', TrackEventView.as_view(), name='track_event'),
    path('dashboard/', AnalyticsDashboardView.as_view(), name='analytics_dashboard'),
]
