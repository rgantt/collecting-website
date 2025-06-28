#!/usr/bin/env python3
"""
Database backup script for collecting-website.
Uploads the games.db file to S3 for backup purposes.
Based on the publish_to_s3 functionality from the collecting-tools CLI.
"""

import argparse
import boto3
from datetime import datetime
import logging
import os
import sys
from pathlib import Path


def setup_logging():
    """Configure logging for the backup script."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('/var/log/collecting-website-backup.log'),
            logging.StreamHandler()
        ]
    )
    return logging.getLogger(__name__)


def backup_database(db_path: str, bucket: str = "collecting-tools-gantt-pub", key: str = "games.db"):
    """
    Backup the SQLite database to S3.
    
    Args:
        db_path: Path to the SQLite database file
        bucket: S3 bucket name
        key: S3 object key for the database file
    """
    logger = logging.getLogger(__name__)
    
    try:
        # Verify database file exists
        db_file = Path(db_path)
        if not db_file.exists():
            raise FileNotFoundError(f"Database file not found: {db_path}")
        
        # Get file size for logging
        file_size = db_file.stat().st_size
        logger.info(f"Backing up database: {db_path} ({file_size:,} bytes)")
        
        # Initialize S3 client
        s3 = boto3.client('s3')
        
        # Upload file to S3
        logger.info(f"Uploading to s3://{bucket}/{key}...")
        s3.upload_file(str(db_path), bucket, key)
        
        # Also create a timestamped backup for historical purposes
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        timestamped_key = f"backups/games_{timestamp}.db"
        logger.info(f"Creating timestamped backup: s3://{bucket}/{timestamped_key}")
        s3.upload_file(str(db_path), bucket, timestamped_key)
        
        logger.info("Database backup completed successfully!")
        return True
        
    except Exception as e:
        logger.error(f"Failed to backup database to S3: {e}")
        return False


def main():
    """Main function to handle command line arguments and execute backup."""
    parser = argparse.ArgumentParser(description='Backup collecting-website database to S3')
    parser.add_argument(
        '-d', '--db', 
        default='/var/www/collecting-website/games.db',
        help='Path to SQLite database file (default: /var/www/collecting-website/games.db)'
    )
    parser.add_argument(
        '-b', '--bucket',
        default='collecting-tools-gantt-pub',
        help='S3 bucket name (default: collecting-tools-gantt-pub)'
    )
    parser.add_argument(
        '-k', '--key',
        default='games.db',
        help='S3 object key (default: games.db)'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Show what would be done without actually uploading'
    )
    
    args = parser.parse_args()
    
    # Setup logging
    logger = setup_logging()
    
    if args.dry_run:
        logger.info(f"DRY RUN: Would backup {args.db} to s3://{args.bucket}/{args.key}")
        return 0
    
    # Perform backup
    success = backup_database(args.db, args.bucket, args.key)
    return 0 if success else 1


if __name__ == '__main__':
    sys.exit(main())
