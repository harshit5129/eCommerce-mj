from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
import admin_urls

urlpatterns = [
    path('admin/', admin.site.urls),
    path('my-admin/', include(admin_urls.urlpatterns)),
    path('', include('products.urls')),
    path('accounts/', include('users.urls')),
    path('cart/', include('cart.urls')),
    path('orders/', include('orders.urls')),
    path('api/', include('products.api_urls')),
    path('api/auth/', include('users.api_urls')),
    path('api/cart/', include('cart.api_urls')),
    path('api/orders/', include('orders.api_urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
