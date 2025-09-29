# Optimized startup - only run lightweight commands
web: python3 setup_db.py && python3 manage.py collectstatic --noinput && python3 railway_load_data.py && DJANGO_SETTINGS_MODULE=school_organizer.settings_production gunicorn school_organizer.wsgi:application --bind 0.0.0.0:$PORT --workers 1 --worker-class sync --worker-connections 1000 --timeout 120 --preload
