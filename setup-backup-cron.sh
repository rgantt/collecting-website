#!/bin/bash
#
# Setup script for S3 database backup cron job
# This script configures automated backups of the games.db database to S3
#

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
APP_DIR="/var/www/collecting-website"
BACKUP_SCRIPT="$APP_DIR/backup_to_s3.py"
LOG_FILE="/var/log/collecting-website-backup.log"
CRON_SCHEDULE="0 */6 * * *"  # Every 6 hours
VENV_PATH="$APP_DIR/venv"

echo -e "${BLUE}Setting up S3 backup cron job for collecting-website...${NC}"

# Check if running as root
if [[ $EUID -eq 0 ]]; then
    echo -e "${RED}This script should not be run as root. Run as the www-data user or your regular user with sudo when needed.${NC}"
    exit 1
fi

# Ensure backup script exists and is executable
if [[ ! -f "$BACKUP_SCRIPT" ]]; then
    echo -e "${RED}Backup script not found at $BACKUP_SCRIPT${NC}"
    echo "Please ensure the backup_to_s3.py script is deployed to the server."
    exit 1
fi

echo -e "${YELLOW}Making backup script executable...${NC}"
sudo chmod +x "$BACKUP_SCRIPT"

# Create log file with proper permissions
echo -e "${YELLOW}Setting up log file...${NC}"
sudo touch "$LOG_FILE"
sudo chown www-data:www-data "$LOG_FILE"
sudo chmod 644 "$LOG_FILE"

# Create the cron job entry
CRON_JOB="$CRON_SCHEDULE cd $APP_DIR && $VENV_PATH/bin/python $BACKUP_SCRIPT >> $LOG_FILE 2>&1"

echo -e "${YELLOW}Adding cron job for www-data user...${NC}"
echo "Cron schedule: $CRON_SCHEDULE (every 6 hours)"
echo "Command: $CRON_JOB"

# Add cron job for www-data user
(sudo crontab -u www-data -l 2>/dev/null | grep -v "backup_to_s3.py"; echo "$CRON_JOB") | sudo crontab -u www-data -

echo -e "${GREEN}Cron job installed successfully!${NC}"

# Test the backup script
echo -e "${YELLOW}Testing backup script...${NC}"
if sudo -u www-data bash -c "cd $APP_DIR && $VENV_PATH/bin/python $BACKUP_SCRIPT --dry-run"; then
    echo -e "${GREEN}Backup script test passed!${NC}"
else
    echo -e "${RED}Backup script test failed. Please check configuration.${NC}"
    exit 1
fi

# Show current crontab
echo -e "${BLUE}Current crontab for www-data user:${NC}"
sudo crontab -u www-data -l

echo
echo -e "${GREEN}Setup complete!${NC}"
echo -e "${BLUE}Backup Information:${NC}"
echo "  - Backup runs every 6 hours"
echo "  - Database: $APP_DIR/games.db"
echo "  - S3 Bucket: collecting-tools-gantt-pub"
echo "  - Log file: $LOG_FILE"
echo "  - Script: $BACKUP_SCRIPT"
echo
echo -e "${YELLOW}AWS Configuration Required:${NC}"
echo "Make sure AWS credentials are configured for the www-data user:"
echo "  sudo -u www-data aws configure"
echo "  Or set AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY environment variables"
echo
echo -e "${YELLOW}Manual Testing:${NC}"
echo "  Test backup: sudo -u www-data bash -c 'cd $APP_DIR && $VENV_PATH/bin/python $BACKUP_SCRIPT'"
echo "  View logs: tail -f $LOG_FILE"
echo "  List cron jobs: sudo crontab -u www-data -l"
