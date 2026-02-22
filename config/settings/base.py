import os
from pathlib import Path
from django.core.exceptions import ImproperlyConfigured
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent.parent


def get_setting(key, default=None, required=False):
    """
    Get setting from database first, then fall back to environment variable.
    This allows admin to override settings from the setup page.
    """
    try:
        from core.models import SiteConfiguration
        db_value = SiteConfiguration.get(key, None)
        if db_value is not None:
            return db_value
    except Exception:
        pass
    
    env_value = os.getenv(key, default)
    
    if required and env_value is None:
        raise ImproperlyConfigured(f'{key} is required but not set')
    
    return env_value


SECRET_KEY = get_setting('SECRET_KEY')

DEBUG = str(get_setting('DEBUG', 'False')).lower() == 'true'

if not SECRET_KEY:
    if DEBUG:
        import secrets
        SECRET_KEY = secrets.token_urlsafe(50)
    else:
        raise ImproperlyConfigured('SECRET_KEY environment variable is required in production')

ALLOWED_HOSTS = str(get_setting('ALLOWED_HOSTS', 'localhost,127.0.0.1')).split(',')

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.humanize',
    
    # Third party
    'django.contrib.sites',
    'rest_framework',
    'rest_framework_simplejwt',
    'corsheaders',
    'django_filters',
    'allauth',
    'allauth.account',
    'allauth.socialaccount',
    'allauth.socialaccount.providers.google',
    'drf_spectacular',
    
    # Local apps (using AppConfig paths)
    'core.apps.CoreConfig',
    'users.apps.UsersConfig',
    'products.apps.ProductsConfig',
    'cart.apps.CartConfig',
    'orders.apps.OrdersConfig',
    'analytics.apps.AnalyticsConfig',
    'cookies.apps.CookiesConfig',
    'pages.apps.PagesConfig',
    'offers.apps.OffersConfig',
]

SITE_ID = 1

AUTHENTICATION_BACKENDS = (
    'django.contrib.auth.backends.ModelBackend',
    'allauth.account.auth_backends.AuthenticationBackend',
)

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'allauth.account.middleware.AccountMiddleware',
    'core.middleware.SecurityHeadersMiddleware',
    'core.middleware.RateLimitMiddleware',
    'core.middleware.AuthenticationRateLimitMiddleware',
    'core.middleware.RequestLoggingMiddleware',
    'core.middleware.CacheControlMiddleware',
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
                'context_processors': [
                    'django.template.context_processors.debug',
                    'django.template.context_processors.request',
                    'django.contrib.auth.context_processors.auth',
                    'django.contrib.messages.context_processors.messages',
                    'cart.context_processors.cart',
                    'cart.context_processors.wishlist',
                ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'

# PostgreSQL Configuration
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': get_setting('DB_NAME', 'ecomm_db'),
        'USER': get_setting('DB_USER', 'postgres'),
        'PASSWORD': get_setting('DB_PASSWORD', ''),
        'HOST': get_setting('DB_HOST', 'localhost'),
        'PORT': get_setting('DB_PORT', '5432'),
        'OPTIONS': {
            'connect_timeout': 10,
        },
    }
}

# Connection pooling for PostgreSQL (production)
if not DEBUG:
    DATABASES['default']['OPTIONS']['MAX_CONNS'] = 20
    DATABASES['default']['OPTIONS']['MIN_CONNS'] = 5

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

STATIC_URL = 'static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = BASE_DIR / 'staticfiles'

MEDIA_URL = 'media/'
MEDIA_ROOT = BASE_DIR / 'media'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

AUTH_USER_MODEL = 'users.User'

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ),
    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.IsAuthenticatedOrReadOnly',
    ),
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 12,
    'DEFAULT_FILTER_BACKENDS': (
        'django_filters.rest_framework.DjangoFilterBackend',
        'rest_framework.filters.SearchFilter',
        'rest_framework.filters.OrderingFilter',
    ),
    'DEFAULT_RENDERER_CLASSES': (
        'rest_framework.renderers.JSONRenderer',
        'rest_framework.renderers.BrowsableAPIRenderer',
    ),
    'DEFAULT_THROTTLE_CLASSES': [
        'rest_framework.throttling.AnonRateThrottle',
        'rest_framework.throttling.UserRateThrottle',
    ],
    'DEFAULT_THROTTLE_RATES': {
        'anon': '100/hour',
        'user': '500/hour',
        'auth': '10/minute',  # For login/register endpoints
    },
    'DEFAULT_VERSIONING_CLASS': 'rest_framework.versioning.NamespaceVersioning',
    'DEFAULT_VERSION': 'v1',
    'ALLOWED_VERSIONS': ['v1'],
    'VERSION_PARAM': 'version',
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
    'EXCEPTION_HANDLER': 'core.exceptions.custom_exception_handler',
}

# API Documentation Settings
SPECTACULAR_SETTINGS = {
    'TITLE': 'E-Commerce API',
    'DESCRIPTION': 'A comprehensive e-commerce platform API',
    'VERSION': '1.0.0',
    'SERVE_INCLUDE_SCHEMA': False,
    'COMPONENT_SPLIT_REQUEST': True,
    'SECURITY': [{'bearerAuth': []}],
    'SWAGGER_UI_SETTINGS': {
        'persistAuthorization': True,
        'displayOperationId': True,
    },
}

JWT_SECRET_KEY = get_setting('JWT_SECRET_KEY', SECRET_KEY)
JWT_ALGORITHM = get_setting('JWT_ALGORITHM', 'HS256')
JWT_ACCESS_TOKEN_LIFETIME = int(get_setting('JWT_ACCESS_TOKEN_LIFETIME', 60))
JWT_REFRESH_TOKEN_LIFETIME = int(get_setting('JWT_REFRESH_TOKEN_LIFETIME', 1440))

CORS_ALLOWED_ORIGINS = str(get_setting('CORS_ALLOWED_ORIGINS', 'http://localhost:3000,http://localhost:8000')).split(',')

RATE_LIMIT_PER_MINUTE = int(get_setting('RATE_LIMIT_PER_MINUTE', 60))

SITE_NAME = get_setting('SITE_NAME', 'E-Commerce Store')
SITE_URL = get_setting('SITE_URL', 'http://localhost:8000')

EMAIL_BACKEND = get_setting('EMAIL_BACKEND', 'django.core.mail.backends.console.EmailBackend')
EMAIL_HOST = get_setting('EMAIL_HOST', 'smtp.gmail.com')
EMAIL_PORT = int(get_setting('EMAIL_PORT', 587))
EMAIL_USE_TLS = str(get_setting('EMAIL_USE_TLS', 'True')).lower() == 'true'
EMAIL_HOST_USER = get_setting('EMAIL_HOST_USER', '')
EMAIL_HOST_PASSWORD = get_setting('EMAIL_HOST_PASSWORD', '')
DEFAULT_FROM_EMAIL = get_setting('DEFAULT_FROM_EMAIL', EMAIL_HOST_USER or 'noreply@example.com')

PASSWORD_RESET_TIMEOUT = int(get_setting('PASSWORD_RESET_TIMEOUT', 3600))

CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': get_setting('REDIS_URL', 'redis://127.0.0.1:6379/1'),
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
        }
    }
}

# Sessions using cache
SESSION_ENGINE = 'django.contrib.sessions.backends.cache'
SESSION_CACHE_ALIAS = 'default'

RATE_LIMIT_REQUESTS = int(get_setting('RATE_LIMIT_REQUESTS', '100'))
RATE_LIMIT_PERIOD = int(get_setting('RATE_LIMIT_PERIOD', '60'))

CELERY_BROKER_URL = get_setting('REDIS_URL', 'redis://127.0.0.1:6379/0')
CELERY_RESULT_BACKEND = get_setting('REDIS_URL', 'redis://127.0.0.1:6379/0')
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = TIME_ZONE

# Logging
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
        'simple': {
            'format': '{levelname} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'verbose'
        },
        'file': {
            'class': 'logging.FileHandler',
            'filename': BASE_DIR / 'logs' / 'django.log',
            'formatter': 'verbose',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'INFO',
    },
    'loggers': {
        'django': {
            'handlers': ['console', 'file'],
            'level': 'INFO',
            'propagate': False,
        },
        'ecommerce': {
            'handlers': ['console', 'file'],
            'level': 'DEBUG',
            'propagate': False,
        },
    },
}

# Create logs directory if it doesn't exist
import pathlib
pathlib.Path(BASE_DIR / 'logs').mkdir(exist_ok=True)

# Razorpay Configuration
RAZORPAY_KEY_ID = get_setting('RAZORPAY_KEY_ID', '')
RAZORPAY_KEY_SECRET = get_setting('RAZORPAY_KEY_SECRET', '')
RAZORPAY_WEBHOOK_SECRET = get_setting('RAZORPAY_WEBHOOK_SECRET', '')

# Payment Methods
PAYMENT_METHODS = {
    'cod': {
        'name': 'Cash on Delivery',
        'enabled': True,
    },
    'razorpay': {
        'name': 'Pay Online (Card/UPI/NetBanking)',
        'enabled': bool(RAZORPAY_KEY_ID and RAZORPAY_KEY_SECRET),
    }
}

# Allauth Settings (Django AllAuth 65+)
ACCOUNT_LOGIN_METHODS = {'email'}
ACCOUNT_SIGNUP_FIELDS = ['email*', 'password1*', 'password2*']
ACCOUNT_EMAIL_VERIFICATION = 'none'  # or 'mandatory' for production
ACCOUNT_USER_MODEL_USERNAME_FIELD = None
ACCOUNT_ADAPTER = 'users.adapters.CustomAccountAdapter'

# Social Account Settings
SOCIALACCOUNT_PROVIDERS = {
    'google': {
        'SCOPE': [
            'profile',
            'email',
        ],
        'AUTH_PARAMS': {
            'access_type': 'online',
        },
        'OAUTH_PKCE_ENABLED': True,
        'APP': {
            'client_id': get_setting('GOOGLE_CLIENT_ID', ''),
            'secret': get_setting('GOOGLE_CLIENT_SECRET', ''),
        }
    }
}

GOOGLE_CLIENT_ID = get_setting('GOOGLE_CLIENT_ID', '')
GOOGLE_CLIENT_SECRET = get_setting('GOOGLE_CLIENT_SECRET', '')
