#!/bin/bash

# Production setup script for School Organizer
# This script installs all dependencies including Playwright browsers

echo "🚀 Setting up School Organizer for production..."

# Install Python dependencies
echo "📦 Installing Python dependencies..."
pip install -r requirements.txt

# Install Playwright browsers
echo "🌐 Installing Playwright browsers..."
playwright install chromium

# Set up Django
echo "⚙️ Setting up Django..."
python3 manage.py collectstatic --noinput
python3 manage.py migrate

echo "✅ Production setup complete!"
echo "📋 Next steps:"
echo "   1. Set up your environment variables (DATABASE_URL, SECRET_KEY, etc.)"
echo "   2. Configure your web server (nginx, apache, etc.)"
echo "   3. Start your Django application"
echo ""
echo "🔧 For Railway deployment:"
echo "   - Add 'playwright install chromium' to your build command"
echo "   - Or add it as a postinstall script in package.json"
