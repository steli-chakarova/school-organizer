#!/bin/bash
python manage.py migrate
python manage.py collectstatic --noinput
exec gunicorn school_organizer.wsgi:application --bind 0.0.0.0:$PORT
