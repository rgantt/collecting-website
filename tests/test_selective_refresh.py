"""
Tests for selective game data refresh functionality (Phase 3)
"""
import pytest
import json
from unittest.mock import patch, MagicMock
from app import create_app
from pathlib import Path
import sqlite3
import tempfile
import os


@pytest.fixture
def app():
    """Create application for testing"""
    # Create a temporary database file
    db_fd, db_path = tempfile.mkstemp()
    
    app = create_app()
    app.config['TESTING'] = True
    app.config['DATABASE'] = db_path
    
    # Initialize the database with schema
    with app.app_context():
        init_db(db_path)
    
    yield app
    
    # Cleanup
    os.close(db_fd)
    os.unlink(db_path)


@pytest.fixture
def client(app):
    """Create a test client for the app"""
    return app.test_client()


def init_db(db_path):
    """Initialize test database with schema"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Create tables (same as in main test file)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS physical_games (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            console TEXT NOT NULL
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS wanted_games (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            physical_game INTEGER,
            condition TEXT DEFAULT 'complete',
            FOREIGN KEY (physical_game) REFERENCES physical_games(id)
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS purchased_games (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            physical_game INTEGER,
            acquisition_date DATE,
            source TEXT,
            price DECIMAL,
            condition TEXT DEFAULT 'complete',
            FOREIGN KEY (physical_game) REFERENCES physical_games(id)
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS games_for_sale (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            purchased_game_id INTEGER UNIQUE,
            asking_price REAL,
            notes TEXT,
            date_marked TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (purchased_game_id) REFERENCES purchased_games(id)
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS lent_games (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            purchased_game INTEGER,
            lent_date DATE NOT NULL,
            lent_to TEXT NOT NULL,
            note TEXT,
            returned_date DATE NULL,
            FOREIGN KEY (purchased_game) REFERENCES purchased_games(id)
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS sources (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS pricecharting_games (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            pricecharting_id INTEGER,
            name TEXT NOT NULL,
            console TEXT NOT NULL,
            url TEXT
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS pricecharting_prices (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            retrieve_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            pricecharting_id INTEGER,
            condition TEXT,
            price DECIMAL
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS physical_games_pricecharting_games (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            physical_game INTEGER,
            pricecharting_game INTEGER,
            FOREIGN KEY (physical_game) REFERENCES physical_games(id),
            FOREIGN KEY (pricecharting_game) REFERENCES pricecharting_games(id)
        )
    ''')
    
    conn.commit()
    conn.close()


class TestSelectiveGameRefresh:
    """Test suite for selective game data refresh functionality"""
    
    def test_get_single_game_api_endpoint_success(self, client):
        """Test new GET /api/game/<id> endpoint with valid game"""
        # First create a physical game
        with client.application.app_context():
            from app.routes import get_db
            with get_db() as db:
                cursor = db.cursor()
                
                # Insert physical game
                cursor.execute(
                    "INSERT INTO physical_games (name, console) VALUES (?, ?)",
                    ("Test Game", "Test Console")
                )
                physical_game_id = cursor.lastrowid
                
                # Insert purchased game
                cursor.execute(
                    "INSERT INTO purchased_games (physical_game, acquisition_date, source, price, condition) VALUES (?, ?, ?, ?, ?)",
                    (physical_game_id, "2024-01-01", "Test Store", 29.99, "complete")
                )
                
                db.commit()
        
        # Test the API endpoint
        response = client.get(f'/api/game/{physical_game_id}')
        assert response.status_code == 200
        
        data = json.loads(response.data)
        assert 'game' in data
        game = data['game']
        
        # Verify game data structure
        assert game['id'] == physical_game_id
        assert game['name'] == 'Test Game'
        assert game['console'] == 'Test Console'
        assert game['condition'] == 'complete'
        assert game['purchase_price'] == 29.99
        assert game['source_name'] is None  # No source record created
        assert game['is_wanted'] is False
        assert game['is_lent'] is False
        assert game['is_for_sale'] is False
    
    def test_get_single_game_api_endpoint_not_found(self, client):
        """Test GET /api/game/<id> endpoint with non-existent game"""
        response = client.get('/api/game/99999')
        assert response.status_code == 404
        
        data = json.loads(response.data)
        assert 'error' in data
        assert data['error'] == 'Game not found'
    
    def test_get_single_game_wishlist_item(self, client):
        """Test GET /api/game/<id> endpoint with wishlist item"""
        # Create a wishlist item
        with client.application.app_context():
            from app.routes import get_db
            with get_db() as db:
                cursor = db.cursor()
                
                # Insert physical game
                cursor.execute(
                    "INSERT INTO physical_games (name, console) VALUES (?, ?)",
                    ("Wishlist Game", "N64")
                )
                physical_game_id = cursor.lastrowid
                
                # Insert wanted game (wishlist)
                cursor.execute(
                    "INSERT INTO wanted_games (physical_game, condition) VALUES (?, ?)",
                    (physical_game_id, "CIB")
                )
                
                db.commit()
        
        # Test the API endpoint
        response = client.get(f'/api/game/{physical_game_id}')
        assert response.status_code == 200
        
        data = json.loads(response.data)
        game = data['game']
        
        assert game['name'] == 'Wishlist Game'
        assert game['console'] == 'N64'
        assert game['condition'] == 'CIB'
        assert game['is_wanted'] is True
        assert game['purchase_price'] is None
        assert game['purchased_game_id'] is None
    
    def test_get_single_game_with_lent_status(self, client):
        """Test GET /api/game/<id> endpoint with lent out game"""
        # Create a game that's lent out
        with client.application.app_context():
            from app.routes import get_db
            with get_db() as db:
                cursor = db.cursor()
                
                # Insert physical game
                cursor.execute(
                    "INSERT INTO physical_games (name, console) VALUES (?, ?)",
                    ("Lent Game", "GameCube")
                )
                physical_game_id = cursor.lastrowid
                
                # Insert purchased game
                cursor.execute(
                    "INSERT INTO purchased_games (physical_game, acquisition_date, price) VALUES (?, ?, ?)",
                    (physical_game_id, "2024-01-01", 39.99)
                )
                purchased_game_id = cursor.lastrowid
                
                # Insert lent status
                cursor.execute(
                    "INSERT INTO lent_games (purchased_game, lent_date, lent_to, note) VALUES (?, ?, ?, ?)",
                    (purchased_game_id, "2024-02-01", "Friend Name", "Test note")
                )
                
                db.commit()
        
        # Test the API endpoint
        response = client.get(f'/api/game/{physical_game_id}')
        assert response.status_code == 200
        
        data = json.loads(response.data)
        game = data['game']
        
        assert game['name'] == 'Lent Game'
        assert game['is_lent'] is True
        assert game['lent_date'] == '2024-02-01'
        assert game['lent_to'] == 'Friend Name'
        assert game['lent_note'] == 'Test note'
    
    def test_get_single_game_with_sale_status(self, client):
        """Test GET /api/game/<id> endpoint with game marked for sale"""
        # Create a game that's for sale
        with client.application.app_context():
            from app.routes import get_db
            with get_db() as db:
                cursor = db.cursor()
                
                # Insert physical game
                cursor.execute(
                    "INSERT INTO physical_games (name, console) VALUES (?, ?)",
                    ("Sale Game", "PS2")
                )
                physical_game_id = cursor.lastrowid
                
                # Insert purchased game
                cursor.execute(
                    "INSERT INTO purchased_games (physical_game, acquisition_date, price) VALUES (?, ?, ?)",
                    (physical_game_id, "2024-01-01", 19.99)
                )
                purchased_game_id = cursor.lastrowid
                
                # Insert sale status
                cursor.execute(
                    "INSERT INTO games_for_sale (purchased_game_id, asking_price, notes) VALUES (?, ?, ?)",
                    (purchased_game_id, 25.99, "Great condition")
                )
                
                db.commit()
        
        # Test the API endpoint
        response = client.get(f'/api/game/{physical_game_id}')
        assert response.status_code == 200
        
        data = json.loads(response.data)
        game = data['game']
        
        assert game['name'] == 'Sale Game'
        assert game['is_for_sale'] is True
        assert game['asking_price'] == 25.99
        assert game['sale_notes'] == 'Great condition'


if __name__ == '__main__':
    pytest.main([__file__, '-v'])