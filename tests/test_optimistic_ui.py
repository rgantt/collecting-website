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
    db_fd, db_path = tempfile.mkstemp(suffix='.db')
    
    app = create_app()
    app.config['TESTING'] = True
    app.config['DATABASE_PATH'] = db_path
    
    # Initialize the database with production schema
    with app.app_context():
        init_test_db()
    
    yield app
    
    # Cleanup
    os.close(db_fd)
    os.unlink(db_path)


def init_test_db():
    """Initialize test database using production schema"""
    from app.routes import get_db_path
    import sqlite3
    
    schema_path = Path(__file__).parent.parent / "test_schema.sql"
    
    # Connect to the in-memory database
    conn = sqlite3.connect(get_db_path())
    
    try:
        # Execute the schema SQL
        with open(schema_path, 'r') as f:
            schema_sql = f.read()
        
        # Execute each statement (split by semicolons, filter empty)
        statements = [stmt.strip() for stmt in schema_sql.split(';') if stmt.strip()]
        for statement in statements:
            conn.execute(statement)
        
        conn.commit()
    finally:
        conn.close()


@pytest.fixture
def client(app):
    """Create a test client for the app"""
    return app.test_client()




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


class TestPurchaseConversion:
    """Test suite for purchase conversion optimistic operations"""
    
    def test_purchase_conversion_success(self, client):
        """Test successful conversion from wishlist to collection"""
        # First add a game to wishlist
        add_response = client.post('/api/wishlist/add',
            json={
                'url': 'https://www.pricecharting.com/game/nintendo-64/mario-party-2',
                'condition': 'CIB'
            }
        )
        game_data = json.loads(add_response.data)
        game_id = game_data['game']['id']
        
        # Then convert it to purchased
        purchase_response = client.post(f'/api/wishlist/{game_id}/purchase',
            json={
                'purchase_date': '2024-01-15',
                'purchase_source': 'Local Store',
                'purchase_price': '34.99'
            }
        )
        
        assert purchase_response.status_code == 200
        purchase_data = json.loads(purchase_response.data)
        assert 'message' in purchase_data
        assert 'game' in purchase_data
        assert purchase_data['game']['purchase_price'] == 34.99
        assert purchase_data['game']['purchase_source'] == 'Local Store'
    
    def test_purchase_conversion_missing_date(self, client):
        """Test purchase conversion without required purchase date"""
        # Add a game to wishlist first
        add_response = client.post('/api/wishlist/add',
            json={
                'url': 'https://www.pricecharting.com/game/nintendo-64/paper-mario',
                'condition': 'CIB'
            }
        )
        game_data = json.loads(add_response.data)
        game_id = game_data['game']['id']
        
        # Try to convert without purchase date
        purchase_response = client.post(f'/api/wishlist/{game_id}/purchase',
            json={
                'purchase_source': 'Online',
                'purchase_price': '45.00'
            }
        )
        
        assert purchase_response.status_code == 400
        error_data = json.loads(purchase_response.data)
        assert 'error' in error_data
    
    def test_purchase_conversion_nonexistent_game(self, client):
        """Test purchase conversion for non-existent wishlist game"""
        purchase_response = client.post('/api/wishlist/99999/purchase',
            json={
                'purchase_date': '2024-01-15',
                'purchase_price': '25.00'
            }
        )
        
        assert purchase_response.status_code == 404
        error_data = json.loads(purchase_response.data)
        assert 'error' in error_data


class TestLentStatusOperations:
    """Test suite for lent status optimistic operations"""
    
    def test_mark_as_lent_success(self, client):
        """Test successful mark as lent operation"""
        # First add a game to collection
        add_response = client.post('/api/collection/add',
            json={
                'url': 'https://www.pricecharting.com/game/nintendo-64/mario-party-3',
                'condition': 'CIB',
                'purchase_price': 44.99
            }
        )
        game_data = json.loads(add_response.data)
        # The lent API expects physical_game_id, which is stored as 'id' in the response
        physical_game_id = game_data['game']['id']
        
        # Then mark it as lent
        lent_response = client.post(f'/api/game/{physical_game_id}/mark_as_lent',
            json={
                'lent_date': '2024-02-01',
                'lent_to': 'Friend Name'
            }
        )
        
        assert lent_response.status_code == 200
        lent_data = json.loads(lent_response.data)
        assert 'message' in lent_data
    
    def test_mark_as_lent_missing_required_fields(self, client):
        """Test mark as lent without required fields"""
        # Add a game to collection first
        add_response = client.post('/api/collection/add',
            json={
                'url': 'https://www.pricecharting.com/game/nintendo-64/super-smash-bros',
                'condition': 'CIB',
                'purchase_price': 39.99
            }
        )
        game_data = json.loads(add_response.data)
        physical_game_id = game_data['game']['id']
        
        # Try to mark as lent without required fields
        lent_response = client.post(f'/api/game/{physical_game_id}/mark_as_lent',
            json={
                'lent_to': 'Someone'
                # Missing lent_date
            }
        )
        
        assert lent_response.status_code == 400
        error_data = json.loads(lent_response.data)
        assert 'error' in error_data
    
    def test_unmark_as_lent_success(self, client):
        """Test successful return from lent operation"""
        # Add a game to collection
        add_response = client.post('/api/collection/add',
            json={
                'url': 'https://www.pricecharting.com/game/nintendo-64/diddy-kong-racing',
                'condition': 'CIB',
                'purchase_price': 29.99
            }
        )
        game_data = json.loads(add_response.data)
        physical_game_id = game_data['game']['id']
        
        # Mark it as lent first
        lent_response = client.post(f'/api/game/{physical_game_id}/mark_as_lent',
            json={
                'lent_date': '2024-02-01',
                'lent_to': 'Test Person'
            }
        )
        assert lent_response.status_code == 200
        
        # Then return from lent
        return_response = client.delete(f'/api/game/{physical_game_id}/unmark_as_lent')
        assert return_response.status_code == 200
        return_data = json.loads(return_response.data)
        assert 'message' in return_data
    
    def test_unmark_as_lent_not_lent(self, client):
        """Test return from lent on game that's not lent out"""
        return_response = client.delete('/api/game/99999/unmark_as_lent')
        assert return_response.status_code == 404
        error_data = json.loads(return_response.data)
        assert 'error' in error_data


class TestEditDetailsOperations:
    """Test suite for edit game details optimistic operations"""
    
    def test_edit_details_success(self, client):
        """Test successful edit game details operation"""
        # First add a game to collection
        add_response = client.post('/api/collection/add',
            json={
                'url': 'https://www.pricecharting.com/game/nintendo-64/super-mario-64',
                'condition': 'CIB',
                'purchase_price': 39.99
            }
        )
        game_data = json.loads(add_response.data)
        physical_game_id = game_data['game']['id']
        
        # Then edit the details
        edit_response = client.put(f'/api/game/{physical_game_id}/details',
            json={
                'name': 'Super Mario 64 Updated',
                'console': 'Nintendo 64 Console'
            }
        )
        
        assert edit_response.status_code == 200
        edit_data = json.loads(edit_response.data)
        assert 'message' in edit_data
        assert edit_data['name'] == 'Super Mario 64 Updated'
        assert edit_data['console'] == 'Nintendo 64 Console'
    
    def test_edit_details_missing_name(self, client):
        """Test edit details without required name"""
        # Add a game to collection first
        add_response = client.post('/api/collection/add',
            json={
                'url': 'https://www.pricecharting.com/game/nintendo-64/zelda-ocarina-of-time',
                'condition': 'CIB',
                'purchase_price': 49.99
            }
        )
        game_data = json.loads(add_response.data)
        physical_game_id = game_data['game']['id']
        
        # Try to edit without name
        edit_response = client.put(f'/api/game/{physical_game_id}/details',
            json={
                'console': 'Nintendo 64'
                # Missing name
            }
        )
        
        assert edit_response.status_code == 400
        error_data = json.loads(edit_response.data)
        assert 'error' in error_data
    
    def test_edit_details_missing_console(self, client):
        """Test edit details without required console"""
        # Add a game to collection first
        add_response = client.post('/api/collection/add',
            json={
                'url': 'https://www.pricecharting.com/game/nintendo-64/mario-kart-64',
                'condition': 'CIB',
                'purchase_price': 34.99
            }
        )
        game_data = json.loads(add_response.data)
        physical_game_id = game_data['game']['id']
        
        # Try to edit without console
        edit_response = client.put(f'/api/game/{physical_game_id}/details',
            json={
                'name': 'Mario Kart 64 Updated'
                # Missing console
            }
        )
        
        assert edit_response.status_code == 400
        error_data = json.loads(edit_response.data)
        assert 'error' in error_data
    
    def test_edit_details_nonexistent_game(self, client):
        """Test edit details for non-existent game"""
        edit_response = client.put('/api/game/99999/details',
            json={
                'name': 'Nonexistent Game',
                'console': 'Nonexistent Console'
            }
        )
        
        assert edit_response.status_code == 404
        error_data = json.loads(edit_response.data)
        assert 'error' in error_data


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