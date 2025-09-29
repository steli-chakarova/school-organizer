#!/bin/bash

echo "Starting School Organizer..."

# Check if Playwright browsers are installed
if [ ! -d "/root/.cache/ms-playwright/chromium_headless_shell" ]; then
    echo "Installing Playwright browsers (first time setup)..."
    python3 -m playwright install chromium
    python3 -m playwright install-deps
else
    echo "Playwright browsers already installed, skipping..."
fi

# Always ensure system dependencies are installed (in case they're missing)
echo "Ensuring system dependencies are installed..."
python3 -m playwright install-deps

# Setup database
echo "Setting up database..."
python3 setup_db.py

# Collect static files
echo "Collecting static files..."
python3 manage.py collectstatic --noinput

# Load data
echo "Loading data..."
python3 railway_load_data.py

# Start the application
echo "Starting Django application..."
export DJANGO_SETTINGS_MODULE=school_organizer.settings_production
export DJANGO_ALLOW_ASYNC_UNSAFE=True
exec gunicorn school_organizer.wsgi_production:application --bind 0.0.0.0:$PORT --workers 1 --worker-class sync --worker-connections 1000 --timeout 120 --preload
