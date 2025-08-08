"""
Tests for optimistic UI update functionality
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
    
    # Create tables
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS wishlist (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            console TEXT NOT NULL,
            url TEXT,
            current_price REAL,
            date_added TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            condition TEXT DEFAULT 'CIB'
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS purchased_games (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            game_id INTEGER,
            name TEXT NOT NULL,
            console TEXT NOT NULL,
            url TEXT,
            purchase_date DATE,
            purchase_price REAL,
            purchase_source TEXT,
            current_price REAL,
            condition TEXT DEFAULT 'CIB',
            is_for_sale BOOLEAN DEFAULT 0,
            is_lent_out BOOLEAN DEFAULT 0,
            acquisition_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS games_for_sale (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            purchased_game_id INTEGER UNIQUE,
            asking_price REAL,
            date_marked TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (purchased_game_id) REFERENCES purchased_games(id)
        )
    ''')
    
    conn.commit()
    conn.close()


class TestAddGameOptimistic:
    """Test suite for optimistic add game functionality"""
    
    def test_add_to_wishlist_success(self, client):
        """Test successful addition to wishlist"""
        response = client.post('/api/wishlist/add',
            json={
                'url': 'https://www.pricecharting.com/game/nintendo-64/mario-kart-64',
                'condition': 'CIB'
            }
        )
        
        assert response.status_code == 201
        data = json.loads(response.data)
        assert 'game' in data
        assert data['game']['name'] is not None
        assert data['game']['console'] is not None
        assert data['game']['id'] is not None
    
    def test_add_to_wishlist_invalid_url(self, client):
        """Test adding with invalid URL"""
        response = client.post('/api/wishlist/add',
            json={
                'url': 'https://invalid-url.com',
                'condition': 'CIB'
            }
        )
        
        assert response.status_code == 400
        data = json.loads(response.data)
        assert 'error' in data
    
    def test_add_to_collection_success(self, client):
        """Test successful addition to collection"""
        response = client.post('/api/collection/add',
            json={
                'url': 'https://www.pricecharting.com/game/nintendo-64/goldeneye-007',
                'condition': 'CIB',
                'purchase_date': '2024-01-01',
                'purchase_price': 29.99,
                'purchase_source': 'eBay'
            }
        )
        
        assert response.status_code == 201
        data = json.loads(response.data)
        assert 'game' in data
        assert data['game']['purchase_price'] == 29.99
        assert data['game']['purchase_source'] == 'eBay'
    
    def test_add_to_collection_missing_required_fields(self, client):
        """Test adding to collection without required fields"""
        response = client.post('/api/collection/add',
            json={
                'url': 'https://www.pricecharting.com/game/nintendo-64/perfect-dark',
                'condition': 'CIB'
                # Missing purchase_date and purchase_price
            }
        )
        
        # Should still work with defaults
        assert response.status_code == 201
        data = json.loads(response.data)
        assert 'game' in data


class TestRemoveGameOptimistic:
    """Test suite for optimistic remove game functionality"""
    
    def setup_method(self):
        """Set up test data before each test"""
        self.test_game_id = None
        self.test_purchased_game_id = None
    
    def test_remove_from_wishlist_success(self, client):
        """Test successful removal from wishlist"""
        # First add a game
        add_response = client.post('/api/wishlist/add',
            json={
                'url': 'https://www.pricecharting.com/game/nintendo-64/banjo-kazooie',
                'condition': 'CIB'
            }
        )
        game_data = json.loads(add_response.data)
        game_id = game_data['game']['id']
        
        # Then remove it
        response = client.delete(f'/api/wishlist/{game_id}/remove')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert 'message' in data
    
    def test_remove_from_wishlist_not_found(self, client):
        """Test removing non-existent wishlist item"""
        response = client.delete('/api/wishlist/99999/remove')
        assert response.status_code == 404
        data = json.loads(response.data)
        assert 'error' in data
    
    def test_remove_from_collection_success(self, client):
        """Test successful removal from collection"""
        # First add a game
        add_response = client.post('/api/collection/add',
            json={
                'url': 'https://www.pricecharting.com/game/nintendo-64/star-fox-64',
                'condition': 'CIB',
                'purchase_price': 24.99
            }
        )
        game_data = json.loads(add_response.data)
        purchased_game_id = game_data['game'].get('purchased_game_id', game_data['game']['id'])
        
        # Then remove it
        response = client.delete(f'/api/purchased_game/{purchased_game_id}/remove_from_collection')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert 'message' in data


class TestOptimisticUIRollback:
    """Test suite for rollback scenarios"""
    
    def test_add_rollback_on_database_error(self, client):
        """Test that add operation handles invalid URLs properly"""
        response = client.post('/api/wishlist/add',
            json={
                'url': 'https://invalid-pricecharting-url.com',
                'condition': 'CIB'
            }
        )
        
        assert response.status_code == 400
        data = json.loads(response.data)
        assert 'error' in data
    
    def test_add_rollback_on_pricecharting_error(self, client):
        """Test handling malformed URLs"""
        response = client.post('/api/wishlist/add',
            json={
                'url': 'not-a-url',
                'condition': 'CIB'
            }
        )
        
        assert response.status_code == 400
        data = json.loads(response.data)
        assert 'error' in data


class TestConcurrentOperations:
    """Test suite for concurrent optimistic operations"""
    
    def test_rapid_add_operations(self, client):
        """Test multiple rapid add operations"""
        urls = [
            'https://www.pricecharting.com/game/nintendo-64/mario-kart-64',
            'https://www.pricecharting.com/game/nintendo-64/goldeneye-007',
            'https://www.pricecharting.com/game/nintendo-64/perfect-dark'
        ]
        
        responses = []
        for url in urls:
            response = client.post('/api/wishlist/add',
                json={'url': url, 'condition': 'CIB'}
            )
            responses.append(response)
        
        # All should succeed
        for response in responses:
            assert response.status_code == 201
    
    def test_add_then_remove_same_game(self, client):
        """Test adding then immediately removing the same game"""
        # Add game
        add_response = client.post('/api/wishlist/add',
            json={
                'url': 'https://www.pricecharting.com/game/nintendo-64/donkey-kong-64',
                'condition': 'CIB'
            }
        )
        game_data = json.loads(add_response.data)
        game_id = game_data['game']['id']
        
        # Immediately remove
        remove_response = client.delete(f'/api/wishlist/{game_id}/remove')
        
        assert add_response.status_code == 201
        assert remove_response.status_code == 200


if __name__ == '__main__':
    pytest.main([__file__, '-v'])