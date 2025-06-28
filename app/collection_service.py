import sqlite3
import logging
from pathlib import Path
from contextlib import contextmanager
from datetime import datetime
from app.pricecharting_service import PricechartingService

logger = logging.getLogger(__name__)

class CollectionService:
    """Service for managing the collection of games."""
    
    def __init__(self, db_path):
        """
        Initialize the collection service.
        
        Args:
            db_path (Path): Path to SQLite database file
        """
        self.db_path = db_path
    
    @contextmanager
    def get_db_connection(self):
        """Get a database connection."""
        conn = sqlite3.connect(self.db_path)
        try:
            yield conn
        finally:
            conn.close()
    
    def add_game_to_collection(self, url, purchase_date=None, purchase_source=None, 
                               purchase_price=None, condition="complete"):
        """
        Add a game to the collection using a pricecharting.com URL.
        
        Args:
            url (str): URL to the game on pricecharting.com
            purchase_date (str, optional): Date of purchase (YYYY-MM-DD). Defaults to current date.
            purchase_source (str, optional): Source of purchase. Defaults to None.
            purchase_price (float, optional): Price paid for the game. Defaults to None.
            condition (str, optional): Condition of the game. Defaults to "complete".
            
        Returns:
            dict: Information about the added game
            
        Raises:
            ValueError: If the URL is invalid or the game couldn't be added
        """
        # Set default purchase date to today if not provided
        if not purchase_date:
            purchase_date = datetime.now().strftime("%Y-%m-%d")
            
        # Extract game data from URL
        try:
            game_data = PricechartingService.extract_game_data_from_url(url)
            logger.info(f"Successfully extracted game data: {game_data}")
        except Exception as e:
            logger.error(f"Error extracting game data: {e}")
            raise ValueError(f"Failed to extract game data: {str(e)}")
        
        # Validate required fields
        for field in ['name', 'console', 'pricecharting_id', 'url']:
            if not game_data.get(field):
                logger.error(f"Missing required field in game data: {field}")
                game_data[field] = f"Unknown {field}" if field != 'pricecharting_id' else "999999"
                logger.warning(f"Using fallback value for {field}: {game_data[field]}")
        
        with self.get_db_connection() as conn:
            cursor = conn.cursor()
            try:
                conn.execute("BEGIN TRANSACTION")
                
                # Check if game already exists in pricecharting_games table
                cursor.execute(
                    "SELECT id FROM pricecharting_games WHERE pricecharting_id = ?", 
                    (game_data['pricecharting_id'],)
                )
                result = cursor.fetchone()
                
                if result:
                    pricecharting_game_id = result[0]
                    logger.info(f"Found existing pricecharting game with ID: {pricecharting_game_id}")
                else:
                    # Insert into pricecharting_games
                    cursor.execute(
                        "INSERT INTO pricecharting_games (pricecharting_id, name, console, url) VALUES (?, ?, ?, ?)",
                        (game_data['pricecharting_id'], game_data['name'], game_data['console'], game_data['url'])
                    )
                    pricecharting_game_id = cursor.lastrowid
                    logger.info(f"Added new pricecharting game with ID: {pricecharting_game_id}")
                
                # Check if physical game already exists
                cursor.execute(
                    "SELECT id FROM physical_games WHERE name = ? AND console = ?",
                    (game_data['name'], game_data['console'])
                )
                result = cursor.fetchone()
                
                if result:
                    physical_game_id = result[0]
                    logger.info(f"Found existing physical game with ID: {physical_game_id}")
                else:
                    # Insert into physical_games
                    cursor.execute(
                        "INSERT INTO physical_games (name, console) VALUES (?, ?)",
                        (game_data['name'], game_data['console'])
                    )
                    physical_game_id = cursor.lastrowid
                    logger.info(f"Added new physical game with ID: {physical_game_id}")
                
                # Check if purchased game already exists
                cursor.execute(
                    "SELECT id FROM purchased_games WHERE physical_game = ?",
                    (physical_game_id,)
                )
                result = cursor.fetchone()
                
                if result:
                    logger.warning(f"Game already exists in collection with ID: {result[0]}")
                    # Optionally update the purchased entry here
                    purchased_game_id = result[0]
                    # Update if needed
                    cursor.execute(
                        """UPDATE purchased_games SET 
                           condition = ?, 
                           acquisition_date = ?, 
                           source = ?, 
                           price = ? 
                           WHERE id = ?""",
                        (condition, purchase_date, purchase_source, purchase_price, purchased_game_id)
                    )
                    logger.info(f"Updated existing purchased game with ID: {purchased_game_id}")
                else:
                    # Insert into purchased_games
                    cursor.execute(
                        """INSERT INTO purchased_games 
                           (physical_game, condition, acquisition_date, source, price) 
                           VALUES (?, ?, ?, ?, ?)""",
                        (physical_game_id, condition, purchase_date, purchase_source, purchase_price)
                    )
                    purchased_game_id = cursor.lastrowid
                    logger.info(f"Added new game to collection with ID: {purchased_game_id}")
                
                # Create association between physical_game and pricecharting_game if not exists
                cursor.execute(
                    "SELECT id FROM physical_games_pricecharting_games WHERE physical_game = ? AND pricecharting_game = ?",
                    (physical_game_id, pricecharting_game_id)
                )
                association_result = cursor.fetchone()
                
                if not association_result:
                    cursor.execute(
                        "INSERT INTO physical_games_pricecharting_games (physical_game, pricecharting_game) VALUES (?, ?)",
                        (physical_game_id, pricecharting_game_id)
                    )
                    logger.info(f"Created association between physical_game {physical_game_id} and pricecharting_game {pricecharting_game_id}")
                else:
                    logger.info(f"Association already exists between physical_game {physical_game_id} and pricecharting_game {pricecharting_game_id}")
                
                # Commit the transaction
                conn.commit()
                
                # Return the game data with additional information
                response_data = {
                    'id': purchased_game_id,
                    'name': game_data['name'],
                    'console': game_data['console'],
                    'pricecharting_id': game_data['pricecharting_id'],
                    'url': game_data['url'],
                    'condition': condition,
                    'purchase_date': purchase_date,
                    'purchase_source': purchase_source,
                    'purchase_price': purchase_price
                }
                
                return response_data
                
            except Exception as e:
                conn.rollback()
                logger.error(f"Error adding game to collection: {e}")
                raise ValueError(f"Failed to add game to collection: {str(e)}")
