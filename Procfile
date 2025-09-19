web: python setup_db.py && python manage.py collectstatic --noinput && gunicorn school_organizer.wsgi:application --bind 0.0.0.0:$PORT --workers 3
