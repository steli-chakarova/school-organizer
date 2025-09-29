#!/bin/bash

# Railway build script - runs heavy downloads during build phase
# This runs once during build, not on every deployment

echo "🚀 Starting Railway build process..."

# Install Playwright browsers (heavy download - ~100MB)
echo "📦 Installing Playwright browsers..."
python3 -m playwright install chromium
python3 -m playwright install-deps

echo "✅ Build process complete!"