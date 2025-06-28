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
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1"
}

error() {
    echo -e "${RED}[$(date +'%Y-%m-%d %H:%M:%S')] ERROR:${NC} $1"
}

warn() {
    echo -e "${YELLOW}[$(date +'%Y-%m-%d %H:%M:%S')] WARNING:${NC} $1"
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

# Ensure games.db exists and has proper permissions
log "Setting up database..."
if [ -f "$APP_DIR/games.db" ]; then
    log "Database found, setting permissions"
    sudo chown "$APP_USER:$APP_USER" "$APP_DIR/games.db"
    sudo chmod 664 "$APP_DIR/games.db"
else
    warn "games.db not found in deployment directory"
    log "Attempting to download games.db from S3..."
    
    # Try AWS CLI to download games.db
    if command -v aws &> /dev/null; then
        log "Attempting S3 download with AWS CLI..."
        if sudo -u "$APP_USER" aws s3api get-object --bucket collecting-tools-gantt-pub --key games.db "$APP_DIR/games.db" >/dev/null 2>&1; then
            log "✅ Downloaded games.db from S3 successfully"
            sudo chown "$APP_USER:$APP_USER" "$APP_DIR/games.db"
            sudo chmod 664 "$APP_DIR/games.db"
        else
            error "Failed to download games.db from S3"
            log "You may need to manually copy games.db to $APP_DIR/"
        fi
    else
        error "AWS CLI not found - cannot download games.db"
        log "You may need to manually copy games.db to $APP_DIR/"
    fi
fi

# Install Python dependencies
log "Installing Python dependencies..."
cd "$APP_DIR"

# Create .local directory structure for www-data user
sudo mkdir -p "/var/www/.local/bin"
sudo mkdir -p "/var/www/.local/lib/python3.10/site-packages"
sudo chown -R "$APP_USER:$APP_USER" "/var/www/.local"

# Use system packages for externally managed Python environment
sudo -H -u "$APP_USER" python3 -m pip install --break-system-packages --user -r requirements.txt

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
Environment=PATH=/var/www/.local/bin:\$PATH
ExecStart=/var/www/.local/bin/gunicorn --bind 0.0.0.0:8080 --workers 3 --timeout 120 wsgi:app
ExecReload=/bin/kill -s HUP \$MAINPID
KillMode=mixed
TimeoutStopSec=5
PrivateTmp=true
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# Set up S3 backup system
log "Setting up S3 database backup..."
if [[ -f "$APP_DIR/setup-backup-cron.sh" ]]; then
    sudo chmod +x "$APP_DIR/setup-backup-cron.sh"
    sudo chmod +x "$APP_DIR/backup_to_s3.py"
    
    # Run setup as the app user to avoid permission issues
    if sudo -u "$APP_USER" bash -c "cd $APP_DIR && ./setup-backup-cron.sh" 2>/dev/null; then
        log "✅ S3 backup system configured successfully"
    else
        warn "⚠️  S3 backup setup failed - you may need to configure AWS credentials manually"
        warn "    Run: sudo -u $APP_USER aws configure"
        warn "    Then: cd $APP_DIR && ./setup-backup-cron.sh"
    fi
else
    warn "⚠️  setup-backup-cron.sh not found, skipping backup setup"
fi

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
