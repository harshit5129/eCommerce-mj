from django.urls import path
from users.api_views import RegisterAPIView, LoginAPIView, ProfileAPIView, LogoutAPIView

urlpatterns = [
    path('register/', RegisterAPIView.as_view(), name='api_register'),
    path('login/', LoginAPIView.as_view(), name='api_login'),
    path('logout/', LogoutAPIView.as_view(), name='api_logout'),
    path('profile/', ProfileAPIView.as_view(), name='api_profile'),
]
