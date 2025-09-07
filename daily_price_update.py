#!/usr/bin/env python3
"""
Daily Price Update Script for Collecting Website
Retrieves current prices for N least-recently-updated games from PriceCharting.com

This script is designed to be run daily via cron to maintain up-to-date pricing
information for the game collection. It uses a controlled batch size to ensure
consistent server load and avoid overwhelming external APIs.

Usage:
    python3 daily_price_update.py [--batch-size N] [--verbose]
    
Environment Variables:
    PRICE_BATCH_SIZE: Override default batch size (default: 50)
    DATABASE_PATH: Override database location (default: games.db)
"""

import sys
import os
import sqlite3
import argparse
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Tuple, Optional
import time

# Add the app directory to the path so we can import price_retrieval
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import price retrieval functions directly to avoid Flask dependency issues
# when running as standalone script
def get_game_prices(pricecharting_id: str):
    """Import at runtime to avoid Flask dependency when running standalone."""
    import requests
    from bs4 import BeautifulSoup
    from datetime import datetime, timezone
    
    url = f"https://www.pricecharting.com/game/{pricecharting_id}"
    
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        document = BeautifulSoup(response.content, 'html.parser')
        
        current_time = datetime.now(timezone.utc).isoformat()
        
        def extract_price(selector):
            if element := document.select_one(selector):
                text = element.text.strip()
                if text.startswith('$'):
                    text = text[1:]
                text = text.replace(',', '')
                return None if text == '-' else float(text)
            return None
        
        prices = {
            'complete': extract_price('#complete_price > span.price.js-price'),
            'new': extract_price('#new_price > span.price.js-price'),
            'loose': extract_price('#used_price > span.price.js-price')
        }
        
        return {
            'time': current_time,
            'pricecharting_id': pricecharting_id,
            'prices': prices
        }
    except Exception as e:
        print(f"Error retrieving prices for {pricecharting_id}: {e}")
        return None

def insert_price_records(price_data: dict, connection):
    """Insert price records into the database."""
    if not price_data:
        return False
    
    records = []
    has_prices = False
    
    for condition, price in price_data['prices'].items():
        records.append((price_data['pricecharting_id'], price_data['time'], price, condition))
        if price is not None:
            has_prices = True
    
    # If no prices found, mark the attempt
    if not has_prices:
        records.append((price_data['pricecharting_id'], price_data['time'], None, 'new'))
    
    try:
        connection.execute("PRAGMA foreign_keys = ON")
        connection.executemany("""
            INSERT INTO pricecharting_prices 
            (pricecharting_id, retrieve_time, price, condition)
            VALUES (?,?,?,?)
        """, records)
        connection.commit()
        return True
    except Exception as e:
        print(f"Error inserting price records: {e}")
        return False

# Configuration
DEFAULT_BATCH_SIZE = 200
DEFAULT_DB_PATH = Path(__file__).parent / "games.db"
LOG_FORMAT = '%(asctime)s - %(levelname)s - %(message)s'

def setup_logging(verbose: bool = False) -> logging.Logger:
    """Configure logging for the script."""
    level = logging.DEBUG if verbose else logging.INFO
    
    # Create logger
    logger = logging.getLogger('daily_price_update')
    logger.setLevel(level)
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(level)
    console_formatter = logging.Formatter(LOG_FORMAT)
    console_handler.setFormatter(console_formatter)
    
    # File handler - logs to /var/log if available, otherwise local
    log_dir = Path('/var/log') if Path('/var/log').exists() else Path(__file__).parent
    log_file = log_dir / 'collecting-website-prices.log'
    
    try:
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(logging.INFO)
        file_formatter = logging.Formatter(LOG_FORMAT)
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)
    except PermissionError:
        # If we can't write to the log file, just use console
        logger.warning(f"Cannot write to log file {log_file}, using console only")
    
    logger.addHandler(console_handler)
    return logger

def get_eligible_games(db_path: Path, batch_size: int) -> List[Tuple[int, str, str, str]]:
    """
    Get games eligible for price updates from the database.
    
    Returns:
        List of tuples: (game_id, name, console, pricecharting_id)
    """
    try:
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT game_id, name, console, pricecharting_id
                FROM eligible_price_updates
                LIMIT ?
            """, (batch_size,))
            return cursor.fetchall()
    except sqlite3.Error as e:
        raise Exception(f"Database error retrieving eligible games: {e}")

def update_game_price(game_id: int, pricecharting_id: str, db_path: Path, logger: logging.Logger) -> bool:
    """
    Update price for a single game.
    
    Returns:
        True if successful, False otherwise
    """
    try:
        # Fetch current prices from PriceCharting
        price_data = get_game_prices(pricecharting_id)
        
        if not price_data:
            logger.warning(f"No price data retrieved for game {game_id} (PC ID: {pricecharting_id})")
            return False
        
        # Insert price records into database
        with sqlite3.connect(db_path) as conn:
            success = insert_price_records(price_data, conn)
            
        if success:
            logger.debug(f"Successfully updated prices for game {game_id}")
        else:
            logger.warning(f"Failed to insert price records for game {game_id}")
            
        return success
        
    except Exception as e:
        logger.error(f"Error updating price for game {game_id}: {e}")
        return False

def format_duration(seconds: float) -> str:
    """Format duration in seconds to human-readable string."""
    if seconds < 60:
        return f"{seconds:.1f} seconds"
    elif seconds < 3600:
        minutes = seconds / 60
        return f"{minutes:.1f} minutes"
    else:
        hours = seconds / 3600
        return f"{hours:.1f} hours"

def main():
    """Main execution function."""
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Update game prices from PriceCharting.com')
    parser.add_argument('--batch-size', type=int, 
                      default=int(os.environ.get('PRICE_BATCH_SIZE', DEFAULT_BATCH_SIZE)),
                      help=f'Number of games to update (default: {DEFAULT_BATCH_SIZE})')
    parser.add_argument('--verbose', action='store_true',
                      help='Enable verbose logging')
    parser.add_argument('--dry-run', action='store_true',
                      help='Show what would be updated without making changes')
    
    args = parser.parse_args()
    
    # Setup logging
    logger = setup_logging(args.verbose)
    
    # Get database path
    db_path = Path(os.environ.get('DATABASE_PATH', DEFAULT_DB_PATH))
    
    if not db_path.exists():
        logger.error(f"Database not found at {db_path}")
        sys.exit(1)
    
    # Start processing
    start_time = time.time()
    logger.info(f"Starting daily price update - Batch size: {args.batch_size}")
    
    try:
        # Get eligible games
        games = get_eligible_games(db_path, args.batch_size)
        
        if not games:
            logger.info("No games found needing price updates")
            return
        
        logger.info(f"Found {len(games)} games to update")
        
        if args.dry_run:
            logger.info("DRY RUN - Would update the following games:")
            for game_id, name, console, pc_id in games[:10]:  # Show first 10
                logger.info(f"  - {name} ({console}) [PC: {pc_id}]")
            if len(games) > 10:
                logger.info(f"  ... and {len(games) - 10} more")
            return
        
        # Process each game
        successful = 0
        failed = 0
        
        for i, (game_id, name, console, pricecharting_id) in enumerate(games, 1):
            # Progress indicator
            percent = (i / len(games)) * 100
            logger.info(f"[{i}/{len(games)}] ({percent:.0f}%) Updating: {name} ({console})")
            
            # Update the game
            if update_game_price(game_id, pricecharting_id, db_path, logger):
                successful += 1
            else:
                failed += 1
            
            # Small delay between requests to be respectful to PriceCharting
            # This results in roughly 1 request per second
            if i < len(games):  # Don't sleep after the last game
                time.sleep(1)
        
        # Calculate duration
        duration = time.time() - start_time
        
        # Summary
        logger.info("=" * 60)
        logger.info("DAILY PRICE UPDATE COMPLETE")
        logger.info(f"  Duration: {format_duration(duration)}")
        logger.info(f"  Successful: {successful}")
        logger.info(f"  Failed: {failed}")
        logger.info(f"  Success Rate: {(successful/len(games)*100):.1f}%")
        logger.info("=" * 60)
        
        # Exit with error code if too many failures
        if failed > successful:
            logger.error("More than half of updates failed")
            sys.exit(1)
            
    except Exception as e:
        logger.error(f"Fatal error during price update: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()