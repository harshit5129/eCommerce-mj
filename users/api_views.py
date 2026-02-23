from datetime import datetime
from django.utils import timezone
from rest_framework import generics, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import get_user_model
from django.core.exceptions import ObjectDoesNotExist
import logging

logger = logging.getLogger(__name__)

User = get_user_model()

from users.serializers import UserSerializer, RegisterSerializer, LoginSerializer


class RegisterAPIView(generics.CreateAPIView):
    """
    Register a new user.
    """
    serializer_class = RegisterSerializer
    permission_classes = [AllowAny]
    
    def create(self, request, *args, **kwargs):
        try:
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            
            user = User.objects.create_user(
                email=serializer.validated_data['email'],
                username=serializer.validated_data['username'],
                password=serializer.validated_data['password'],
                first_name=serializer.validated_data.get('first_name', ''),
                last_name=serializer.validated_data.get('last_name', '')
            )
            
            refresh = RefreshToken.for_user(user)
            
            return Response({
                'success': True,
                'user': UserSerializer(user).data,
                'tokens': {
                    'refresh': str(refresh),
                    'access': str(refresh.access_token),
                }
            }, status=status.HTTP_201_CREATED)
        except Exception as e:
            logger.error(f"Registration failed: {e}", exc_info=True)
            return Response({
                'success': False,
                'error': {
                    'type': 'registration_error',
                    'message': 'Registration failed. Please try again.',
                    'details': None
                },
                'status_code': status.HTTP_400_BAD_REQUEST
            }, status=status.HTTP_400_BAD_REQUEST)


class LoginAPIView(generics.GenericAPIView):
    """
    Login user and return JWT tokens.
    """
    serializer_class = LoginSerializer
    permission_classes = [AllowAny]
    
    def post(self, request, *args, **kwargs):
        try:
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            
            email = serializer.validated_data['email']
            password = serializer.validated_data['password']
            
            try:
                user = User.objects.get(email=email)
            except User.DoesNotExist:
                logger.warning(f"Login attempt with non-existent email: {email}")
                return Response({
                    'success': False,
                    'error': {
                        'type': 'authentication_error',
                        'message': 'Invalid credentials',
                        'details': None
                    },
                    'status_code': status.HTTP_401_UNAUTHORIZED
                }, status=status.HTTP_401_UNAUTHORIZED)
            
            if not user.check_password(password):
                logger.warning(f"Failed login attempt for user: {email}")
                return Response({
                    'success': False,
                    'error': {
                        'type': 'authentication_error',
                        'message': 'Invalid credentials',
                        'details': None
                    },
                    'status_code': status.HTTP_401_UNAUTHORIZED
                }, status=status.HTTP_401_UNAUTHORIZED)
            
            if not user.is_active:
                return Response({
                    'success': False,
                    'error': {
                        'type': 'authentication_error',
                        'message': 'Account is disabled',
                        'details': None
                    },
                    'status_code': status.HTTP_401_UNAUTHORIZED
                }, status=status.HTTP_401_UNAUTHORIZED)
            
            user.last_login = timezone.now()
            user.save()
            
            refresh = RefreshToken.for_user(user)
            
            logger.info(f"User logged in: {email}")
            
            return Response({
                'success': True,
                'user': UserSerializer(user).data,
                'tokens': {
                    'refresh': str(refresh),
                    'access': str(refresh.access_token),
                }
            })
        except Exception as e:
            logger.error(f"Login failed: {e}", exc_info=True)
            return Response({
                'success': False,
                'error': {
                    'type': 'authentication_error',
                    'message': 'Login failed. Please try again.',
                    'details': None
                },
                'status_code': status.HTTP_400_BAD_REQUEST
            }, status=status.HTTP_400_BAD_REQUEST)


class ProfileAPIView(generics.RetrieveUpdateAPIView):
    """
    Get or update user profile.
    """
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]
    
    def get_object(self):
        return self.request.user
    
    def retrieve(self, request, *args, **kwargs):
        try:
            instance = self.get_object()
            serializer = self.get_serializer(instance)
            return Response({
                'success': True,
                'user': serializer.data
            })
        except Exception as e:
            logger.error(f"Profile retrieve failed: {e}", exc_info=True)
            return Response({
                'success': False,
                'error': {
                    'type': 'server_error',
                    'message': 'Failed to retrieve profile',
                    'details': None
                },
                'status_code': status.HTTP_500_INTERNAL_SERVER_ERROR
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def update(self, request, *args, **kwargs):
        try:
            user = self.get_object()
            
            user.first_name = request.data.get('first_name', user.first_name)[:50]
            user.last_name = request.data.get('last_name', user.last_name)[:50]
            user.phone = request.data.get('phone', user.phone)[:20]
            user.save()
            
            serializer = self.get_serializer(user)
            logger.info(f"Profile updated for user: {user.email}")
            
            return Response({
                'success': True,
                'user': serializer.data
            })
        except Exception as e:
            logger.error(f"Profile update failed: {e}", exc_info=True)
            return Response({
                'success': False,
                'error': {
                    'type': 'server_error',
                    'message': 'Failed to update profile',
                    'details': None
                },
                'status_code': status.HTTP_500_INTERNAL_SERVER_ERROR
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class LogoutAPIView(APIView):
    """
    Logout user (blacklist refresh token).
    """
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        try:
            refresh_token = request.data.get('refresh')
            if refresh_token:
                token = RefreshToken(refresh_token)
                token.blacklist()
            logger.info(f"User logged out: {request.user.email}")
            return Response({
                'success': True,
                'message': 'Logout successful'
            })
        except Exception as e:
            logger.error(f"Logout failed: {e}", exc_info=True)
            return Response({
                'success': False,
                'error': {
                    'type': 'logout_error',
                    'message': 'Logout failed',
                    'details': None
                },
                'status_code': status.HTTP_400_BAD_REQUEST
            }, status=status.HTTP_400_BAD_REQUEST)
