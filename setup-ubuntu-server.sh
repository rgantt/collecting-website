#!/bin/bash
set -e

# Ubuntu Server Setup Script for Collecting Website
# Run this on your Ubuntu server to set up everything needed

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
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

info() {
    echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')] INFO:${NC} $1"
}

# Check if running as root
if [[ $EUID -ne 0 ]]; then
   error "This script must be run as root (use sudo)"
   exit 1
fi

log "🚀 Setting up Ubuntu server for Collecting Website..."

# Update system
log "📦 Updating system packages..."
apt-get update && apt-get upgrade -y

# Enable universe repository for more packages
log "📦 Enabling universe repository..."
add-apt-repository universe -y
apt-get update

# Install required packages
log "📦 Installing required packages..."
apt-get install -y \
    python3 \
    python3-pip \
    python3-venv \
    git \
    nginx \
    ufw \
    curl \
    unzip \
    snapd

# Install AWS CLI via snap
log "📦 Installing AWS CLI via snap..."
snap install aws-cli --classic

# Create users
log "👤 Creating application users..."
if ! id "www-data" &>/dev/null; then
    useradd -r -s /bin/false www-data
fi

# Configure firewall
log "🔥 Configuring firewall..."
ufw --force enable
ufw default deny incoming
ufw default allow outgoing
ufw allow ssh
ufw allow 80/tcp
ufw allow 443/tcp

# Create application directory
log "📁 Creating application directory..."
mkdir -p /opt/collecting-website
chown www-data:www-data /opt/collecting-website

# Create home directory for www-data user (needed for AWS CLI snap)
log "🏠 Setting up www-data home directory..."
mkdir -p /var/lib/www-data
chown www-data:www-data /var/lib/www-data
chmod 755 /var/lib/www-data

# Set up log directory
log "📝 Setting up logging..."
mkdir -p /var/log/collecting-website
chown www-data:www-data /var/log/collecting-website

# Configure nginx
log "🌐 Configuring Nginx..."
cat > /etc/nginx/sites-available/collecting-website << 'EOF'
server {
    listen 80;
    server_name _;  # Replace with your local IP or hostname

    # Main application
    location / {
        proxy_pass http://localhost:8080;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # Health check
    location /health {
        return 200 'OK';
        add_header Content-Type text/plain;
    }
}
EOF

# Enable nginx site
ln -sf /etc/nginx/sites-available/collecting-website /etc/nginx/sites-enabled/
rm -f /etc/nginx/sites-enabled/default
nginx -t && systemctl daemon-reload && systemctl restart nginx
systemctl enable nginx

log "✅ Ubuntu server setup completed!"
log ""
log "📋 Next steps:"
log "1. Clone your repository to /opt/collecting-website"
log "2. Set up your .env file with necessary environment variables"
log "3. Run the initial deployment with: sudo /opt/collecting-website/deploy-local-simple.sh"
log ""
log "🔧 Useful commands:"
log "  - View app logs: sudo journalctl -u collecting-website -f"
log "  - Restart app: sudo systemctl restart collecting-website"
log "  - Manual deployment: sudo /opt/collecting-website/deploy-local-simple.sh"
log ""
log "🌐 Access your application at: http://$(hostname -I | awk '{print $1}')"
