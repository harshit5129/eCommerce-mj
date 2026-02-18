from django.http import JsonResponse
from django.views import View
from django.db import connection
import time


class HealthCheckView(View):
    """Health check endpoint for load balancers and monitoring."""
    
    def get(self, request):
        health = {
            'status': 'healthy',
            'timestamp': time.time(),
            'checks': {}
        }
        
        try:
            with connection.cursor() as cursor:
                cursor.execute('SELECT 1')
            health['checks']['database'] = 'ok'
        except Exception as e:
            health['checks']['database'] = f'error: {str(e)}'
            health['status'] = 'unhealthy'
        
        try:
            import mongoengine
            from config.settings.base import MONGODB_AVAILABLE
            if MONGODB_AVAILABLE:
                health['checks']['mongodb'] = 'ok'
            else:
                health['checks']['mongodb'] = 'unavailable'
        except Exception as e:
            health['checks']['mongodb'] = f'error: {str(e)}'
        
        try:
            from django.core.cache import cache
            cache.set('health_check', 'ok', 10)
            if cache.get('health_check') == 'ok':
                health['checks']['cache'] = 'ok'
            else:
                health['checks']['cache'] = 'error'
                health['status'] = 'degraded'
        except Exception as e:
            health['checks']['cache'] = f'error: {str(e)}'
            health['status'] = 'degraded'
        
        status_code = 200 if health['status'] == 'healthy' else 503
        
        return JsonResponse(health, status=status_code)


class ReadinessCheckView(View):
    """Readiness check for Kubernetes deployments."""
    
    def get(self, request):
        checks = []
        
        try:
            with connection.cursor() as cursor:
                cursor.execute('SELECT 1')
            checks.append(True)
        except Exception:
            checks.append(False)
        
        try:
            import mongoengine
            from config.settings.base import MONGODB_AVAILABLE
            checks.append(MONGODB_AVAILABLE)
        except Exception:
            checks.append(False)
        
        if all(checks):
            return JsonResponse({'ready': True}, status=200)
        return JsonResponse({'ready': False}, status=503)


class LivenessCheckView(View):
    """Liveness check for Kubernetes deployments."""
    
    def get(self, request):
        return JsonResponse({'alive': True}, status=200)
