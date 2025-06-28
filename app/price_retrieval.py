import sqlite3
import requests
from bs4 import BeautifulSoup
import datetime
from typing import Optional, Dict, Any, Union
from flask import current_app


def extract_price(document: BeautifulSoup, selector: str) -> Optional[float]:
    """Extract price from HTML document using CSS selector."""
    if price_element := document.select_one(selector):
        price_text = price_element.text.strip()
        if price_text.startswith('$'):
            price_text = price_text[1:]
        price_text = price_text.replace(',', '')
        return None if price_text == '-' else float(price_text)
    return None


def get_game_prices(pricecharting_id: str) -> Optional[Dict[str, Any]]:
    """Retrieve current prices for a game from PriceCharting.com."""
    url = f"https://www.pricecharting.com/game/{pricecharting_id}"
    
    try:
        current_app.logger.info(f"Fetching prices from: {url}")
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        document = BeautifulSoup(response.content, 'html.parser')

        # Use UTC time explicitly
        current_time = datetime.datetime.now(datetime.timezone.utc).isoformat()

        prices = {
            'complete': extract_price(document, '#complete_price > span.price.js-price'),
            'new': extract_price(document, '#new_price > span.price.js-price'),
            'loose': extract_price(document, '#used_price > span.price.js-price')
        }
        
        current_app.logger.info(f"Retrieved prices: {prices}")
        
        return {
            'time': current_time,
            'pricecharting_id': pricecharting_id,
            'prices': prices
        }
        
    except requests.RequestException as e:
        current_app.logger.error(f"Error retrieving prices for game {pricecharting_id}: {e}")
        return None
    except Exception as e:
        current_app.logger.error(f"Unexpected error retrieving prices for game {pricecharting_id}: {e}")
        return None


def insert_price_records(price_data: Dict[str, Any], connection: Union[str, sqlite3.Connection]) -> bool:
    """Insert price records into the database."""
    if not price_data:
        return False
        
    records = []
    has_prices = False
    
    for condition, price in price_data['prices'].items():
        records.append((price_data['pricecharting_id'], price_data['time'], price, condition))
        if price is not None:
            has_prices = True
            
    # If no prices were found, insert a single null record to mark the attempt
    if not has_prices:
        records.append((price_data['pricecharting_id'], price_data['time'], None, 'new'))
    
    try:
        if isinstance(connection, str):
            with sqlite3.connect(connection) as conn:
                conn.execute("PRAGMA foreign_keys = ON")
                conn.executemany("""
                    INSERT INTO pricecharting_prices 
                    (pricecharting_id, retrieve_time, price, condition)
                    VALUES (?,?,?,?)
                """, records)
                conn.commit()
        else:
            connection.execute("PRAGMA foreign_keys = ON")
            connection.executemany("""
                INSERT INTO pricecharting_prices 
                (pricecharting_id, retrieve_time, price, condition)
                VALUES (?,?,?,?)
            """, records)
            connection.commit()
            
        current_app.logger.info(f"Inserted {len(records)} price records for game {price_data['pricecharting_id']}")
        return True
        
    except sqlite3.Error as e:
        current_app.logger.error(f"Database error inserting price records: {e}")
        return False


def update_game_prices(game_id: int, connection: Union[str, sqlite3.Connection]) -> bool:
    """Update prices for a specific game by ID."""
    try:
        # Get the pricecharting_id for this game
        if isinstance(connection, str):
            conn = sqlite3.connect(connection)
        else:
            conn = connection
            
        cursor = conn.cursor()
        cursor.execute("""
            SELECT pc.pricecharting_id
            FROM physical_games p
            LEFT JOIN physical_games_pricecharting_games pcg ON p.id = pcg.physical_game
            LEFT JOIN pricecharting_games pc ON pcg.pricecharting_game = pc.id
            WHERE p.id = ?
        """, (game_id,))
        
        result = cursor.fetchone()
        if not result or not result[0]:
            current_app.logger.warning(f"No pricecharting_id found for game {game_id}")
            return False
            
        pricecharting_id = result[0]
        
        # Fetch current prices
        price_data = get_game_prices(pricecharting_id)
        if not price_data:
            return False
            
        # Insert the new price data
        success = insert_price_records(price_data, conn)
        
        if isinstance(connection, str):
            conn.close()
            
        return success
        
    except Exception as e:
        current_app.logger.error(f"Error updating prices for game {game_id}: {e}")
        return False


def get_last_price_update(game_id: int, connection: Union[str, sqlite3.Connection]) -> Optional[str]:
    """Get the date of the last price update for a game."""
    try:
        if isinstance(connection, str):
            conn = sqlite3.connect(connection)
        else:
            conn = connection
            
        cursor = conn.cursor()
        cursor.execute("""
            SELECT MAX(pp.retrieve_time)
            FROM physical_games p
            LEFT JOIN physical_games_pricecharting_games pcg ON p.id = pcg.physical_game
            LEFT JOIN pricecharting_games pc ON pcg.pricecharting_game = pc.id
            LEFT JOIN pricecharting_prices pp ON pc.pricecharting_id = pp.pricecharting_id
            WHERE p.id = ?
        """, (game_id,))
        
        result = cursor.fetchone()
        
        if isinstance(connection, str):
            conn.close()
            
        return result[0] if result and result[0] else None
        
    except Exception as e:
        current_app.logger.error(f"Error getting last price update for game {game_id}: {e}")
        return None
