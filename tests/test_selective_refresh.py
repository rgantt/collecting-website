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


class TestBatchRefreshOperations:
    """Test suite for batch refresh functionality"""
    
    def test_batch_refresh_success_multiple_games(self, client):
        """Test batch refresh with multiple valid games"""
        # Create multiple games
        game_ids = []
        with client.application.app_context():
            from app.routes import get_db
            with get_db() as db:
                cursor = db.cursor()
                
                # Insert multiple physical games
                for i, name in enumerate(['Game 1', 'Game 2', 'Game 3']):
                    cursor.execute(
                        "INSERT INTO physical_games (name, console) VALUES (?, ?)",
                        (name, f"Console {i+1}")
                    )
                    physical_game_id = cursor.lastrowid
                    game_ids.append(physical_game_id)
                    
                    # Insert purchased games
                    cursor.execute(
                        "INSERT INTO purchased_games (physical_game, acquisition_date, price) VALUES (?, ?, ?)",
                        (physical_game_id, "2024-01-01", 29.99 + i)
                    )
                
                db.commit()
        
        # Test batch refresh API
        response = client.post('/api/games/batch-refresh',
            json={'game_ids': game_ids}
        )
        
        assert response.status_code == 200
        data = json.loads(response.data)
        
        assert 'games' in data
        assert 'missing_game_ids' in data
        assert data['found_count'] == 3
        assert data['missing_count'] == 0
        assert len(data['games']) == 3
        
        # Verify game data structure
        for i, game in enumerate(data['games']):
            assert game['id'] == game_ids[i]
            assert game['name'] == f'Game {i+1}'
            assert game['console'] == f'Console {i+1}'
            assert game['purchase_price'] == 29.99 + i
    
    def test_batch_refresh_with_missing_games(self, client):
        """Test batch refresh when some games don't exist"""
        # Create one game
        with client.application.app_context():
            from app.routes import get_db
            with get_db() as db:
                cursor = db.cursor()
                
                cursor.execute(
                    "INSERT INTO physical_games (name, console) VALUES (?, ?)",
                    ("Existing Game", "Test Console")
                )
                existing_game_id = cursor.lastrowid
                
                cursor.execute(
                    "INSERT INTO purchased_games (physical_game, acquisition_date, price) VALUES (?, ?, ?)",
                    (existing_game_id, "2024-01-01", 39.99)
                )
                
                db.commit()
        
        # Request batch with existing and non-existing games
        game_ids = [existing_game_id, 99999, 99998]
        response = client.post('/api/games/batch-refresh',
            json={'game_ids': game_ids}
        )
        
        assert response.status_code == 200
        data = json.loads(response.data)
        
        assert data['found_count'] == 1
        assert data['missing_count'] == 2
        assert len(data['games']) == 1
        assert len(data['missing_game_ids']) == 2
        
        # Verify found game
        assert data['games'][0]['id'] == existing_game_id
        assert data['games'][0]['name'] == 'Existing Game'
        
        # Verify missing games
        assert 99999 in data['missing_game_ids']
        assert 99998 in data['missing_game_ids']
    
    def test_batch_refresh_invalid_request_data(self, client):
        """Test batch refresh with invalid request data"""
        # Missing game_ids
        response = client.post('/api/games/batch-refresh', json={})
        assert response.status_code == 400
        data = json.loads(response.data)
        assert 'error' in data
        
        # Non-array game_ids
        response = client.post('/api/games/batch-refresh', json={'game_ids': 'not-an-array'})
        assert response.status_code == 400
        
        # Empty game_ids array
        response = client.post('/api/games/batch-refresh', json={'game_ids': []})
        assert response.status_code == 400
        
        # Too many game_ids (over limit)
        large_array = list(range(101))  # 101 items, over the limit of 100
        response = client.post('/api/games/batch-refresh', json={'game_ids': large_array})
        assert response.status_code == 400
        data = json.loads(response.data)
        assert 'Maximum 100 games' in data['error']
    
    def test_batch_refresh_mixed_game_types(self, client):
        """Test batch refresh with wishlist and collection games"""
        with client.application.app_context():
            from app.routes import get_db
            with get_db() as db:
                cursor = db.cursor()
                
                # Create wishlist game
                cursor.execute(
                    "INSERT INTO physical_games (name, console) VALUES (?, ?)",
                    ("Wishlist Game", "N64")
                )
                wishlist_game_id = cursor.lastrowid
                
                cursor.execute(
                    "INSERT INTO wanted_games (physical_game, condition) VALUES (?, ?)",
                    (wishlist_game_id, "CIB")
                )
                
                # Create collection game
                cursor.execute(
                    "INSERT INTO physical_games (name, console) VALUES (?, ?)",
                    ("Collection Game", "GameCube")
                )
                collection_game_id = cursor.lastrowid
                
                cursor.execute(
                    "INSERT INTO purchased_games (physical_game, acquisition_date, price) VALUES (?, ?, ?)",
                    (collection_game_id, "2024-01-01", 24.99)
                )
                
                db.commit()
        
        # Test batch refresh with both types
        response = client.post('/api/games/batch-refresh',
            json={'game_ids': [wishlist_game_id, collection_game_id]}
        )
        
        assert response.status_code == 200
        data = json.loads(response.data)
        
        assert data['found_count'] == 2
        assert data['missing_count'] == 0
        
        # Find games by name to verify properties
        games_by_name = {game['name']: game for game in data['games']}
        
        # Verify wishlist game
        wishlist_game = games_by_name['Wishlist Game']
        assert wishlist_game['is_wanted'] is True
        assert wishlist_game['purchase_price'] is None
        assert wishlist_game['condition'] == 'CIB'
        
        # Verify collection game
        collection_game = games_by_name['Collection Game']
        assert collection_game['is_wanted'] is False
        assert collection_game['purchase_price'] == 24.99
    
    def test_batch_refresh_large_batch_within_limits(self, client):
        """Test batch refresh with a large but valid batch size"""
        # Create 50 games (within the 100 game limit)
        game_ids = []
        with client.application.app_context():
            from app.routes import get_db
            with get_db() as db:
                cursor = db.cursor()
                
                for i in range(50):
                    cursor.execute(
                        "INSERT INTO physical_games (name, console) VALUES (?, ?)",
                        (f"Batch Game {i}", "Test Console")
                    )
                    physical_game_id = cursor.lastrowid
                    game_ids.append(physical_game_id)
                    
                    cursor.execute(
                        "INSERT INTO purchased_games (physical_game, acquisition_date, price) VALUES (?, ?, ?)",
                        (physical_game_id, "2024-01-01", 10.00 + i)
                    )
                
                db.commit()
        
        # Test batch refresh
        response = client.post('/api/games/batch-refresh',
            json={'game_ids': game_ids}
        )
        
        assert response.status_code == 200
        data = json.loads(response.data)
        
        assert data['found_count'] == 50
        assert data['missing_count'] == 0
        assert len(data['games']) == 50
        
        # Verify games are returned in order
        for i, game in enumerate(data['games']):
            assert game['name'] == f'Batch Game {i}'
            assert game['purchase_price'] == 10.00 + i


if __name__ == '__main__':
    pytest.main([__file__, '-v'])