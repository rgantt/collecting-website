#!/bin/bash

# Debug script to test the application locally and see detailed errors
# Run this on your Ubuntu server to debug the app loading issue

APP_DIR="/opt/collecting-website"
APP_USER="www-data"

echo "🔍 Debugging collecting-website app loading..."

cd "$APP_DIR"

echo ""
echo "📁 Current directory contents:"
ls -la

echo ""
echo "🐍 Testing Python app directly..."
echo "Running: sudo -u $APP_USER $APP_DIR/venv/bin/python wsgi.py"
echo ""

# Try to run the app directly to see any import errors
sudo -u "$APP_USER" "$APP_DIR/venv/bin/python" wsgi.py

echo ""
echo "🔧 If that failed, trying to import the app module..."
sudo -u "$APP_USER" "$APP_DIR/venv/bin/python" -c "
import sys
sys.path.insert(0, '$APP_DIR')
try:
    from app import create_app
    app = create_app()
    print('✅ App imported successfully!')
except Exception as e:
    print(f'❌ Import error: {e}')
    import traceback
    traceback.print_exc()
"

echo ""
echo "📋 Environment variables:"
sudo -u "$APP_USER" env | grep -E "(FLASK|SECRET|DATABASE)" || echo "No Flask environment variables found"

echo ""
echo "📦 Installed packages:"
sudo -u "$APP_USER" "$APP_DIR/venv/bin/pip" list | grep -E "(Flask|gunicorn|requests|beautifulsoup4)"
