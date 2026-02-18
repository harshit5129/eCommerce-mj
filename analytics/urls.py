from django.urls import path
from analytics.views import track_page_view, track_event, AnalyticsDashboardView

urlpatterns = [
    path('pageview/', track_page_view, name='track_pageview'),
    path('event/', track_event, name='track_event'),
    path('dashboard/', AnalyticsDashboardView.as_view(), name='analytics_dashboard'),
]
