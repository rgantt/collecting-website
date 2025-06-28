# S3 Database Backup Setup

This document describes the automated backup system for the collecting-website database to Amazon S3.

## Overview

The backup system consists of:
- `backup_to_s3.py`: Python script that uploads the games.db file to S3
- `setup-backup-cron.sh`: Setup script that configures the cron job
- Automated cron job that runs every 6 hours

## Files

### backup_to_s3.py
The main backup script that:
- Uploads the current `games.db` to S3 as `games.db` (latest backup)
- Creates timestamped backups in the `backups/` folder for historical purposes
- Logs all activities to `/var/log/collecting-website-backup.log`
- Supports dry-run mode for testing

### setup-backup-cron.sh
Setup script that:
- Makes the backup script executable
- Creates and configures the log file
- Installs a cron job for the www-data user
- Tests the backup script configuration

## Installation

### 1. Deploy the Backup Files

Make sure the following files are deployed to your server:
- `backup_to_s3.py`
- `setup-backup-cron.sh`

### 2. Install AWS Dependencies

The backup system requires boto3, which should already be in your requirements.txt:
```bash
cd /var/www/collecting-website
source venv/bin/activate
pip install -r requirements.txt
```

### 3. Configure AWS Credentials

Set up AWS credentials for the www-data user. You have two options:

**Option A: AWS Configure (Recommended)**
```bash
sudo -u www-data aws configure
```
Enter your:
- AWS Access Key ID
- AWS Secret Access Key  
- Default region (e.g., us-west-2)
- Default output format (json)

**Option B: Environment Variables**
Add to `/etc/environment` or create a credentials file:
```bash
sudo -u www-data mkdir -p /var/www/.aws
sudo -u www-data tee /var/www/.aws/credentials <<EOF
[default]
aws_access_key_id = YOUR_ACCESS_KEY_ID
aws_secret_access_key = YOUR_SECRET_ACCESS_KEY
region = us-west-2
EOF
```

### 4. Run the Setup Script

Execute the cron job setup script:
```bash
cd /var/www/collecting-website
chmod +x setup-backup-cron.sh
./setup-backup-cron.sh
```

This will:
- Install the cron job to run every 6 hours
- Set up proper permissions
- Test the backup script
- Create the log file

## Configuration

### S3 Settings

By default, the backup uses:
- **Bucket**: `collecting-tools-gantt-pub`
- **Main backup key**: `games.db`
- **Historical backups**: `backups/games_YYYYMMDD_HHMMSS.db`

To customize these settings, edit the `backup_to_s3.py` script or use command-line arguments:

```bash
python backup_to_s3.py --help
```

### Cron Schedule

By default, backups run every 6 hours. To modify the schedule:

1. Edit the cron job:
   ```bash
   sudo crontab -u www-data -e
   ```

2. Modify the schedule (current: `0 */6 * * *`)
   - Every 4 hours: `0 */4 * * *`
   - Daily at 2 AM: `0 2 * * *`
   - Twice daily: `0 2,14 * * *`

## Manual Operations

### Manual Backup
```bash
cd /var/www/collecting-website
sudo -u www-data bash -c 'source venv/bin/activate && python backup_to_s3.py'
```

### Dry Run Test
```bash
cd /var/www/collecting-website
sudo -u www-data bash -c 'source venv/bin/activate && python backup_to_s3.py --dry-run'
```

### View Logs
```bash
tail -f /var/log/collecting-website-backup.log
```

### List Cron Jobs
```bash
sudo crontab -u www-data -l
```

### Check S3 Backups
```bash
aws s3 ls s3://collecting-tools-gantt-pub/
aws s3 ls s3://collecting-tools-gantt-pub/backups/
```

## Troubleshooting

### Common Issues

**1. AWS Credentials Not Found**
```
Error: Unable to locate credentials
```
Solution: Configure AWS credentials as described in step 3 above.

**2. Permission Denied**
```
Error: [Errno 13] Permission denied: '/var/www/collecting-website/games.db'
```
Solution: Ensure www-data user has read access to the database file.

**3. S3 Access Denied**
```
Error: Access Denied
```
Solution: Verify your AWS credentials have S3 write permissions for the bucket.

**4. Cron Job Not Running**
Check if cron service is running:
```bash
sudo systemctl status cron
```

View cron logs:
```bash
grep CRON /var/log/syslog
```

### Log Analysis

Monitor backup activity:
```bash
# View recent backup attempts
tail -20 /var/log/collecting-website-backup.log

# Watch live backup activity
tail -f /var/log/collecting-website-backup.log

# Check for errors
grep ERROR /var/log/collecting-website-backup.log
```

## Backup Verification

### Automated Checks
The backup script automatically:
- Verifies the database file exists before uploading
- Logs file size and upload status
- Creates both current and timestamped backups

### Manual Verification
```bash
# Check latest backup
aws s3 ls s3://collecting-tools-gantt-pub/games.db

# Check historical backups
aws s3 ls s3://collecting-tools-gantt-pub/backups/

# Download and verify backup
aws s3 cp s3://collecting-tools-gantt-pub/games.db /tmp/games-backup.db
sqlite3 /tmp/games-backup.db "SELECT COUNT(*) FROM physical_games;"
```

## Integration with Deployment

### Automatic Setup During Deployment

To automatically configure backups during deployment, add these lines to your deployment scripts:

```bash
# Add to deploy-local-simple.sh or deploy-github-actions.sh
echo "Setting up S3 backup..."
if [[ -f setup-backup-cron.sh ]]; then
    chmod +x setup-backup-cron.sh
    ./setup-backup-cron.sh
else
    echo "Warning: setup-backup-cron.sh not found, skipping backup setup"
fi
```

### GitHub Actions Integration

The backup system works seamlessly with GitHub Actions deployment. The backup script and cron job will be updated automatically when you deploy new versions.

## Security Considerations

1. **AWS Credentials**: Store securely and use IAM policies with minimal required permissions
2. **S3 Bucket**: Consider enabling bucket versioning and lifecycle policies
3. **Log Files**: Backup logs may contain file paths but no sensitive data
4. **Network**: S3 access uses HTTPS encryption in transit

## Backup Retention

Historical backups accumulate in the `backups/` folder. Consider implementing S3 lifecycle policies to:
- Move old backups to cheaper storage classes (IA, Glacier)
- Delete backups older than a certain age
- Maintain a specific number of recent backups

Example S3 lifecycle policy:
```json
{
    "Rules": [{
        "Id": "BackupRetention",
        "Status": "Enabled",
        "Filter": {"Prefix": "backups/"},
        "Transitions": [{
            "Days": 30,
            "StorageClass": "STANDARD_IA"
        }, {
            "Days": 90,
            "StorageClass": "GLACIER"
        }],
        "Expiration": {
            "Days": 365
        }
    }]
}
```
