#!/bin/bash

# Railway build script for School Organizer
# This ensures Playwright browsers are installed during Railway deployment

echo "🚀 Building School Organizer for Railway..."

# Install Python dependencies
echo "📦 Installing Python dependencies..."
pip install -r requirements.txt

# Install Node.js dependencies (for Playwright)
echo "📦 Installing Node.js dependencies..."
npm install

# Install Playwright browsers
echo "🌐 Installing Playwright browsers..."
playwright install chromium

# Set up Django
echo "⚙️ Setting up Django..."
python3 manage.py collectstatic --noinput
python3 manage.py migrate

echo "✅ Railway build complete!"
