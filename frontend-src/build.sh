#!/bin/bash
# build.sh - Script to build the frontend

set -e  # Exit on any error

echo "🚀 Building frontend..."

# Check if package.json exists
if [ ! -f "package.json" ]; then
  echo "❌ Error: package.json not found in frontend-src directory!"
  exit 1
fi

# Install dependencies if node_modules doesn't exist or if --force flag is provided
if [ ! -d "node_modules" ] || [[ "$*" == *--force* ]]; then
  echo "📦 Installing dependencies..."
  npm install
fi

# Build the frontend
echo "🔨 Running build process..."
npm run build:web

# Check if build was successful
if [ ! -d "dist/web" ]; then
  echo "❌ Error: Build failed! dist/web directory not found."
  exit 1
fi

echo "✅ Frontend build completed successfully!"
echo "🌐 The application is ready to be served directly from frontend-src/dist/web directory."
