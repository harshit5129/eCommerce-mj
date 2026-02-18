from django.http import JsonResponse
from django.views import View
from django.db import connection
from django.core.cache import cache
import time


class HealthCheckView(View):
    """Health check endpoint for load balancers and monitoring."""
    
    def get(self, request):
        health = {
            'status': 'healthy',
            'timestamp': time.time(),
            'checks': {}
        }
        
        # Check PostgreSQL
        try:
            with connection.cursor() as cursor:
                cursor.execute('SELECT 1')
            health['checks']['database'] = 'ok'
        except Exception as e:
            health['checks']['database'] = f'error: {str(e)}'
            health['status'] = 'unhealthy'
        
        # Check Redis/Cache (optional - don't fail if not available)
        try:
            cache.set('health_check', 'ok', 10)
            if cache.get('health_check') == 'ok':
                health['checks']['cache'] = 'ok'
            else:
                health['checks']['cache'] = 'not configured'
        except Exception as e:
            health['checks']['cache'] = 'not configured'
        
        # Return 200 even if cache fails - only fail on database
        status_code = 200 if health['checks'].get('database') == 'ok' else 503
        
        return JsonResponse(health, status=status_code)


class ReadinessCheckView(View):
    """Readiness check for Kubernetes deployments."""
    
    def get(self, request):
        checks = []
        
        # Check PostgreSQL
        try:
            with connection.cursor() as cursor:
                cursor.execute('SELECT 1')
            checks.append(True)
        except Exception:
            checks.append(False)
        
        if all(checks):
            return JsonResponse({'ready': True}, status=200)
        return JsonResponse({'ready': False}, status=503)


class LivenessCheckView(View):
    """Liveness check for Kubernetes deployments."""
    
    def get(self, request):
        return JsonResponse({'alive': True}, status=200)
