#!/usr/bin/env python
"""Django's command-line utility for administrative tasks."""
import os
import sys


def main():
    """Run administrative tasks."""
    # Debug: Print environment variables to see what Railway sets
    print("DEBUG: Checking environment variables...")
    railway_indicators = [
        'RAILWAY_ENVIRONMENT',
        'DATABASE_URL', 
        'PORT',
        'RAILWAY_STATIC_URL',
        'RAILWAY_GIT_COMMIT_SHA'
    ]
    
    for var in railway_indicators:
        value = os.environ.get(var)
        print(f"DEBUG: {var} = {value}")
    
    # Check if we're running in Railway
    if any(os.environ.get(var) for var in railway_indicators):
        print("DEBUG: Using production settings")
        os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'school_organizer.settings_production')
    else:
        print("DEBUG: Using development settings")
        os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'school_organizer.settings')
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?"
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == '__main__':
    main()