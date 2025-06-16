#!/bin/bash

# Test gunicorn directly to see the real error
APP_DIR="/opt/collecting-website"
APP_USER="www-data"

echo "🔍 Testing gunicorn directly..."

cd "$APP_DIR"

echo ""
echo "📁 Current directory: $(pwd)"
echo "📄 Files in directory:"
ls -la *.py

echo ""
echo "🐍 Testing gunicorn command directly..."
echo "Running: sudo -u $APP_USER $APP_DIR/venv/bin/gunicorn --bind 127.0.0.1:8081 --workers 1 wsgi:app"
echo ""

# Run gunicorn in foreground to see the actual error
sudo -u "$APP_USER" "$APP_DIR/venv/bin/gunicorn" --bind 127.0.0.1:8081 --workers 1 wsgi:app

echo ""
echo "🔧 If that failed, let's test the import directly:"
sudo -u "$APP_USER" "$APP_DIR/venv/bin/python" -c "
import sys
sys.path.insert(0, '$APP_DIR')
print('Testing wsgi import...')
try:
    import wsgi
    print('✅ wsgi module imported successfully')
    print('wsgi module attributes:', dir(wsgi))
    
    if hasattr(wsgi, 'app'):
        print('✅ wsgi.app found:', type(wsgi.app))
    else:
        print('❌ wsgi.app not found')
        
except Exception as e:
    print(f'❌ Import error: {e}')
    import traceback
    traceback.print_exc()
"
