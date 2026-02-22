# Set DEBUG before importing base to avoid SECRET_KEY check
import os
os.environ['DEBUG'] = 'True'

from .base import *

# Override DEBUG to ensure it's True
DEBUG = True
ALLOWED_HOSTS = ['localhost', '127.0.0.1', '*']

# CSRF trusted origins for development
CSRF_TRUSTED_ORIGINS = ['http://localhost:8000', 'http://127.0.0.1:8000', 'http://localhost:3000']

# Use PostgreSQL from environment variables
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': get_env_setting('DB_NAME', 'postgres'),
        'USER': get_env_setting('DB_USER', 'postgres'),
        'PASSWORD': get_env_setting('DB_PASSWORD', ''),
        'HOST': get_env_setting('DB_HOST', 'localhost'),
        'PORT': get_env_setting('DB_PORT', '5432'),
        'OPTIONS': {
            'connect_timeout': 10,
        },
    }
}

# More verbose logging in development
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'DEBUG',
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
    },
}

# Allow CORS for development
CORS_ALLOW_ALL_ORIGINS = True

# Disable caching for development (use DummyCache instead of Redis)
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.dummy.DummyCache',
    }
}

# Use file-based sessions instead of cache-based
SESSION_ENGINE = 'django.contrib.sessions.backends.db'
