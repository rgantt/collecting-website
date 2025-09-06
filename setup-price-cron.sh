#!/bin/bash

# Setup script for daily price update cron job
# This script configures a cron job to run price updates daily

# Configuration
APP_DIR="/var/www/collecting-website"
APP_USER="www-data"
VENV_PATH="$APP_DIR/venv"
UPDATE_SCRIPT="$APP_DIR/daily_price_update.py"
LOG_FILE="/var/log/collecting-website-prices.log"
CRON_SCHEDULE="0 2 * * *"  # Daily at 2 AM
BATCH_SIZE="${PRICE_BATCH_SIZE:-50}"  # Default 50 games per day

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}Setting up daily price update cron job for collecting-website...${NC}"
echo ""

# Check if running as root or with sudo
if [[ $EUID -eq 0 ]]; then
   echo -e "${GREEN}Running with appropriate privileges${NC}"
else
   echo -e "${RED}This script should be run with sudo${NC}"
   exit 1
fi

# Check if app directory exists
if [[ ! -d "$APP_DIR" ]]; then
    echo -e "${RED}Error: Application directory $APP_DIR not found${NC}"
    exit 1
fi

# Check if daily_price_update.py exists
if [[ ! -f "$UPDATE_SCRIPT" ]]; then
    echo -e "${RED}Error: Price update script not found at $UPDATE_SCRIPT${NC}"
    exit 1
fi

# Check if virtual environment exists
if [[ ! -d "$VENV_PATH" ]]; then
    echo -e "${RED}Error: Virtual environment not found at $VENV_PATH${NC}"
    exit 1
fi

# Create log file with proper permissions
echo -e "${YELLOW}Creating log file...${NC}"
touch "$LOG_FILE"
chown $APP_USER:$APP_USER "$LOG_FILE"
chmod 644 "$LOG_FILE"
echo -e "${GREEN}Log file created at: $LOG_FILE${NC}"

# Create the cron job entry
# Include environment variables for database path and batch size
CRON_JOB="$CRON_SCHEDULE cd $APP_DIR && DATABASE_PATH=$APP_DIR/games.db PRICE_BATCH_SIZE=$BATCH_SIZE $VENV_PATH/bin/python $UPDATE_SCRIPT >> $LOG_FILE 2>&1"

echo -e "${YELLOW}Adding cron job for $APP_USER user...${NC}"
echo "Cron schedule: $CRON_SCHEDULE (daily at 2 AM)"
echo "Batch size: $BATCH_SIZE games per day"
echo "Command: $CRON_JOB"
echo ""

# Remove any existing price update cron jobs to avoid duplicates
(sudo crontab -u $APP_USER -l 2>/dev/null | grep -v "daily_price_update.py") | sudo crontab -u $APP_USER -

# Add the new cron job
(sudo crontab -u $APP_USER -l 2>/dev/null; echo "$CRON_JOB") | sudo crontab -u $APP_USER -

if [[ $? -eq 0 ]]; then
    echo -e "${GREEN}Cron job installed successfully!${NC}"
else
    echo -e "${RED}Failed to install cron job${NC}"
    exit 1
fi

# Show current crontab
echo ""
echo -e "${BLUE}Current crontab for $APP_USER user:${NC}"
sudo crontab -u $APP_USER -l
echo ""

# Test the script can run
echo -e "${YELLOW}Testing price update script (dry run)...${NC}"
cd "$APP_DIR"
if sudo -u $APP_USER DATABASE_PATH="$APP_DIR/games.db" $VENV_PATH/bin/python $UPDATE_SCRIPT --dry-run --batch-size 5 2>&1; then
    echo -e "${GREEN}Test successful! Script is ready to run.${NC}"
else
    echo -e "${RED}Test failed! Please check the script configuration.${NC}"
    exit 1
fi

echo ""
echo -e "${GREEN}Setup complete!${NC}"
echo ""
echo "Daily price updates configured with:"
echo "  Schedule: Daily at 2 AM"
echo "  Batch size: $BATCH_SIZE games"
echo "  Log file: $LOG_FILE"
echo ""
echo "Useful commands:"
echo "  View log: tail -f $LOG_FILE"
echo "  List cron jobs: sudo crontab -u $APP_USER -l"
echo "  Edit cron jobs: sudo crontab -u $APP_USER -e"
echo "  Run manually: cd $APP_DIR && sudo -u $APP_USER $VENV_PATH/bin/python $UPDATE_SCRIPT"
echo "  Test run: cd $APP_DIR && sudo -u $APP_USER $VENV_PATH/bin/python $UPDATE_SCRIPT --dry-run --verbose"
echo ""
echo -e "${BLUE}Price updates will begin automatically at the next scheduled time.${NC}"