#!/bin/bash
#
# Setup script to configure AWS credentials for the www-data user
# This is needed for S3 backup functionality
#

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

APP_USER="www-data"
AWS_DIR="/var/www/.aws"

echo -e "${BLUE}Setting up AWS credentials for $APP_USER user...${NC}"

# Check if running as root or with sudo
if [[ $EUID -ne 0 ]]; then
    echo -e "${RED}This script must be run with sudo${NC}"
    exit 1
fi

# Create .aws directory for www-data user
echo -e "${YELLOW}Creating AWS configuration directory...${NC}"
mkdir -p "$AWS_DIR"
chown "$APP_USER:$APP_USER" "$AWS_DIR"
chmod 700 "$AWS_DIR"

# Check if AWS CLI is installed
if ! command -v aws &> /dev/null; then
    echo -e "${YELLOW}Installing AWS CLI...${NC}"
    apt-get update
    apt-get install -y awscli
fi

echo -e "${YELLOW}Please provide your AWS credentials:${NC}"
echo -e "${BLUE}You can find these in your AWS Console > IAM > Users > [Your User] > Security credentials${NC}"
echo

# Prompt for credentials
read -p "AWS Access Key ID: " aws_access_key_id
read -s -p "AWS Secret Access Key: " aws_secret_access_key
echo
read -p "Default region (e.g., us-west-2): " aws_region
aws_region=${aws_region:-us-west-2}

# Create credentials file
echo -e "${YELLOW}Creating AWS credentials file...${NC}"
cat > "$AWS_DIR/credentials" <<EOF
[default]
aws_access_key_id = $aws_access_key_id
aws_secret_access_key = $aws_secret_access_key
EOF

# Create config file
cat > "$AWS_DIR/config" <<EOF
[default]
region = $aws_region
output = json
EOF

# Set proper permissions
chown "$APP_USER:$APP_USER" "$AWS_DIR/credentials" "$AWS_DIR/config"
chmod 600 "$AWS_DIR/credentials" "$AWS_DIR/config"

echo -e "${GREEN}AWS credentials configured successfully!${NC}"

# Test the configuration
echo -e "${YELLOW}Testing AWS configuration...${NC}"
if sudo -u "$APP_USER" aws s3 ls s3://collecting-tools-gantt-pub/ &>/dev/null; then
    echo -e "${GREEN}✅ AWS S3 access test passed!${NC}"
    echo -e "${BLUE}You can now run the backup setup:${NC}"
    echo "  cd /var/www/collecting-website"
    echo "  ./setup-backup-cron.sh"
else
    echo -e "${YELLOW}⚠️  AWS S3 access test failed${NC}"
    echo -e "${BLUE}Please verify:${NC}"
    echo "  1. Your AWS credentials are correct"
    echo "  2. The S3 bucket 'collecting-tools-gantt-pub' exists and you have access"
    echo "  3. Your IAM user has S3 permissions"
    echo
    echo -e "${BLUE}You can test manually with:${NC}"
    echo "  sudo -u $APP_USER aws s3 ls s3://collecting-tools-gantt-pub/"
fi

echo
echo -e "${GREEN}Setup complete!${NC}"
