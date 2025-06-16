#!/bin/bash
set -e

# Simple Local Deployment Script
# For deploying on your local Ubuntu server

# Configuration
APP_NAME="collecting-website"
APP_USER="www-data"
APP_DIR="/opt/${APP_NAME}"
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

# Check if running as root
if [[ $EUID -ne 0 ]]; then
   error "This script must be run as root (use sudo)"
   exit 1
fi

log "Starting local deployment of ${APP_NAME}..."

# Ensure app directory exists
if [ ! -d "$APP_DIR" ]; then
    error "Application directory $APP_DIR not found. Please run setup-ubuntu-server.sh first."
    exit 1
fi

cd "$APP_DIR"

# Stop service before updating
log "Stopping ${APP_NAME} service..."
if systemctl is-active --quiet "$SERVICE_NAME"; then
    systemctl stop "$SERVICE_NAME"
    log "Service stopped successfully"
else
    log "Service is not running (this is normal for first-time deployment)"
fi

# Download games.db from S3 (if AWS credentials are configured)
log "Downloading games database..."
if command -v aws &> /dev/null; then
    # Set HOME environment for www-data user to avoid snap permission issues
    export HOME="/var/lib/www-data"
    sudo -u "$APP_USER" mkdir -p "$HOME/.aws" 2>/dev/null || true
    
    # Get the ETag of the local games.db if it exists
    if [ -f games.db ]; then
        LOCAL_ETAG=$(sudo -u "$APP_USER" env HOME="$HOME" aws s3api head-object --bucket collecting-tools-gantt-pub --key games.db --query ETag --output text 2>/dev/null || echo "")
        if [ ! -z "$LOCAL_ETAG" ]; then
            log "Checking if games.db needs updating..."
            ERROR_MSG=$(sudo -u "$APP_USER" env HOME="$HOME" aws s3api get-object --bucket collecting-tools-gantt-pub --key games.db --if-none-match $LOCAL_ETAG games.db 2>&1 || true)
            if [[ $ERROR_MSG == *"Not Modified"* ]]; then
                log "Local games.db is already up to date"
            elif [[ $ERROR_MSG == "" ]]; then
                log "Downloaded newer version of games.db"
            else
                warn "Error checking games.db: $ERROR_MSG"
            fi
        else
            log "Downloading games.db from S3..."
            sudo -u "$APP_USER" env HOME="$HOME" aws s3api get-object --bucket collecting-tools-gantt-pub --key games.db games.db >/dev/null
        fi
    else
        log "Downloading games.db from S3..."
        sudo -u "$APP_USER" env HOME="$HOME" aws s3api get-object --bucket collecting-tools-gantt-pub --key games.db games.db >/dev/null
    fi
else
    warn "AWS CLI not found. Skipping games.db download."
    warn "If you need the database, configure AWS CLI with: aws configure"
fi

# Set up Python virtual environment
log "Setting up Python environment..."
if [ ! -d "venv" ]; then
    sudo -u "$APP_USER" python3 -m venv venv
fi

# Install/update dependencies
log "Installing Python dependencies..."
sudo -u "$APP_USER" venv/bin/pip install --upgrade pip
sudo -u "$APP_USER" venv/bin/pip install -r requirements.txt

# Set proper ownership
log "Setting file permissions..."
chown -R "$APP_USER:$APP_USER" "$APP_DIR"
chmod +x "$APP_DIR/app.py"

# Install systemd service if not already installed
if [ ! -f "/etc/systemd/system/${SERVICE_NAME}" ]; then
    log "Installing systemd service..."
    cp "$APP_DIR/${SERVICE_NAME}" "/etc/systemd/system/${SERVICE_NAME}"
    systemctl daemon-reload
    systemctl enable "$SERVICE_NAME"
fi

# Start service
log "Starting ${APP_NAME} service..."
systemctl start "$SERVICE_NAME"

# Wait for service to start
sleep 3

# Check service status
if systemctl is-active --quiet "$SERVICE_NAME"; then
    log "✅ Deployment successful! ${APP_NAME} is running."
    
    # Get local IP
    LOCAL_IP=$(hostname -I | awk '{print $1}')
    log "🌐 Access your application at: http://${LOCAL_IP}"
    
    log "Service status:"
    systemctl status "$SERVICE_NAME" --no-pager -l
else
    error "❌ Deployment failed! Service is not running."
    log "Service logs:"
    journalctl -u "$SERVICE_NAME" --no-pager -l -n 20
    exit 1
fi

log "Local deployment completed successfully!"
