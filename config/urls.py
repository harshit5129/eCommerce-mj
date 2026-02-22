from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView, SpectacularRedocView

import admin_urls

urlpatterns = [
    # Django Admin
    path('admin/', admin.site.urls),
    
    # Custom Admin Panel
    path('my-admin/', include(admin_urls.urlpatterns)),
    
    # Web Frontend
    path('', include('products.urls')),
    path('accounts/', include('users.urls')),
    path('accounts/', include('allauth.urls')),
    path('cart/', include('cart.urls')),
    path('orders/', include('orders.urls')),
    path('cookies/', include('cookies.urls')),
    path('my-admin/analytics/', include('analytics.urls')),
    path('', include('core.urls')),
    path('', include('pages.urls')),
    
    # API v1 - Versioned API
    path('api/v1/', include('api.v1.urls', namespace='v1')),
    
    # API Documentation
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('api/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),
    
    # Legacy API endpoints (redirect to v1)
    path('api/', include('products.api_urls')),
    path('api/auth/', include('users.api_urls')),
    path('api/cart/', include('cart.api_urls')),
    path('api/orders/', include('orders.api_urls')),
    path('api/offers/', include('offers.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
