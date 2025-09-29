"""
WSGI config for school_organizer project - Production optimized version.

This module contains the WSGI application used by Django's development server
and any production WSGI deployments. It should expose a module-level variable
named ``application``. Django's ``runserver`` and ``runfcgi`` commands discover
this application via the ``WSGI_APPLICATION`` setting.

For more information on this file, see
https://docs.djangoproject.com/en/5.2/howto/deployment/wsgi/
"""

import os
import sys

from django.core.wsgi import get_wsgi_application

# Force sync mode
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'school_organizer.settings_production')

# Ensure we're in sync mode
os.environ['DJANGO_ALLOW_ASYNC_UNSAFE'] = 'True'

application = get_wsgi_application()
