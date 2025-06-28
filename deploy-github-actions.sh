#!/bin/bash
set -e

# GitHub Actions Deployment Script
# For deploying via GitHub Actions self-hosted runner

# Configuration
APP_NAME="collecting-website"
APP_USER="www-data"
APP_DIR="/var/www/${APP_NAME}"
SERVICE_NAME="${APP_NAME}.service"
LOG_FILE="/var/log/${APP_NAME}-deploy.log"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1" | tee -a "$LOG_FILE"
}

error() {
    echo -e "${RED}[$(date +'%Y-%m-%d %H:%M:%S')] ERROR:${NC} $1" | tee -a "$LOG_FILE"
}

warn() {
    echo -e "${YELLOW}[$(date +'%Y-%m-%d %H:%M:%S')] WARNING:${NC} $1" | tee -a "$LOG_FILE"
}

log "Starting GitHub Actions deployment of ${APP_NAME}..."

# Create app directory if it doesn't exist
sudo mkdir -p "$APP_DIR"

# Stop service before updating
log "Stopping ${APP_NAME} service..."
if sudo systemctl is-active --quiet "$SERVICE_NAME"; then
    sudo systemctl stop "$SERVICE_NAME"
    log "Service stopped"
else
    warn "Service was not running"
fi

# Copy files to deployment directory
log "Copying application files..."
sudo cp -r . "$APP_DIR/"
sudo chown -R "$APP_USER:$APP_USER" "$APP_DIR"

# Install Python dependencies
log "Installing Python dependencies..."
cd "$APP_DIR"
sudo -u "$APP_USER" python3 -m pip install --user -r requirements.txt

# Create/update systemd service file
log "Updating systemd service..."
sudo tee "/etc/systemd/system/$SERVICE_NAME" > /dev/null <<EOF
[Unit]
Description=$APP_NAME
After=network.target

[Service]
Type=notify
User=$APP_USER
Group=$APP_USER
RuntimeDirectory=$APP_NAME
WorkingDirectory=$APP_DIR
Environment=PATH=/home/$APP_USER/.local/bin:\$PATH
ExecStart=/usr/local/bin/gunicorn --bind 0.0.0.0:8080 --workers 3 --timeout 120 wsgi:app
ExecReload=/bin/kill -s HUP \$MAINPID
KillMode=mixed
TimeoutStopSec=5
PrivateTmp=true
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# Reload systemd and start service
log "Reloading systemd and starting service..."
sudo systemctl daemon-reload
sudo systemctl enable "$SERVICE_NAME"
sudo systemctl start "$SERVICE_NAME"

# Wait a moment for service to start
sleep 3

# Check service status
if sudo systemctl is-active --quiet "$SERVICE_NAME"; then
    log "✅ Service is running successfully"
    
    # Test the application
    log "Testing application..."
    if curl -f -s http://localhost:8080 > /dev/null; then
        log "✅ Application is responding correctly"
    else
        error "❌ Application is not responding on port 8080"
        sudo systemctl status "$SERVICE_NAME" --no-pager -l
        exit 1
    fi
else
    error "❌ Service failed to start"
    sudo systemctl status "$SERVICE_NAME" --no-pager -l
    exit 1
fi

log "GitHub Actions deployment completed successfully!"
log "Application is now running at http://localhost:8080"
