from .base import *
import urllib.parse

DEBUG = False

ALLOWED_HOSTS = str(get_env_setting('ALLOWED_HOSTS', '')).split(',') if get_env_setting('ALLOWED_HOSTS') else ['localhost', '127.0.0.1']

SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = 'strict-origin-when-cross-origin'
X_FRAME_OPTIONS = 'DENY'

# Parse DATABASE_URL if provided (Render, Heroku, etc.)
database_url = get_env_setting('DATABASE_URL', '')
if database_url:
    parsed = urllib.parse.urlparse(database_url)
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': parsed.path[1:],  # Remove leading '/'
            'USER': parsed.username,
            'PASSWORD': parsed.password,
            'HOST': parsed.hostname,
            'PORT': parsed.port or '5432',
            'CONN_MAX_AGE': 600,
            'OPTIONS': {
                'connect_timeout': 10,
            },
        }
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': get_env_setting('DB_NAME', 'ecomm_db'),
            'USER': get_env_setting('DB_USER', 'postgres'),
            'PASSWORD': get_env_setting('DB_PASSWORD', ''),
            'HOST': get_env_setting('DB_HOST', 'localhost'),
            'PORT': get_env_setting('DB_PORT', '5432'),
            'CONN_MAX_AGE': 600,
            'OPTIONS': {
                'connect_timeout': 10,
            },
        }
    }

CSRF_COOKIE_SECURE = str(get_db_setting('CSRF_COOKIE_SECURE', 'True')).lower() == 'true'
SESSION_COOKIE_SECURE = str(get_db_setting('SESSION_COOKIE_SECURE', 'True')).lower() == 'true'
CSRF_COOKIE_HTTPONLY = True
SESSION_COOKIE_HTTPONLY = True

SECURE_SSL_REDIRECT = str(get_db_setting('SECURE_SSL_REDIRECT', 'False')).lower() == 'true'
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

if str(get_db_setting('SECURE_HSTS', 'False')).lower() == 'true':
    SECURE_HSTS_SECONDS = 31536000
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True

redis_url = get_env_setting('REDIS_URL', '')
if redis_url:
    CACHES = {
        'default': {
            'BACKEND': 'django.core.cache.backends.redis.RedisCache',
            'LOCATION': redis_url,
            'KEY_PREFIX': 'ecomm_prod',
            'TIMEOUT': 300,
        }
    }
    SESSION_ENGINE = 'django.contrib.sessions.backends.cache'
    SESSION_CACHE_ALIAS = 'default'
else:
    CACHES = {
        'default': {
            'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        }
    }
    SESSION_ENGINE = 'django.contrib.sessions.backends.db'

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
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

STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'INFO',
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'level': get_db_setting('DJANGO_LOG_LEVEL', 'INFO'),
            'propagate': False,
        },
        'django.request': {
            'handlers': ['console'],
            'level': 'ERROR',
            'propagate': False,
        },
    },
}

CORS_ALLOW_ALL_ORIGINS = False
CORS_ALLOWED_ORIGINS = str(get_db_setting('CORS_ALLOWED_ORIGINS', '')).split(',') if get_db_setting('CORS_ALLOWED_ORIGINS') else []

CSRF_TRUSTED_ORIGINS = str(get_db_setting('CSRF_TRUSTED_ORIGINS', '')).split(',') if get_db_setting('CSRF_TRUSTED_ORIGINS') else []

RATE_LIMIT_REQUESTS = int(get_db_setting('RATE_LIMIT_REQUESTS', '100'))
RATE_LIMIT_PERIOD = int(get_db_setting('RATE_LIMIT_PERIOD', '60'))

REST_FRAMEWORK['DEFAULT_THROTTLE_CLASSES'] = [
    'rest_framework.throttling.AnonRateThrottle',
    'rest_framework.throttling.UserRateThrottle',
]
REST_FRAMEWORK['DEFAULT_THROTTLE_RATES'] = {
    'anon': '100/hour',
    'user': '1000/hour',
}

DATA_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024
FILE_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
