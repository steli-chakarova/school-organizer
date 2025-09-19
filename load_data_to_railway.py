#!/usr/bin/env python
"""
Script to load local data into Railway database
"""
import os
import sys
import django

# Set up Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'school_organizer.settings')
django.setup()

from django.core.management import call_command
from django.core.management.base import CommandError

def load_data_to_railway():
    """
    Load the exported data into Railway database
    """
    try:
        print("Loading data from data_export.json...")
        
        # Use loaddata command to load the exported data
        call_command('loaddata', 'data_export.json')
        
        print("✅ Data loaded successfully!")
        
    except CommandError as e:
        print(f"❌ Error loading data: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False
    
    return True

if __name__ == '__main__':
    success = load_data_to_railway()
    sys.exit(0 if success else 1)
