"""
Production settings for CodeLearn LMS
Domain: uptrail.ralfiz.com
"""

import os
from .settings import *

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = False

# SECURITY WARNING: define the correct hosts in production!
ALLOWED_HOSTS = [
    'uptrail.ralfiz.com',
    'www.uptrail.ralfiz.com',
    'api.uptrail.ralfiz.com',
    # Add IP address if needed
    # '192.168.1.100',
]

# Database - Use PostgreSQL in production
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.environ.get('DB_NAME', 'codelearn_lms_prod'),
        'USER': os.environ.get('DB_USER', 'codelearn_user'),
        'PASSWORD': os.environ.get('DB_PASSWORD', ''),
        'HOST': os.environ.get('DB_HOST', 'localhost'),
        'PORT': os.environ.get('DB_PORT', '5432'),
        'OPTIONS': {
            'sslmode': 'prefer',
        },
    }
}

# Redis Cache Configuration
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.redis.RedisCache',
        'LOCATION': os.environ.get('REDIS_URL', 'redis://127.0.0.1:6379/1'),
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
        },
        'KEY_PREFIX': 'codelearn_lms',
        'TIMEOUT': 300,
    }
}

# Session engine
SESSION_ENGINE = 'django.contrib.sessions.backends.cache'
SESSION_CACHE_ALIAS = 'default'

# Security Settings
SECURE_SSL_REDIRECT = True
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
SECURE_HSTS_SECONDS = 31536000  # 1 year
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_BROWSER_XSS_FILTER = True
X_FRAME_OPTIONS = 'DENY'

# CSRF Settings
CSRF_COOKIE_SECURE = True
CSRF_TRUSTED_ORIGINS = [
    'https://uptrail.ralfiz.com',
    'https://www.uptrail.ralfiz.com',
    'https://api.uptrail.ralfiz.com',
]

# Session Security
SESSION_COOKIE_SECURE = True
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_AGE = 3600  # 1 hour
SESSION_COOKIE_SAMESITE = 'Lax'

# Static files (CSS, JavaScript, Images)
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')
STATIC_URL = '/static/'

# Media files
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')
MEDIA_URL = '/media/'

# Email Configuration
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = os.environ.get('EMAIL_HOST', 'smtp.gmail.com')
EMAIL_PORT = int(os.environ.get('EMAIL_PORT', '587'))
EMAIL_USE_TLS = True
EMAIL_HOST_USER = os.environ.get('EMAIL_HOST_USER', '')
EMAIL_HOST_PASSWORD = os.environ.get('EMAIL_HOST_PASSWORD', '')
DEFAULT_FROM_EMAIL = os.environ.get('DEFAULT_FROM_EMAIL', 'noreply@uptrail.ralfiz.com')

# CORS Configuration for Production
CORS_ALLOW_ALL_ORIGINS = False
CORS_ALLOWED_ORIGINS = [
    "https://uptrail.ralfiz.com",
    "https://www.uptrail.ralfiz.com",
    "https://api.uptrail.ralfiz.com",
    # Add your mobile app domains if needed
    # "https://app.uptrail.ralfiz.com",
]

# Additional CORS settings
CORS_ALLOW_CREDENTIALS = True
CORS_ALLOW_HEADERS = [
    'accept',
    'accept-encoding',
    'authorization',
    'content-type',
    'dnt',
    'origin',
    'user-agent',
    'x-csrftoken',
    'x-requested-with',
]

CORS_ALLOW_METHODS = [
    'DELETE',
    'GET',
    'OPTIONS',
    'PATCH',
    'POST',
    'PUT',
]

# Production-specific CORS preflight max age
CORS_PREFLIGHT_MAX_AGE = 86400

# API Settings - Remove browsable API in production
REST_FRAMEWORK['DEFAULT_RENDERER_CLASSES'] = [
    'rest_framework.renderers.JSONRenderer',
]

# Remove browsable API renderer if present
if 'rest_framework.renderers.BrowsableAPIRenderer' in REST_FRAMEWORK.get('DEFAULT_RENDERER_CLASSES', []):
    REST_FRAMEWORK['DEFAULT_RENDERER_CLASSES'].remove('rest_framework.renderers.BrowsableAPIRenderer')

# Logging Configuration
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
        'file': {
            'level': 'INFO',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': os.path.join(BASE_DIR, 'logs', 'django.log'),
            'maxBytes': 1024*1024*50,  # 50 MB
            'backupCount': 5,
            'formatter': 'verbose',
        },
        'error_file': {
            'level': 'ERROR',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': os.path.join(BASE_DIR, 'logs', 'django_error.log'),
            'maxBytes': 1024*1024*50,  # 50 MB
            'backupCount': 5,
            'formatter': 'verbose',
        },
        'console': {
            'level': 'INFO',
            'class': 'logging.StreamHandler',
            'formatter': 'simple',
        },
    },
    'root': {
        'handlers': ['file', 'console'],
        'level': 'INFO',
    },
    'loggers': {
        'django': {
            'handlers': ['file', 'console'],
            'level': 'INFO',
            'propagate': False,
        },
        'django.request': {
            'handlers': ['error_file'],
            'level': 'ERROR',
            'propagate': False,
        },
        'apps': {
            'handlers': ['file', 'console'],
            'level': 'INFO',
            'propagate': False,
        },
    },
}

# Ensure logs directory exists
os.makedirs(os.path.join(BASE_DIR, 'logs'), exist_ok=True)

# File Upload Settings
FILE_UPLOAD_MAX_MEMORY_SIZE = 5242880  # 5MB
DATA_UPLOAD_MAX_MEMORY_SIZE = 5242880  # 5MB

# Performance Settings
USE_ETAGS = True

# WhiteNoise for static files
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# Admin Security
ADMIN_URL = os.environ.get('ADMIN_URL', 'admin/')

# Payment Gateway Configuration (Production)
RAZORPAY_KEY_ID = os.environ.get('RAZORPAY_KEY_ID', '')
RAZORPAY_KEY_SECRET = os.environ.get('RAZORPAY_KEY_SECRET', '')

# YouTube API Configuration
YOUTUBE_API_KEY = os.environ.get('YOUTUBE_API_KEY', '')

# Celery Configuration for Production
CELERY_BROKER_URL = os.environ.get('REDIS_URL', 'redis://127.0.0.1:6379/0')
CELERY_RESULT_BACKEND = os.environ.get('REDIS_URL', 'redis://127.0.0.1:6379/0')

# Sentry Error Tracking (Optional)
SENTRY_DSN = os.environ.get('SENTRY_DSN', '')
if SENTRY_DSN:
    import sentry_sdk
    from sentry_sdk.integrations.django import DjangoIntegration
    from sentry_sdk.integrations.logging import LoggingIntegration

    sentry_sdk.init(
        dsn=SENTRY_DSN,
        integrations=[
            DjangoIntegration(),
            LoggingIntegration(level=logging.INFO, event_level=logging.ERROR),
        ],
        traces_sample_rate=0.1,
        send_default_pii=True,
        environment='production',
    )

# Rate Limiting (if using django-ratelimit)
RATELIMIT_ENABLE = True

# Additional Security Headers
SECURE_REFERRER_POLICY = 'strict-origin-when-cross-origin'

# Disable admin docs in production
INSTALLED_APPS = [app for app in INSTALLED_APPS if app != 'django.contrib.admindocs']

print(f"🏭 Production settings loaded for uptrail.ralfiz.com")