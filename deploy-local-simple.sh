#!/bin/bash
set -e

# Simple Local Deployment Script
# For deploying on your local Ubuntu server

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

# Check if running as root
if [[ $EUID -ne 0 ]]; then
   error "This script must be run as root (use sudo)"
   exit 1
fi

log "Starting local deployment of ${APP_NAME}..."

# Install system dependencies for faster Python compilation
log "Installing system build dependencies..."
apt-get update -qq
apt-get install -y -qq \
    python3-dev \
    python3-wheel \
    build-essential \
    libffi-dev \
    libssl-dev \
    pkg-config \
    rustc \
    2>/dev/null || warn "Some system packages may not be available"

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

# Download games.db from S3 (REQUIRED)
log "Downloading games database..."

# Check if we have a games.db file already
if [ -f games.db ]; then
    log "games.db already exists, skipping S3 download"
else
    log "games.db is required - attempting to download..."
    
    # Method 1: Try AWS CLI snap as root
    if command -v aws &> /dev/null; then
        log "Attempting S3 download with AWS CLI..."
        if aws s3api get-object --bucket collecting-tools-gantt-pub --key games.db games.db >/dev/null 2>&1; then
            log "✅ Downloaded games.db from S3 successfully"
            chown "$APP_USER:$APP_USER" games.db
        else
            warn "AWS CLI snap failed due to permission issues"
            
            # Method 2: Try installing pip-based AWS CLI as fallback
            log "Installing pip-based AWS CLI as fallback..."
            pip3 install --quiet awscli 2>/dev/null || true
            
            if command -v ~/.local/bin/aws &> /dev/null; then
                log "Trying pip-based AWS CLI..."
                if ~/.local/bin/aws s3api get-object --bucket collecting-tools-gantt-pub --key games.db games.db >/dev/null 2>&1; then
                    log "✅ Downloaded games.db with pip AWS CLI"
                    chown "$APP_USER:$APP_USER" games.db
                else
                    error "Failed to download games.db with pip AWS CLI"
                fi
            else
                error "Could not install pip-based AWS CLI"
            fi
        fi
    else
        # Skip AWS CLI installation - not needed for deployment
        warn "AWS CLI not available - skipping S3 download"
        warn "You can manually copy games.db or set up AWS credentials later"
    fi
    
    # Final check - ensure we have the database
    if [ ! -f games.db ]; then
        error "❌ CRITICAL: games.db is required but could not be downloaded!"
        error ""
        error "Please do one of the following:"
        error "  1. Configure AWS credentials: aws configure"
        error "  2. Copy games.db manually to $APP_DIR"
        error "  3. Run: scp your-local-machine:path/to/games.db $APP_DIR/"
        error ""
        error "The deployment cannot continue without games.db"
        exit 1
    fi
fi

# Set up Python virtual environment
log "Setting up Python environment..."
if [ ! -d "venv" ]; then
    sudo -u "$APP_USER" python3 -m venv venv
fi

# Install/update dependencies
log "Installing Python dependencies..."
# Optimize pip for faster installation
log "Upgrading pip and installing dependencies (this may take a few minutes)..."
sudo -u "$APP_USER" venv/bin/pip install --upgrade pip setuptools wheel

# Install system packages that have binary wheels to avoid compilation
log "Installing Python dependencies with optimizations..."
sudo -u "$APP_USER" venv/bin/pip install \
    --no-cache-dir \
    --prefer-binary \
    --only-binary=cryptography,cffi,lxml \
    -r requirements.txt

# Set proper ownership
log "Setting file permissions..."
chown -R "$APP_USER:$APP_USER" "$APP_DIR"
chmod +x "$APP_DIR/wsgi.py"

# Install/update systemd service
log "Installing/updating systemd service..."
cp "$APP_DIR/${SERVICE_NAME}" "/etc/systemd/system/${SERVICE_NAME}"
systemctl daemon-reload
if ! systemctl is-enabled "$SERVICE_NAME" >/dev/null 2>&1; then
    systemctl enable "$SERVICE_NAME"
fi

# Set up S3 backup system
log "Setting up S3 database backup..."
if [[ -f "$APP_DIR/setup-backup-cron.sh" ]]; then
    chmod +x "$APP_DIR/setup-backup-cron.sh"
    chmod +x "$APP_DIR/backup_to_s3.py"
    
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
