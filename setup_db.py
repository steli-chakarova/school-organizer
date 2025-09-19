#!/usr/bin/env python
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'school_organizer.settings_production')
django.setup()

from django.core.management import execute_from_command_line

if __name__ == '__main__':
    try:
        # First, create the database tables without running migrations
        print("Creating database tables...")
        execute_from_command_line(['manage.py', 'migrate', '--run-syncdb', '--noinput'])
        
        # Then apply any remaining migrations
        print("Applying migrations...")
        execute_from_command_line(['manage.py', 'migrate', '--noinput'])
        
        print("Database setup complete!")
    except Exception as e:
        print(f"Error setting up database: {e}")
        # If migrations fail, try to create tables manually
        try:
            print("Trying alternative setup...")
            execute_from_command_line(['manage.py', 'migrate', 'organizer', '--fake-initial', '--noinput'])
            execute_from_command_line(['manage.py', 'migrate', '--noinput'])
            print("Alternative setup successful!")
        except Exception as e2:
            print(f"Alternative setup also failed: {e2}")
            sys.exit(1)
