import os
from .settings import *

# Production settings
DEBUG = False
ALLOWED_HOSTS = ['*']  # Railway will provide the domain

# Database configuration for Railway PostgreSQL
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.environ.get('PGDATABASE', os.environ.get('DATABASE_NAME', 'railway')),
        'USER': os.environ.get('PGUSER', os.environ.get('DATABASE_USER', 'postgres')),
        'PASSWORD': os.environ.get('PGPASSWORD', os.environ.get('DATABASE_PASSWORD', 'password')),
        'HOST': os.environ.get('PGHOST', os.environ.get('DATABASE_HOST', 'localhost')),
        'PORT': os.environ.get('PGPORT', os.environ.get('DATABASE_PORT', '5432')),
    }
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
SECRET_KEY = os.environ.get('SECRET_KEY', 'your-secret-key-here')
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True

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
