from django.urls import path
from core.views import HealthCheckView, ReadinessCheckView, LivenessCheckView

urlpatterns = [
    path('health/', HealthCheckView.as_view(), name='health_check'),
    path('ready/', ReadinessCheckView.as_view(), name='readiness_check'),
    path('alive/', LivenessCheckView.as_view(), name='liveness_check'),
]
