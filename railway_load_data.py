#!/usr/bin/env python
"""
Script to be run on Railway to load data
"""
import os
import sys
import django

# Set up Django with production settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'school_organizer.settings_production')
django.setup()

from django.core.management import call_command
from django.core.management.base import CommandError

def load_data():
    """
    Load data from the uploaded JSON file
    """
    try:
        print("Loading data...")
        
        # The data file should be uploaded to the app directory
        data_file = 'data_export.json'
        
        if not os.path.exists(data_file):
            print(f"❌ Data file {data_file} not found!")
            return False
        
        # Load the data
        call_command('loaddata', data_file)
        
        print("✅ Data loaded successfully!")
        return True
        
    except CommandError as e:
        print(f"❌ Error loading data: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False

if __name__ == '__main__':
    success = load_data()
    sys.exit(0 if success else 1)
