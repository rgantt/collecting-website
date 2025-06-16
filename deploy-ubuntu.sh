#!/bin/bash
set -e

# Configuration
APP_NAME="collecting-website"
APP_USER="www-data"
APP_DIR="/opt/${APP_NAME}"
REPO_URL="https://github.com/rgantt/collecting-website.git"
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

log "Starting deployment of ${APP_NAME}..."

# Backup current deployment if it exists
if [ -d "$APP_DIR" ]; then
    log "Creating backup of current deployment..."
    cp -r "$APP_DIR" "${APP_DIR}.backup.$(date +%s)"
fi

# Create app directory
log "Setting up application directory..."
mkdir -p "$APP_DIR"
cd "$APP_DIR"

# Clone or update repository
if [ -d ".git" ]; then
    log "Updating existing repository..."
    sudo -u "$APP_USER" git fetch origin
    sudo -u "$APP_USER" git reset --hard origin/main
else
    log "Cloning repository..."
    sudo -u "$APP_USER" git clone "$REPO_URL" .
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

# Install systemd service
log "Installing systemd service..."
cp "$APP_DIR/${SERVICE_NAME}" "/etc/systemd/system/${SERVICE_NAME}"
systemctl daemon-reload

# Enable and start service
log "Starting ${APP_NAME} service..."
systemctl enable "$SERVICE_NAME"
systemctl restart "$SERVICE_NAME"

# Wait for service to start
sleep 5

# Check service status
if systemctl is-active --quiet "$SERVICE_NAME"; then
    log "✅ Deployment successful! ${APP_NAME} is running."
    log "Service status:"
    systemctl status "$SERVICE_NAME" --no-pager -l
else
    error "❌ Deployment failed! Service is not running."
    log "Service logs:"
    journalctl -u "$SERVICE_NAME" --no-pager -l -n 50
    exit 1
fi

log "Deployment completed successfully!"
