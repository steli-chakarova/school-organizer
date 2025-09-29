#!/bin/bash

echo "Starting School Organizer..."

# Setup database
echo "Setting up database..."
python3 setup_db.py

# Collect static files
echo "Collecting static files..."
python3 manage.py collectstatic --noinput

# Load data
echo "Loading data..."
python3 railway_load_data.py

# Pre-initialize browser for faster PDF generation
echo "Pre-initializing browser..."
python3 -c "
import sys
sys.path.append('/app')
import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'school_organizer.settings_production')
import django
django.setup()
from organizer.pdf_service import get_browser
print('Initializing browser...')
browser = get_browser()
print('Browser initialized successfully!')
"

# Start the application
echo "Starting Django application..."
export DJANGO_SETTINGS_MODULE=school_organizer.settings_production
export DJANGO_ALLOW_ASYNC_UNSAFE=True
exec gunicorn school_organizer.wsgi_production:application --bind 0.0.0.0:$PORT --workers 1 --worker-class sync --worker-connections 1000 --timeout 300 --preload
