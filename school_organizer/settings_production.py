import os
import dj_database_url
from .settings import *

# Production settings
DEBUG = False

# Handle ALLOWED_HOSTS properly
allowed_hosts_env = os.environ.get('ALLOWED_HOSTS', '*')
if allowed_hosts_env == '*':
    ALLOWED_HOSTS = ['*']
else:
    ALLOWED_HOSTS = allowed_hosts_env.split(',')

# Add Railway-specific domains as backup
railway_domains = [
    'school-organizer-production.up.railway.app',
    '.up.railway.app',
    '.railway.app'
]
ALLOWED_HOSTS.extend(railway_domains)
ALLOWED_HOSTS = list(set(ALLOWED_HOSTS))  # Remove duplicates

# Database configuration for Railway
# Use dj-database-url to automatically parse Railway's DATABASE_URL
DATABASES = {
    'default': dj_database_url.config(
        default=os.environ.get('DATABASE_URL'),
        conn_max_age=600
    )
}

# Static files configuration
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')
STATIC_URL = '/static/'
STATICFILES_DIRS = [
    os.path.join(BASE_DIR, 'static'),
]

# Use WhiteNoise to serve static files
MIDDLEWARE.insert(1, 'whitenoise.middleware.WhiteNoiseMiddleware')
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# Media files
MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

# Security settings
SECRET_KEY = os.environ.get('SECRET_KEY', 'django-insecure-railway-deployment-key-change-this-in-production')
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True

# CSRF settings for Railway
CSRF_TRUSTED_ORIGINS = [
    'https://school-organizer-production.up.railway.app',
    'https://*.up.railway.app',
    'https://*.railway.app',
]

# Logging
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'level': 'INFO',
        },
    },
}

# Ensure custom user model is set
AUTH_USER_MODEL = 'organizer.User'

# Debug: Print ALLOWED_HOSTS to confirm it's set
print(f"DEBUG: ALLOWED_HOSTS = {ALLOWED_HOSTS}")
print(f"DEBUG: ALLOWED_HOSTS type = {type(ALLOWED_HOSTS)}")
print(f"DEBUG: ALLOWED_HOSTS env var = {os.environ.get('ALLOWED_HOSTS', 'NOT_SET')}")
