from flask import Blueprint, request, render_template, jsonify, current_app
from werkzeug.datastructures import MultiDict
from urllib.parse import urlencode
from contextlib import contextmanager
import sqlite3
from pathlib import Path
from app.wishlist_service import WishlistService
from app.collection_service import CollectionService
from app.price_retrieval import update_game_prices, get_last_price_update

main = Blueprint('main', __name__)

def get_db_path():
    """Get database path from app config or fallback to default"""
    if current_app:
        return current_app.config.get('DATABASE_PATH', Path(__file__).parent.parent / "games.db")
    return Path(__file__).parent.parent / "games.db"

@contextmanager
def get_db():
    conn = sqlite3.connect(get_db_path())
    try:
        yield conn
    finally:
        conn.close()

# Helper function for updating URL parameters
def update_url_params(args, **kwargs):
    if not isinstance(args, MultiDict):
        args = MultiDict(args)
    params = args.copy()
    for key, value in kwargs.items():
        params[key] = value
    return '?' + urlencode(params)

def get_collection_games(page=1, per_page=30, sort_by='acquisition_date', sort_order='desc'):
    """Get paginated list of games in the collection."""
    sort_field = get_sort_field(sort_by)
    sort_direction = 'DESC' if sort_order.lower() == 'desc' else 'ASC'
    
    current_app.logger.info(f'Getting collection games with sort_field={sort_field}, direction={sort_direction}, page={page}, per_page={per_page}')
    
    with get_db() as db:
        cursor = db.cursor()
        
        # Get paginated games with their latest prices
        query = f"""
            WITH latest_prices AS (
                SELECT 
                    pricecharting_id,
                    condition,
                    price,
                    ROW_NUMBER() OVER (PARTITION BY pricecharting_id, condition ORDER BY retrieve_time DESC) as rn
                FROM pricecharting_prices
            ),
            games_with_prices AS (
                SELECT 
                    p.id as id,
                    pg.id as purchased_game_id,
                    p.name as name,
                    p.console as console,
                    COALESCE(w.condition, pg.condition) as condition,
                    s.name as source_name,
                    CAST(pg.price AS DECIMAL) as purchase_price,
                    CAST(lp.price AS DECIMAL) as current_price,
                    pg.acquisition_date as date,
                    CASE WHEN w.physical_game IS NOT NULL THEN 1 ELSE 0 END as is_wanted,
                    CASE WHEN l.id IS NOT NULL THEN 1 ELSE 0 END as is_lent,
                    l.lent_date,
                    l.lent_to,
                    l.note,
                    CASE WHEN gfs.id IS NOT NULL THEN 1 ELSE 0 END as is_for_sale,
                    gfs.asking_price,
                    gfs.notes as sale_notes,
                    gfs.date_marked as sale_date_marked
                FROM physical_games p
                LEFT JOIN purchased_games pg ON p.id = pg.physical_game
                LEFT JOIN wanted_games w ON p.id = w.physical_game
                LEFT JOIN sources s ON pg.source = s.name
                LEFT JOIN physical_games_pricecharting_games pcg ON p.id = pcg.physical_game
                LEFT JOIN pricecharting_games pc ON pcg.pricecharting_game = pc.id
                LEFT JOIN latest_prices lp ON pc.pricecharting_id = lp.pricecharting_id 
                    AND (
                        (pg.condition IS NOT NULL AND LOWER(lp.condition) = LOWER(pg.condition))
                        OR 
                        (w.condition IS NOT NULL AND LOWER(lp.condition) = LOWER(w.condition))
                    )
                    AND lp.rn = 1
                LEFT JOIN lent_games l ON pg.id = l.purchased_game
                LEFT JOIN games_for_sale gfs ON pg.id = gfs.purchased_game_id
                WHERE pg.physical_game IS NOT NULL OR w.physical_game IS NOT NULL
            )
            SELECT 
                id, purchased_game_id, name, console, condition, source_name, 
                purchase_price, current_price, date, is_wanted, is_lent,
                lent_date, lent_to, note, is_for_sale, asking_price, sale_notes, sale_date_marked
            FROM games_with_prices
            ORDER BY 
                CASE WHEN {sort_field} IS NULL THEN 1 ELSE 0 END,
                {sort_field} {sort_direction},
                name ASC
            LIMIT ? OFFSET ?
        """
        current_app.logger.info(f'Executing query: {query}')
        cursor.execute(query, (per_page, (page - 1) * per_page))
        
        collection_games = []
        for row in cursor.fetchall():
            id, purchased_game_id, name, console, condition, source, purchase_price, current_price, date, is_wanted, is_lent, lent_date, lent_to, note, is_for_sale, asking_price, sale_notes, sale_date_marked = row
            collection_games.append({
                'id': id,
                'purchased_game_id': purchased_game_id,
                'name': name,
                'console': console,
                'condition': condition,
                'source': source or None,
                'purchase_price': float(purchase_price) if purchase_price else None,
                'current_price': float(current_price) if current_price else None,
                'acquisition_date': date,
                'is_wanted': bool(is_wanted),
                'is_lent': bool(is_lent),
                'lent_date': lent_date,
                'lent_to': lent_to,
                'note': note,
                'is_for_sale': bool(is_for_sale),
                'asking_price': float(asking_price) if asking_price else None,
                'sale_notes': sale_notes,
                'sale_date_marked': sale_date_marked
            })
        
        current_app.logger.info(f'Found {len(collection_games)} games')
        return collection_games

def get_wishlist_items_sorted(wishlist_sort='name', wishlist_order='asc'):
    sort_field = get_wishlist_sort_field(wishlist_sort)
    sort_direction = 'DESC' if wishlist_order == 'desc' else 'ASC'
    
    with get_db() as db:
        cursor = db.cursor()
        cursor.execute(f"""
            WITH latest_prices AS (
                SELECT 
                    pricecharting_id,
                    condition,
                    price,
                    ROW_NUMBER() OVER (PARTITION BY pricecharting_id, condition ORDER BY retrieve_time DESC) as rn
                FROM pricecharting_prices
            )
            SELECT 
                p.name,
                p.console,
                CAST(lp_complete.price AS DECIMAL) as price_complete,
                CAST(lp_loose.price AS DECIMAL) as price_loose,
                CAST(lp_new.price AS DECIMAL) as price_new
            FROM wanted_games w
            JOIN physical_games p ON w.physical_game = p.id
            LEFT JOIN physical_games_pricecharting_games pcg ON p.id = pcg.physical_game
            LEFT JOIN pricecharting_games pc ON pcg.pricecharting_game = pc.id
            LEFT JOIN latest_prices lp_complete ON pc.pricecharting_id = lp_complete.pricecharting_id 
                AND LOWER(lp_complete.condition) = 'complete'
                AND lp_complete.rn = 1
            LEFT JOIN latest_prices lp_loose ON pc.pricecharting_id = lp_loose.pricecharting_id 
                AND LOWER(lp_loose.condition) = 'loose'
                AND lp_loose.rn = 1
            LEFT JOIN latest_prices lp_new ON pc.pricecharting_id = lp_new.pricecharting_id 
                AND LOWER(lp_new.condition) = 'new'
                AND lp_new.rn = 1
            ORDER BY {sort_field} {sort_direction}, p.name
        """)
        
        wishlist = []
        for row in cursor.fetchall():
            name, console, price_complete, price_loose, price_new = row
            wishlist.append({
                'name': name,
                'console': console,
                'price_complete': float(price_complete) if price_complete else None,
                'price_loose': float(price_loose) if price_loose else None,
                'price_new': float(price_new) if price_new else None
            })
        
        return wishlist

def get_sort_field(sort_by: str) -> str:
    valid_sort_fields = {
        'name': 'name',
        'console': 'console',
        'condition': 'condition',
        'source': 'source_name',
        'purchase_price': 'purchase_price',
        'current_price': 'current_price',
        'date': 'date',
        'acquisition_date': 'date'
    }
    return valid_sort_fields.get(sort_by, 'date')

def get_wishlist_sort_field(sort_by: str) -> str:
    valid_sort_fields = {
        'name': 'p.name',
        'console': 'p.console',
        'price_complete': 'CAST(lp_complete.price AS DECIMAL)',
        'price_loose': 'CAST(lp_loose.price AS DECIMAL)',
        'price_new': 'CAST(lp_new.price AS DECIMAL)'
    }
    return valid_sort_fields.get(sort_by, 'p.name')

@main.route('/')
def index():
    page = request.args.get('page', 1, type=int)
    per_page = 30
    sort_by = request.args.get('sort', 'acquisition_date')
    sort_order = request.args.get('order', 'desc')
    wishlist_sort = request.args.get('wishlist_sort', 'name')
    wishlist_order = request.args.get('wishlist_order', 'asc')

    current_app.logger.info(f'Page: {page}, Sort: {sort_by}, Order: {sort_order}')
    
    # Get total count for pagination
    with get_db() as db:
        cursor = db.cursor()
        cursor.execute("SELECT COUNT(*) FROM purchased_games pg JOIN physical_games p ON pg.physical_game = p.id")
        total_items = cursor.fetchone()[0]
    
    total_pages = (total_items + per_page - 1) // per_page

    collection_games = get_collection_games(page, per_page, sort_by, sort_order)
    wishlist_items = get_wishlist_items_sorted(wishlist_sort, wishlist_order)

    return render_template('index.html',
                         collection_games=collection_games,
                         wishlist=wishlist_items,
                         current_page=page,
                         total_pages=total_pages,
                         sort_by=sort_by,
                         sort_order=sort_order,
                         wishlist_sort=wishlist_sort,
                         wishlist_order=wishlist_order)

@main.route('/api/collection')
def get_all_collection_games():
    """Get all games for client-side operations."""
    # Use existing function but get all games without pagination
    collection_games = get_collection_games(page=1, per_page=10000)  # Large number to get all games
    
    # Calculate totals across all games
    total_acquisition_price = 0
    total_current_price = 0
    
    for game in collection_games:
        if game['purchase_price']:
            total_acquisition_price += game['purchase_price']
        if game['current_price']:
            total_current_price += game['current_price']
    
    return jsonify({
        'games': collection_games,
        'totals': {
            'total_acquisition_price': total_acquisition_price,
            'total_current_price': total_current_price
        }
    })

@main.route('/api/wishlist/add', methods=['POST'])
def add_to_wishlist():
    """Add a game to the wishlist from a pricecharting.com URL."""
    try:
        data = request.get_json()
        current_app.logger.info(f"Received wishlist add request with data: {data}")
        
        if not data or 'url' not in data:
            current_app.logger.warning("Missing URL in wishlist add request")
            return jsonify({"error": "URL is required"}), 400
        
        url = data.get('url')
        condition = data.get('condition', 'complete')
        
        current_app.logger.info(f"Adding game to wishlist with URL: {url}, condition: {condition}")
        wishlist_service = WishlistService(get_db_path())
        result = wishlist_service.add_game_to_wishlist(url, condition)
        
        current_app.logger.info(f"Successfully added game to wishlist: {result}")
        return jsonify({"success": True, "game": result}), 201
    
    except ValueError as e:
        current_app.logger.error(f"Error adding game to wishlist: {str(e)}")
        return jsonify({"error": str(e)}), 400
    
    except Exception as e:
        current_app.logger.error(f"Unexpected error adding game to wishlist: {str(e)}")
        return jsonify({"error": "An unexpected error occurred"}), 500

@main.route('/api/collection/add', methods=['POST'])
def add_to_collection():
    """Add a game to the collection from a pricecharting.com URL."""
    try:
        data = request.get_json()
        current_app.logger.info(f"Received collection add request with data: {data}")
        
        if not data or 'url' not in data:
            current_app.logger.warning("Missing URL in collection add request")
            return jsonify({"error": "URL is required"}), 400
        
        url = data.get('url')
        condition = data.get('condition', 'complete')
        purchase_date = data.get('purchase_date')
        purchase_source = data.get('purchase_source')
        purchase_price = data.get('purchase_price')
        
        # Convert price to float if present
        if purchase_price:
            try:
                purchase_price = float(purchase_price)
            except ValueError:
                current_app.logger.warning(f"Invalid price format: {purchase_price}")
                return jsonify({"error": "Price must be a valid number"}), 400
        
        current_app.logger.info(f"Adding game to collection with URL: {url}, condition: {condition}, " +
                              f"date: {purchase_date}, source: {purchase_source}, price: {purchase_price}")
        
        collection_service = CollectionService(get_db_path())
        result = collection_service.add_game_to_collection(
            url, 
            purchase_date=purchase_date,
            purchase_source=purchase_source,
            purchase_price=purchase_price,
            condition=condition
        )
        
        current_app.logger.info(f"Successfully added game to collection: {result}")
        return jsonify({"success": True, "game": result}), 201
    
    except ValueError as e:
        current_app.logger.error(f"Error adding game to collection: {str(e)}")
        return jsonify({"error": str(e)}), 400
    
    except Exception as e:
        current_app.logger.error(f"Unexpected error adding game to collection: {str(e)}")
        return jsonify({"error": "An unexpected error occurred"}), 500

@main.route('/api/game/<int:game_id>/price_history')
def get_game_price_history(game_id):
    """Get price history data for a specific game."""
    try:
        with get_db() as db:
            cursor = db.cursor()
            
            # First, get the pricecharting_id and condition for this game
            cursor.execute("""
                SELECT pc.pricecharting_id, COALESCE(pg.condition, w.condition) as condition
                FROM physical_games p
                LEFT JOIN purchased_games pg ON p.id = pg.physical_game
                LEFT JOIN wanted_games w ON p.id = w.physical_game
                LEFT JOIN physical_games_pricecharting_games pcg ON p.id = pcg.physical_game
                LEFT JOIN pricecharting_games pc ON pcg.pricecharting_game = pc.id
                WHERE p.id = ?
            """, (game_id,))
            
            result = cursor.fetchone()
            if not result:
                return jsonify({"error": "Game not found"}), 404
                
            pricecharting_id, condition = result
            
            if not pricecharting_id:
                return jsonify({"error": "No price data available for this game"}), 404
            
            # Now get all price observations for this game and condition
            cursor.execute("""
                SELECT 
                    price,
                    retrieve_time
                FROM pricecharting_prices
                WHERE pricecharting_id = ? AND LOWER(condition) = LOWER(?)
                ORDER BY retrieve_time ASC
            """, (pricecharting_id, condition))
            
            price_history = []
            for row in cursor.fetchall():
                price, retrieve_time = row
                price_history.append({
                    'price': float(price) if price else None,
                    'date': retrieve_time
                })
            
            return jsonify(price_history)
    
    except Exception as e:
        current_app.logger.error(f"Error getting price history: {str(e)}")
        return jsonify({"error": "An unexpected error occurred"}), 500

@main.route('/api/game/<int:game_id>/update_price', methods=['POST'])
def update_game_price(game_id):
    """Update the price for a specific game by scraping PriceCharting."""
    try:
        current_app.logger.info(f"Updating price for game ID: {game_id}")
        
        # First check if the game exists and has a pricecharting_id
        with get_db() as db:
            cursor = db.cursor()
            cursor.execute("""
                SELECT p.name, pc.pricecharting_id
                FROM physical_games p
                LEFT JOIN physical_games_pricecharting_games pcg ON p.id = pcg.physical_game
                LEFT JOIN pricecharting_games pc ON pcg.pricecharting_game = pc.id
                WHERE p.id = ?
            """, (game_id,))
            
            result = cursor.fetchone()
            if not result:
                current_app.logger.warning(f"Game with ID {game_id} not found")
                return jsonify({"success": False, "error": "Game not found"}), 404
                
            game_name, pricecharting_id = result
            if not pricecharting_id:
                current_app.logger.warning(f"Game '{game_name}' (ID: {game_id}) has no PriceCharting association")
                return jsonify({"success": False, "error": "This game is not linked to PriceCharting and cannot have prices updated. Games added manually may not have price tracking."}), 400
        
        with get_db() as db:
            success = update_game_prices(game_id, db)
            
            if success:
                current_app.logger.info(f"Successfully updated price for game {game_id}")
                return jsonify({"success": True, "message": "Price updated successfully"})
            else:
                current_app.logger.warning(f"Failed to update price for game {game_id} - price retrieval failed")
                return jsonify({"success": False, "error": "Failed to retrieve current prices from PriceCharting"}), 400
                
    except Exception as e:
        current_app.logger.error(f"Error updating price for game {game_id}: {str(e)}")
        return jsonify({"success": False, "error": "An unexpected error occurred"}), 500

@main.route('/api/game/<int:game_id>/last_price_update', methods=['GET'])
def get_game_last_price_update(game_id):
    """Get the date of the last price update for a specific game."""
    try:
        last_update = get_last_price_update(game_id, str(get_db_path()))
        return jsonify({
            "success": True,
            "last_update": last_update
        })
    except Exception as e:
        current_app.logger.error(f"Error getting last price update for game {game_id}: {str(e)}")
        return jsonify({"error": str(e)}), 500

@main.route('/api/wishlist/<int:game_id>/purchase', methods=['POST'])
def purchase_wishlist_game(game_id):
    """Convert a wishlist game to a purchased collection item."""
    try:
        data = request.get_json()
        current_app.logger.info(f"Received purchase request for game {game_id} with data: {data}")
        
        # Validate required fields
        purchase_date = data.get('purchase_date')
        purchase_source = data.get('purchase_source')
        purchase_price = data.get('purchase_price')
        
        if not purchase_date:
            return jsonify({"error": "Purchase date is required"}), 400
        
        # Convert price to float if present
        if purchase_price:
            try:
                purchase_price = float(purchase_price)
            except ValueError:
                current_app.logger.warning(f"Invalid price format: {purchase_price}")
                return jsonify({"error": "Price must be a valid number"}), 400
        
        current_app.logger.info(f"Converting wishlist game {game_id} to purchased: date={purchase_date}, source={purchase_source}, price={purchase_price}")
        
        with get_db() as db:
            cursor = db.cursor()
            
            # First, get the physical game info and condition from wanted_games
            cursor.execute(
                "SELECT pg.id, wg.condition FROM wanted_games wg JOIN physical_games pg ON wg.physical_game = pg.id WHERE pg.id = ?",
                (game_id,)
            )
            result = cursor.fetchone()
            
            if not result:
                return jsonify({"error": "Game not found in wishlist"}), 404
            
            physical_game_id, condition = result
            
            # Insert into purchased_games table
            cursor.execute(
                "INSERT INTO purchased_games (physical_game, acquisition_date, source, price, condition) VALUES (?, ?, ?, ?, ?)",
                (physical_game_id, purchase_date, purchase_source, purchase_price, condition)
            )
            
            # Remove from wanted_games table
            cursor.execute(
                "DELETE FROM wanted_games WHERE physical_game = ?",
                (physical_game_id,)
            )
            
            db.commit()
            
            # Get the updated game info to return
            cursor.execute(
                "SELECT p.name, p.console FROM pricecharting_games p JOIN physical_games_pricecharting_games pg ON p.id = pg.pricecharting_game WHERE pg.physical_game = ?",
                (physical_game_id,)
            )
            game_info = cursor.fetchone()
            
            if game_info:
                name, console = game_info
                current_app.logger.info(f"Successfully converted wishlist game {game_id} to purchased")
                return jsonify({
                    "success": True,
                    "message": f"Successfully purchased {name} ({console})!",
                    "game": {
                        "id": game_id,
                        "name": name,
                        "console": console,
                        "purchase_date": purchase_date,
                        "purchase_source": purchase_source,
                        "purchase_price": purchase_price
                    }
                }), 200
            else:
                return jsonify({"error": "Game information not found"}), 500
    
    except Exception as e:
        current_app.logger.error(f"Error purchasing wishlist game {game_id}: {str(e)}")
        return jsonify({"error": str(e)}), 500

@main.route('/api/wishlist/<int:game_id>/condition', methods=['PUT'])
def update_wishlist_condition(game_id):
    """Update the condition of a wishlist game."""
    try:
        data = request.get_json()
        if not data or 'condition' not in data:
            return jsonify({"error": "Condition is required"}), 400
        
        condition = data['condition']
        
        # Validate condition
        valid_conditions = ['complete', 'loose', 'new']
        if condition not in valid_conditions:
            return jsonify({"error": f"Invalid condition. Must be one of: {', '.join(valid_conditions)}"}), 400
        
        current_app.logger.info(f"Updating wishlist game {game_id} condition to: {condition}")
        
        with get_db() as db:
            cursor = db.cursor()
            
            # Check if the game exists in wishlist
            cursor.execute(
                "SELECT id FROM wanted_games WHERE physical_game = ?",
                (game_id,)
            )
            
            if not cursor.fetchone():
                return jsonify({"error": "Game not found in wishlist"}), 404
            
            # Update the condition
            cursor.execute(
                "UPDATE wanted_games SET condition = ? WHERE physical_game = ?",
                (condition, game_id)
            )
            
            db.commit()
            
            current_app.logger.info(f"Successfully updated wishlist game {game_id} condition to {condition}")
            return jsonify({
                "message": "Condition updated successfully",
                "game_id": game_id,
                "condition": condition
            })
            
    except Exception as e:
        current_app.logger.error(f"Error updating wishlist game {game_id} condition: {str(e)}")
        return jsonify({"error": str(e)}), 500

@main.route('/api/collection/<int:game_id>/condition', methods=['PUT'])
def update_collection_condition(game_id):
    """Update the condition of a purchased collection game."""
    try:
        data = request.get_json()
        if not data or 'condition' not in data:
            return jsonify({"error": "Condition is required"}), 400
        
        condition = data['condition']
        
        # Validate condition
        valid_conditions = ['complete', 'loose', 'new']
        if condition not in valid_conditions:
            return jsonify({"error": f"Invalid condition. Must be one of: {', '.join(valid_conditions)}"}), 400
        
        current_app.logger.info(f"Updating collection game {game_id} condition to: {condition}")
        
        with get_db() as db:
            cursor = db.cursor()
            
            # Check if the game exists in purchased collection
            cursor.execute(
                "SELECT id FROM purchased_games WHERE physical_game = ?",
                (game_id,)
            )
            
            if not cursor.fetchone():
                return jsonify({"error": "Game not found in purchased collection"}), 404
            
            # Update the condition
            cursor.execute(
                "UPDATE purchased_games SET condition = ? WHERE physical_game = ?",
                (condition, game_id)
            )
            
            db.commit()
            
            current_app.logger.info(f"Successfully updated collection game {game_id} condition to {condition}")
            return jsonify({
                "message": "Condition updated successfully",
                "game_id": game_id,
                "condition": condition
            })
            
    except Exception as e:
        current_app.logger.error(f"Error updating collection game {game_id} condition: {str(e)}")
        return jsonify({"error": str(e)}), 500

@main.route('/api/game/<int:game_id>/details', methods=['PUT'])
def update_game_details(game_id):
    """Update the name and console of a game."""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "JSON data is required"}), 400
        
        name = data.get('name', '').strip()
        console = data.get('console', '').strip()
        
        # Validate inputs
        if not name:
            return jsonify({"error": "Game name is required"}), 400
        if not console:
            return jsonify({"error": "Console is required"}), 400
        
        current_app.logger.info(f"Updating game {game_id} details - name: {name}, console: {console}")
        
        with get_db() as db:
            cursor = db.cursor()
            
            # Check if the game exists
            cursor.execute(
                "SELECT id, name, console FROM physical_games WHERE id = ?",
                (game_id,)
            )
            
            game = cursor.fetchone()
            if not game:
                return jsonify({"error": "Game not found"}), 404
            
            old_name, old_console = game[1], game[2]
            
            # Update the game details
            cursor.execute(
                "UPDATE physical_games SET name = ?, console = ? WHERE id = ?",
                (name, console, game_id)
            )
            
            db.commit()
            
            current_app.logger.info(f"Successfully updated game {game_id} from '{old_name}' ({old_console}) to '{name}' ({console})")
            return jsonify({
                "message": "Game details updated successfully",
                "game_id": game_id,
                "name": name,
                "console": console,
                "old_name": old_name,
                "old_console": old_console
            })
            
    except Exception as e:
        current_app.logger.error(f"Error updating game {game_id} details: {str(e)}")
        return jsonify({"error": "Failed to update game details"}), 500

@main.route('/api/game/<int:game_id>', methods=['GET'])
def get_single_game(game_id):
    """Get data for a single game by physical game ID."""
    try:
        current_app.logger.info(f"Getting single game data for game ID: {game_id}")
        
        with get_db() as db:
            cursor = db.cursor()
            
            # Use same query structure as get_collection_games but for a single game
            query = """
                WITH latest_prices AS (
                    SELECT 
                        pricecharting_id,
                        condition,
                        price,
                        ROW_NUMBER() OVER (PARTITION BY pricecharting_id, condition ORDER BY retrieve_time DESC) as rn
                    FROM pricecharting_prices
                ),
                games_with_prices AS (
                    SELECT 
                        p.id as id,
                        pg.id as purchased_game_id,
                        p.name as name,
                        p.console as console,
                        COALESCE(w.condition, pg.condition) as condition,
                        s.name as source_name,
                        CAST(pg.price AS DECIMAL) as purchase_price,
                        CAST(lp.price AS DECIMAL) as current_price,
                        pg.acquisition_date as date,
                        CASE WHEN w.physical_game IS NOT NULL THEN 1 ELSE 0 END as is_wanted,
                        CASE WHEN l.id IS NOT NULL THEN 1 ELSE 0 END as is_lent,
                        l.lent_date,
                        l.lent_to,
                        l.note as lent_note,
                        CASE WHEN gfs.id IS NOT NULL THEN 1 ELSE 0 END as is_for_sale,
                        gfs.asking_price,
                        gfs.notes as sale_notes,
                        gfs.date_marked as sale_date_marked,
                        pc.url as pricecharting_url,
                        pc.pricecharting_id
                    FROM physical_games p
                    LEFT JOIN purchased_games pg ON p.id = pg.physical_game
                    LEFT JOIN wanted_games w ON p.id = w.physical_game
                    LEFT JOIN sources s ON pg.source = s.name
                    LEFT JOIN physical_games_pricecharting_games pcg ON p.id = pcg.physical_game
                    LEFT JOIN pricecharting_games pc ON pcg.pricecharting_game = pc.id
                    LEFT JOIN latest_prices lp ON pc.pricecharting_id = lp.pricecharting_id 
                        AND lp.rn = 1
                        AND (
                            (pg.condition IS NOT NULL AND LOWER(lp.condition) = LOWER(pg.condition))
                            OR (w.condition IS NOT NULL AND LOWER(lp.condition) = LOWER(w.condition))
                        )
                    LEFT JOIN lent_games l ON pg.id = l.purchased_game AND l.returned_date IS NULL
                    LEFT JOIN games_for_sale gfs ON pg.id = gfs.purchased_game_id
                    WHERE p.id = ?
                )
                SELECT * FROM games_with_prices
            """
            
            cursor.execute(query, (game_id,))
            row = cursor.fetchone()
            
            if not row:
                return jsonify({"error": "Game not found"}), 404
                
            # Convert row to dictionary
            columns = [desc[0] for desc in cursor.description]
            game_data = dict(zip(columns, row))
            
            # Convert boolean fields
            game_data['is_wanted'] = bool(game_data['is_wanted'])
            game_data['is_lent'] = bool(game_data['is_lent'])
            game_data['is_for_sale'] = bool(game_data['is_for_sale'])
            
            current_app.logger.info(f"Successfully retrieved game data: {game_data['name']} ({game_data['console']})")
            return jsonify({"game": game_data})
            
    except Exception as e:
        current_app.logger.error(f"Error getting single game {game_id}: {str(e)}")
        return jsonify({"error": "Failed to get game data"}), 500

@main.route('/api/games/batch-refresh', methods=['POST'])
def batch_refresh_games():
    """Get data for multiple games by physical game IDs."""
    try:
        data = request.get_json()
        if not data or 'game_ids' not in data:
            return jsonify({"error": "game_ids array is required"}), 400
            
        game_ids = data['game_ids']
        if not isinstance(game_ids, list) or len(game_ids) == 0:
            return jsonify({"error": "game_ids must be a non-empty array"}), 400
            
        # Limit batch size to prevent abuse
        if len(game_ids) > 100:
            return jsonify({"error": "Maximum 100 games per batch request"}), 400
            
        current_app.logger.info(f"Batch refreshing {len(game_ids)} games: {game_ids}")
        
        with get_db() as db:
            cursor = db.cursor()
            
            # Use same query structure as single game but with IN clause
            placeholders = ','.join(['?' for _ in game_ids])
            query = f"""
                WITH latest_prices AS (
                    SELECT 
                        pricecharting_id,
                        condition,
                        price,
                        ROW_NUMBER() OVER (PARTITION BY pricecharting_id, condition ORDER BY retrieve_time DESC) as rn
                    FROM pricecharting_prices
                ),
                games_with_prices AS (
                    SELECT 
                        p.id as id,
                        pg.id as purchased_game_id,
                        p.name as name,
                        p.console as console,
                        COALESCE(w.condition, pg.condition) as condition,
                        s.name as source_name,
                        CAST(pg.price AS DECIMAL) as purchase_price,
                        CAST(lp.price AS DECIMAL) as current_price,
                        pg.acquisition_date as date,
                        CASE WHEN w.physical_game IS NOT NULL THEN 1 ELSE 0 END as is_wanted,
                        CASE WHEN l.id IS NOT NULL THEN 1 ELSE 0 END as is_lent,
                        l.lent_date,
                        l.lent_to,
                        l.note as lent_note,
                        CASE WHEN gfs.id IS NOT NULL THEN 1 ELSE 0 END as is_for_sale,
                        gfs.asking_price,
                        gfs.notes as sale_notes,
                        gfs.date_marked as sale_date_marked,
                        pc.url as pricecharting_url,
                        pc.pricecharting_id
                    FROM physical_games p
                    LEFT JOIN purchased_games pg ON p.id = pg.physical_game
                    LEFT JOIN wanted_games w ON p.id = w.physical_game
                    LEFT JOIN sources s ON pg.source = s.name
                    LEFT JOIN physical_games_pricecharting_games pcg ON p.id = pcg.physical_game
                    LEFT JOIN pricecharting_games pc ON pcg.pricecharting_game = pc.id
                    LEFT JOIN latest_prices lp ON pc.pricecharting_id = lp.pricecharting_id 
                        AND lp.rn = 1
                        AND (
                            (pg.condition IS NOT NULL AND LOWER(lp.condition) = LOWER(pg.condition))
                            OR (w.condition IS NOT NULL AND LOWER(lp.condition) = LOWER(w.condition))
                        )
                    LEFT JOIN lent_games l ON pg.id = l.purchased_game AND l.returned_date IS NULL
                    LEFT JOIN games_for_sale gfs ON pg.id = gfs.purchased_game_id
                    WHERE p.id IN ({placeholders})
                )
                SELECT * FROM games_with_prices ORDER BY id
            """
            
            cursor.execute(query, game_ids)
            rows = cursor.fetchall()
            
            # Convert rows to dictionaries
            columns = [desc[0] for desc in cursor.description]
            games_data = []
            found_game_ids = []
            
            for row in rows:
                game_data = dict(zip(columns, row))
                
                # Convert boolean fields
                game_data['is_wanted'] = bool(game_data['is_wanted'])
                game_data['is_lent'] = bool(game_data['is_lent'])
                game_data['is_for_sale'] = bool(game_data['is_for_sale'])
                
                games_data.append(game_data)
                found_game_ids.append(game_data['id'])
            
            # Determine which games were not found (deleted)
            missing_game_ids = [gid for gid in game_ids if gid not in found_game_ids]
            
            current_app.logger.info(f"Batch refresh found {len(games_data)} games, {len(missing_game_ids)} missing")
            
            return jsonify({
                "games": games_data,
                "missing_game_ids": missing_game_ids,
                "found_count": len(games_data),
                "missing_count": len(missing_game_ids)
            })
            
    except Exception as e:
        current_app.logger.error(f"Error in batch refresh: {str(e)}")
        return jsonify({"error": "Failed to refresh games"}), 500

@main.route('/api/wishlist/<int:game_id>/remove', methods=['DELETE'])
def remove_from_wishlist(game_id):
    """Remove a game from the wishlist."""
    try:
        with get_db() as db:
            cursor = db.cursor()
            
            # First get the game info for logging
            cursor.execute(
                """SELECT pg.name, pg.console 
                   FROM wanted_games wg 
                   JOIN physical_games pg ON wg.physical_game = pg.id 
                   WHERE wg.physical_game = ?""",
                (game_id,)
            )
            result = cursor.fetchone()
            
            if not result:
                current_app.logger.warning(f"Game {game_id} not found in wishlist")
                return jsonify({"error": "Game not found in wishlist"}), 404
            
            game_name, game_console = result
            
            # Remove from wishlist
            cursor.execute(
                "DELETE FROM wanted_games WHERE physical_game = ?",
                (game_id,)
            )
            
            if cursor.rowcount == 0:
                current_app.logger.warning(f"No wishlist entry found for game {game_id}")
                return jsonify({"error": "Game not found in wishlist"}), 404
            
            db.commit()
            current_app.logger.info(f"Successfully removed game {game_id} ({game_name} - {game_console}) from wishlist")
            
            return jsonify({
                "message": "Game removed from wishlist successfully",
                "game_id": game_id,
                "name": game_name,
                "console": game_console
            })
            
    except Exception as e:
        current_app.logger.error(f"Error removing game {game_id} from wishlist: {str(e)}")
        return jsonify({"error": "Failed to remove game from wishlist"}), 500


@main.route('/api/purchased_game/<int:purchased_game_id>/remove_from_collection', methods=['DELETE'])
def remove_from_collection(purchased_game_id):
    """Remove a specific purchased game from the collection entirely."""
    try:
        current_app.logger.info(f"Attempting to remove purchased_game_id {purchased_game_id} from collection")
        
        with get_db() as db:
            cursor = db.cursor()
            
            # First get the game info for the specific purchased game
            cursor.execute("""
                SELECT pg.name, pg.console, pur.id
                FROM purchased_games pur
                JOIN physical_games pg ON pur.physical_game = pg.id
                WHERE pur.id = ?
            """, (purchased_game_id,))
            
            result = cursor.fetchone()
            
            if not result:
                current_app.logger.warning(f"Purchased game {purchased_game_id} not found in collection or not owned")
                return jsonify({"error": "Game not found in collection or not owned"}), 404
            
            game_name, game_console, _ = result
            current_app.logger.info(f"Found owned game: {game_name} ({game_console}) with purchased_game_id {purchased_game_id}")
            
            # Remove from all related tables in proper order
            # 1. Remove from games_for_sale if present (uses purchased_game_id)
            cursor.execute(
                "DELETE FROM games_for_sale WHERE purchased_game_id = ?",
                (purchased_game_id,)
            )
            sale_removals = cursor.rowcount
            current_app.logger.info(f"Removed {sale_removals} entries from games_for_sale")
            
            # 2. Remove from lent_games if present (uses purchased_game)
            cursor.execute(
                "DELETE FROM lent_games WHERE purchased_game = ?",
                (purchased_game_id,)
            )
            lent_removals = cursor.rowcount
            current_app.logger.info(f"Removed {lent_removals} entries from lent_games")
            
            # 3. Remove from purchased_games (this removes the ownership)
            cursor.execute(
                "DELETE FROM purchased_games WHERE id = ?",
                (purchased_game_id,)
            )
            purchased_removals = cursor.rowcount
            
            if purchased_removals == 0:
                current_app.logger.error(f"Failed to remove entries from purchased_games for purchased_game_id {purchased_game_id}")
                return jsonify({"error": "Failed to remove game from collection"}), 500
            
            current_app.logger.info(f"Removed {purchased_removals} entries from purchased_games")
            
            # Note: We keep the physical_games entry as it might be referenced by wishlist or other users
            
            db.commit()
            current_app.logger.info(f"Successfully removed purchased_game_id {purchased_game_id} ({game_name} - {game_console}) from collection")
            
            return jsonify({
                "message": "Game removed from collection successfully",
                "purchased_game_id": purchased_game_id,
                "name": game_name,
                "console": game_console
            })
            
    except Exception as e:
        current_app.logger.error(f"Error removing purchased_game_id {purchased_game_id} from collection: {str(e)}")
        import traceback
        current_app.logger.error(f"Traceback: {traceback.format_exc()}")
        return jsonify({"error": f"Failed to remove game from collection: {str(e)}"}), 500


@main.route('/api/game/<int:game_id>/mark_for_sale', methods=['POST'])
def mark_game_for_sale(game_id):
    """Mark an owned game for sale."""
    try:
        data = request.get_json() or {}
        asking_price = data.get('asking_price')
        notes = data.get('notes', '').strip()
        
        # Convert asking_price to float if provided
        if asking_price:
            try:
                asking_price = float(asking_price)
            except (ValueError, TypeError):
                return jsonify({"error": "Invalid asking price format"}), 400
        
        with get_db() as db:
            cursor = db.cursor()
            
            # First, verify the game exists and is owned (has a purchase record)
            cursor.execute("""
                SELECT pg.name, pg.console, pur.id, pur.acquisition_date, pur.source, pur.price
                FROM physical_games pg
                JOIN purchased_games pur ON pg.id = pur.physical_game
                WHERE pg.id = ?
            """, (game_id,))
            
            game_info = cursor.fetchone()
            if not game_info:
                return jsonify({"error": "Game not found or not owned"}), 404
            
            name, console, purchased_game_id, orig_date, orig_source, orig_price = game_info
            
            # Check if already marked for sale
            cursor.execute(
                "SELECT id FROM games_for_sale WHERE purchased_game_id = ?",
                (purchased_game_id,)
            )
            if cursor.fetchone():
                return jsonify({"error": "Game is already marked for sale"}), 400
            
            # Insert into games_for_sale with copied purchase information
            cursor.execute("""
                INSERT INTO games_for_sale 
                (purchased_game_id, asking_price, notes, 
                 original_acquisition_date, original_source, original_purchase_price)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (purchased_game_id, asking_price, notes, orig_date, orig_source, orig_price))
            
            db.commit()
            current_app.logger.info(f"Successfully marked game {game_id} ({name} - {console}) for sale")
            
            return jsonify({
                "message": "Game marked for sale successfully",
                "game_id": game_id,
                "name": name,
                "console": console,
                "asking_price": asking_price,
                "notes": notes
            })
            
    except Exception as e:
        current_app.logger.error(f"Error marking game {game_id} for sale: {str(e)}")
        return jsonify({"error": "Failed to mark game for sale"}), 500


@main.route('/api/game/<int:game_id>/unmark_for_sale', methods=['DELETE'])
def unmark_game_for_sale(game_id):
    """Remove a game from the for sale list."""
    try:
        with get_db() as db:
            cursor = db.cursor()
            
            # First get the purchased_game_id and game info for logging
            cursor.execute("""
                SELECT pur.id, pg.name, pg.console 
                FROM physical_games pg
                JOIN purchased_games pur ON pg.id = pur.physical_game
                WHERE pg.id = ?
            """, (game_id,))
            
            result = cursor.fetchone()
            if not result:
                return jsonify({"error": "Game not found or not owned"}), 404
            
            purchased_game_id, game_name, game_console = result
            
            # Check if the game is actually marked for sale
            cursor.execute(
                "SELECT id FROM games_for_sale WHERE purchased_game_id = ?",
                (purchased_game_id,)
            )
            if not cursor.fetchone():
                return jsonify({"error": "Game not found in for sale list"}), 404
            
            # Remove from games_for_sale
            cursor.execute(
                "DELETE FROM games_for_sale WHERE purchased_game_id = ?",
                (purchased_game_id,)
            )
            
            if cursor.rowcount == 0:
                return jsonify({"error": "Game not found in for sale list"}), 404
            
            db.commit()
            current_app.logger.info(f"Successfully unmarked game {game_id} ({game_name} - {game_console}) for sale")
            
            return jsonify({
                "message": "Game removed from sale list successfully",
                "game_id": game_id,
                "name": game_name,
                "console": game_console
            })
            
    except Exception as e:
        current_app.logger.error(f"Error unmarking game {game_id} for sale: {str(e)}")
        return jsonify({"error": "Failed to remove game from sale list"}), 500


@main.route('/api/game/<int:game_id>/mark_as_lent', methods=['POST'])
def mark_game_as_lent(game_id):
    """Mark an owned game as lent out."""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "No data provided"}), 400
            
        lent_date = data.get('lent_date')
        lent_to = data.get('lent_to', '').strip()
        
        if not lent_date:
            return jsonify({"error": "Lent date is required"}), 400
            
        if not lent_to:
            return jsonify({"error": "Lent to field is required"}), 400
            
        with get_db() as db:
            cursor = db.cursor()
            
            # Check if game exists and is owned (not wanted)
            cursor.execute("""
                SELECT pg.id, pg.name, pg.console, p.id as purchased_id
                FROM physical_games pg
                JOIN purchased_games p ON pg.id = p.physical_game
                WHERE pg.id = ? AND p.acquisition_date IS NOT NULL
            """, (game_id,))
            
            game = cursor.fetchone()
            if not game:
                return jsonify({"error": "Game not found or not owned"}), 404
                
            game_id_db, game_name, game_console, purchased_id = game
            
            # Check if game is already lent out
            cursor.execute("""
                SELECT id FROM lent_games WHERE purchased_game = ?
            """, (purchased_id,))
            
            if cursor.fetchone():
                return jsonify({"error": "Game is already marked as lent out"}), 400
            
            # Add to lent_games table
            cursor.execute("""
                INSERT INTO lent_games (purchased_game, lent_date, lent_to) 
                VALUES (?, ?, ?)
            """, (purchased_id, lent_date, lent_to))
            
            db.commit()
            current_app.logger.info(f"Successfully marked game {game_id} ({game_name} - {game_console}) as lent out to {lent_to}")
            
            return jsonify({
                "message": "Game marked as lent out successfully",
                "game_id": game_id,
                "name": game_name,
                "console": game_console,
                "lent_date": lent_date,
                "lent_to": lent_to
            })
            
    except Exception as e:
        current_app.logger.error(f"Error marking game {game_id} as lent out: {str(e)}")
        return jsonify({"error": "Failed to mark game as lent out"}), 500


@main.route('/api/game/<int:game_id>/unmark_as_lent', methods=['DELETE'])
def unmark_game_as_lent(game_id):
    """Remove a game from the lent out list."""
    try:
        with get_db() as db:
            cursor = db.cursor()
            
            # Check if game exists and is lent out
            cursor.execute("""
                SELECT pg.id, pg.name, pg.console, l.lent_to, p.id as purchased_id
                FROM physical_games pg
                JOIN purchased_games p ON pg.id = p.physical_game
                JOIN lent_games l ON p.id = l.purchased_game
                WHERE pg.id = ?
            """, (game_id,))
            
            game = cursor.fetchone()
            if not game:
                return jsonify({"error": "Game not found or not lent out"}), 404
                
            game_id_db, game_name, game_console, lent_to, purchased_id = game
            
            # Remove from lent_games table
            cursor.execute("""
                DELETE FROM lent_games WHERE purchased_game = ?
            """, (purchased_id,))
            
            db.commit()
            current_app.logger.info(f"Successfully unmarked game {game_id} ({game_name} - {game_console}) as lent out (was lent to {lent_to})")
            
            return jsonify({
                "message": "Game unmarked as lent out successfully",
                "game_id": game_id,
                "name": game_name,
                "console": game_console
            })
            
    except Exception as e:
        current_app.logger.error(f"Error unmarking game {game_id} as lent out: {str(e)}")
        return jsonify({"error": "Failed to unmark game as lent out"}), 500


# ========================================
# Photo Management API Endpoints
# ========================================

@main.route('/api/game/<int:game_id>/photos/upload-url', methods=['POST'])
def get_upload_urls(game_id):
    """
    Generate pre-signed POST URLs for direct S3 upload
    
    Expected request body:
    {
        "files": [
            {
                "filename": "game_box.jpg",
                "content_type": "image/jpeg",
                "file_size": 1024576
            }
        ]
    }
    """
    try:
        from .photo_service import PhotoService
        from .s3_service import create_s3_service
        
        # Validate request data
        data = request.get_json()
        if not data or 'files' not in data:
            return jsonify({"error": "Missing 'files' array in request body"}), 400
        
        files = data['files']
        if not isinstance(files, list) or len(files) == 0:
            return jsonify({"error": "Files array must contain at least one file"}), 400
        
        if len(files) > current_app.config.get('MAX_PHOTOS_PER_GAME', 20):
            return jsonify({"error": f"Maximum {current_app.config.get('MAX_PHOTOS_PER_GAME', 20)} photos per game allowed"}), 400
        
        # Verify the game exists
        if not PhotoService.verify_game_exists(game_id):
            return jsonify({"error": f"Game with ID {game_id} not found"}), 404
        
        # Check current photo count
        current_count = PhotoService.get_photo_count(game_id)
        if current_count + len(files) > current_app.config.get('MAX_PHOTOS_PER_GAME', 20):
            remaining = current_app.config.get('MAX_PHOTOS_PER_GAME', 20) - current_count
            return jsonify({"error": f"Adding {len(files)} photos would exceed limit. Only {remaining} photos can be added."}), 400
        
        # Initialize S3 service
        try:
            s3_service = create_s3_service()
        except ValueError as e:
            current_app.logger.error(f"S3 configuration error: {e}")
            return jsonify({"error": "Photo upload service not configured"}), 503
        
        upload_urls = []
        max_file_size = current_app.config.get('MAX_PHOTO_SIZE', 5 * 1024 * 1024)
        allowed_types = current_app.config.get('ALLOWED_PHOTO_TYPES', ['image/jpeg', 'image/png', 'image/webp'])
        
        for file_info in files:
            # Validate file info
            if not isinstance(file_info, dict):
                return jsonify({"error": "Each file must be an object with filename, content_type, and file_size"}), 400
            
            filename = file_info.get('filename', '').strip()
            content_type = file_info.get('content_type', '').strip()
            file_size = file_info.get('file_size', 0)
            
            if not filename:
                return jsonify({"error": "Filename is required for each file"}), 400
            
            if not content_type:
                return jsonify({"error": f"Content type is required for file: {filename}"}), 400
                
            if content_type not in allowed_types:
                return jsonify({"error": f"Unsupported file type: {content_type}. Allowed types: {', '.join(allowed_types)}"}), 400
            
            if file_size <= 0 or file_size > max_file_size:
                max_mb = max_file_size / (1024 * 1024)
                return jsonify({"error": f"File size must be between 1 byte and {max_mb:.1f} MB for file: {filename}"}), 400
            
            # Generate S3 key and pre-signed POST
            s3_key = PhotoService.generate_s3_key(game_id, filename)
            
            try:
                presigned_post = s3_service.generate_presigned_post(s3_key, content_type, max_file_size)
                
                upload_urls.append({
                    "filename": filename,
                    "s3_key": s3_key,
                    "upload_url": presigned_post['url'],
                    "fields": presigned_post['fields'],
                    "file_size": file_size,
                    "content_type": content_type
                })
                
            except Exception as e:
                current_app.logger.error(f"Error generating pre-signed POST for {filename}: {e}")
                return jsonify({"error": f"Failed to generate upload URL for {filename}"}), 500
        
        current_app.logger.info(f"Generated {len(upload_urls)} pre-signed upload URLs for game {game_id}")
        
        return jsonify({
            "upload_urls": upload_urls,
            "expires_in_minutes": current_app.config.get('PHOTO_UPLOAD_EXPIRY_MINUTES', 15),
            "max_file_size_mb": max_file_size / (1024 * 1024),
            "allowed_types": allowed_types
        })
        
    except Exception as e:
        current_app.logger.error(f"Error generating upload URLs for game {game_id}: {e}")
        return jsonify({"error": "Failed to generate upload URLs"}), 500


@main.route('/api/game/<int:game_id>/photos', methods=['POST'])
def register_uploaded_photos(game_id):
    """
    Register successfully uploaded photos in the database
    
    Expected request body:
    {
        "uploads": [
            {
                "s3_key": "photos/123/timestamp_uuid_filename.jpg",
                "original_filename": "filename.jpg",
                "file_size": 1024576,
                "content_type": "image/jpeg"
            }
        ]
    }
    """
    try:
        from .photo_service import PhotoService
        from .s3_service import create_s3_service
        
        # Validate request data
        data = request.get_json()
        if not data or 'uploads' not in data:
            return jsonify({"error": "Missing 'uploads' array in request body"}), 400
        
        uploads = data['uploads']
        if not isinstance(uploads, list) or len(uploads) == 0:
            return jsonify({"error": "Uploads array must contain at least one upload"}), 400
        
        # Verify the game exists
        if not PhotoService.verify_game_exists(game_id):
            return jsonify({"error": f"Game with ID {game_id} not found"}), 404
        
        # Initialize S3 service
        try:
            s3_service = create_s3_service()
        except ValueError as e:
            current_app.logger.error(f"S3 configuration error: {e}")
            return jsonify({"error": "Photo service not configured"}), 503
        
        registered_photos = []
        failed_uploads = []
        
        for upload_info in uploads:
            try:
                # Validate upload info
                if not isinstance(upload_info, dict):
                    failed_uploads.append({
                        "error": "Upload info must be an object",
                        "upload_info": upload_info
                    })
                    continue
                
                s3_key = upload_info.get('s3_key', '').strip()
                original_filename = upload_info.get('original_filename', '').strip()
                file_size = upload_info.get('file_size', 0)
                content_type = upload_info.get('content_type', '').strip()
                
                if not all([s3_key, original_filename, content_type]) or file_size <= 0:
                    failed_uploads.append({
                        "error": "Missing required fields: s3_key, original_filename, content_type, file_size",
                        "s3_key": s3_key,
                        "filename": original_filename
                    })
                    continue
                
                # Verify S3 object exists
                s3_metadata = s3_service.verify_object_exists(s3_key)
                if not s3_metadata:
                    failed_uploads.append({
                        "error": "File not found in S3",
                        "s3_key": s3_key,
                        "filename": original_filename
                    })
                    continue
                
                # Use S3 metadata for authoritative file info
                actual_file_size = s3_metadata['file_size']
                actual_content_type = s3_metadata['content_type']
                
                # Create photo record
                photo_id = PhotoService.create_photo_record(
                    s3_bucket=current_app.config['S3_PHOTOS_BUCKET'],
                    s3_key=s3_key,
                    original_filename=original_filename,
                    file_size=actual_file_size,
                    mime_type=actual_content_type
                )
                
                # Associate with game
                association_success = PhotoService.associate_photo_with_game(game_id, photo_id)
                if not association_success:
                    current_app.logger.warning(f"Photo {photo_id} already associated with game {game_id}")
                
                registered_photos.append({
                    "photo_id": photo_id,
                    "s3_key": s3_key,
                    "original_filename": original_filename,
                    "file_size": actual_file_size,
                    "content_type": actual_content_type,
                    "upload_timestamp": s3_metadata.get('last_modified')
                })
                
            except Exception as e:
                current_app.logger.error(f"Error registering upload {s3_key}: {e}")
                failed_uploads.append({
                    "error": f"Database error: {str(e)}",
                    "s3_key": s3_key,
                    "filename": original_filename
                })
        
        # Get updated photo count
        total_photos = PhotoService.get_photo_count(game_id)
        
        current_app.logger.info(f"Registered {len(registered_photos)} photos for game {game_id}")
        
        response_data = {
            "registered_photos": registered_photos,
            "total_photos": total_photos,
            "success_count": len(registered_photos),
            "failure_count": len(failed_uploads)
        }
        
        if failed_uploads:
            response_data["failed_uploads"] = failed_uploads
            current_app.logger.warning(f"Failed to register {len(failed_uploads)} uploads for game {game_id}")
        
        status_code = 200 if len(registered_photos) > 0 else 400
        return jsonify(response_data), status_code
        
    except Exception as e:
        current_app.logger.error(f"Error registering photos for game {game_id}: {e}")
        return jsonify({"error": "Failed to register uploaded photos"}), 500


@main.route('/api/game/<int:game_id>/photos', methods=['GET'])
def get_game_photos(game_id):
    """
    Get all photos associated with a game
    
    Query parameters:
    - active_only: true/false (default: true)
    - include_signed_urls: true/false (default: true)
    - url_expiry: seconds (default: 3600)
    """
    try:
        from .photo_service import PhotoService
        from .s3_service import create_s3_service
        
        # Verify the game exists
        if not PhotoService.verify_game_exists(game_id):
            return jsonify({"error": f"Game with ID {game_id} not found"}), 404
        
        # Parse query parameters
        active_only = request.args.get('active_only', 'true').lower() == 'true'
        include_signed_urls = request.args.get('include_signed_urls', 'true').lower() == 'true'
        url_expiry = int(request.args.get('url_expiry', 3600))
        
        # Get photos from database
        photos = PhotoService.get_game_photos(game_id, active_only=active_only)
        
        # Generate signed URLs if requested
        s3_service = None
        if include_signed_urls and photos:
            try:
                s3_service = create_s3_service()
            except ValueError as e:
                current_app.logger.warning(f"S3 not configured for signed URLs: {e}")
        
        photo_list = []
        for photo in photos:
            photo_data = {
                "id": photo['id'],
                "original_filename": photo['original_filename'],
                "file_size": photo['file_size'],
                "mime_type": photo['mime_type'],
                "upload_timestamp": photo['upload_timestamp'],
                "photo_order": photo['photo_order']
            }
            
            # Add signed URL if requested and S3 is configured
            if include_signed_urls and s3_service:
                try:
                    signed_url = s3_service.generate_signed_url(photo['s3_key'], url_expiry)
                    photo_data['signed_url'] = signed_url
                    photo_data['url_expires_in'] = url_expiry
                except Exception as e:
                    current_app.logger.error(f"Error generating signed URL for photo {photo['id']}: {e}")
            
            photo_list.append(photo_data)
        
        return jsonify({
            "photos": photo_list,
            "total_count": len(photo_list),
            "game_id": game_id
        })
        
    except Exception as e:
        current_app.logger.error(f"Error retrieving photos for game {game_id}: {e}")
        return jsonify({"error": "Failed to retrieve photos"}), 500


@main.route('/api/game/<int:game_id>/photos/<int:photo_id>', methods=['DELETE'])
def delete_game_photo(game_id, photo_id):
    """
    Delete a photo associated with a game (soft delete)
    """
    try:
        from .photo_service import PhotoService
        
        # Verify the game exists
        if not PhotoService.verify_game_exists(game_id):
            return jsonify({"error": f"Game with ID {game_id} not found"}), 404
        
        # Get photo info before deletion
        photo = PhotoService.get_photo_by_id(photo_id)
        if not photo:
            return jsonify({"error": f"Photo with ID {photo_id} not found"}), 404
        
        # Verify photo is associated with this game
        game_photos = PhotoService.get_game_photos(game_id, active_only=False)
        photo_ids = [p['id'] for p in game_photos]
        
        if photo_id not in photo_ids:
            return jsonify({"error": f"Photo {photo_id} is not associated with game {game_id}"}), 400
        
        # Perform soft delete
        success = PhotoService.soft_delete_photo(photo_id)
        if not success:
            return jsonify({"error": "Photo may already be deleted"}), 400
        
        # Get updated photo count
        total_photos = PhotoService.get_photo_count(game_id)
        
        current_app.logger.info(f"Soft deleted photo {photo_id} ({photo['original_filename']}) for game {game_id}")
        
        return jsonify({
            "message": "Photo deleted successfully",
            "photo_id": photo_id,
            "filename": photo['original_filename'],
            "total_photos": total_photos
        })
        
    except Exception as e:
        current_app.logger.error(f"Error deleting photo {photo_id} for game {game_id}: {e}")
        return jsonify({"error": "Failed to delete photo"}), 500


@main.route('/api/photos/s3-config', methods=['GET'])
def get_s3_configuration():
    """
    Get S3 configuration status for troubleshooting
    """
    try:
        from .s3_service import create_s3_service
        
        try:
            s3_service = create_s3_service()
            validation = s3_service.validate_configuration()
            
            return jsonify({
                "s3_configured": validation['is_valid'],
                "bucket_name": current_app.config.get('S3_PHOTOS_BUCKET', 'Not configured'),
                "region": current_app.config.get('S3_REGION', 'Not configured'),
                "max_file_size_mb": current_app.config.get('MAX_PHOTO_SIZE', 0) / (1024 * 1024),
                "max_photos_per_game": current_app.config.get('MAX_PHOTOS_PER_GAME', 0),
                "allowed_types": current_app.config.get('ALLOWED_PHOTO_TYPES', []),
                "upload_expiry_minutes": current_app.config.get('PHOTO_UPLOAD_EXPIRY_MINUTES', 0),
                "validation": validation
            })
            
        except ValueError as e:
            return jsonify({
                "s3_configured": False,
                "error": str(e),
                "bucket_name": current_app.config.get('S3_PHOTOS_BUCKET', 'Not configured'),
                "region": current_app.config.get('S3_REGION', 'Not configured')
            })
        
    except Exception as e:
        current_app.logger.error(f"Error checking S3 configuration: {e}")
        return jsonify({"error": "Failed to check configuration"}), 500


@main.route('/api/photos/<int:photo_id>/view', methods=['GET'])
def view_photo(photo_id):
    """
    Proxy endpoint to serve photo content from S3, avoiding CORS issues
    """
    try:
        from app.photo_service import PhotoService
        from app.s3_service import create_s3_service
        import requests
        
        # Get photo record
        photo = PhotoService.get_photo_by_id(photo_id)
        if not photo or not photo['is_active']:
            return jsonify({"error": "Photo not found"}), 404
        
        # Initialize S3 service and verify object exists first
        s3_service = create_s3_service()
        
        # Try to verify the object exists before generating signed URL
        object_metadata = s3_service.verify_object_exists(photo['s3_key'])
        if not object_metadata:
            current_app.logger.error(f"S3 object not found for key: {photo['s3_key']}")
            return jsonify({"error": "Photo not found in storage"}), 404
        
        signed_url = s3_service.generate_signed_url(photo['s3_key'])
        
        # Fetch the image from S3
        try:
            response = requests.get(signed_url, timeout=10)
            if response.status_code != 200:
                current_app.logger.error(f"Failed to fetch photo from S3: {response.status_code}")
                return jsonify({"error": "Failed to load photo"}), 503
        except requests.exceptions.Timeout:
            current_app.logger.error(f"Timeout fetching photo from S3")
            return jsonify({"error": "Timeout loading photo"}), 504
        except requests.exceptions.RequestException as e:
            current_app.logger.error(f"Request error fetching photo: {e}")
            return jsonify({"error": "Request error"}), 503
        
        # Return the image with proper content type
        from flask import Response
        import re
        
        # Sanitize filename for HTTP headers (remove or replace problematic characters)
        safe_filename = re.sub(r'[^\x00-\x7F]', '_', photo['original_filename'])  # Replace non-ASCII with underscore
        
        return Response(
            response.content,
            content_type=photo['mime_type'],
            headers={
                'Content-Length': str(len(response.content)),
                'Cache-Control': 'public, max-age=3600',  # Cache for 1 hour
                'Content-Disposition': f'inline; filename="{safe_filename}"'
            }
        )
        
    except Exception as e:
        current_app.logger.error(f"Error serving photo {photo_id}: {e}")
        return jsonify({"error": "Failed to serve photo"}), 500


@main.route('/api/barcode/search', methods=['POST'])
def search_by_barcode():
    """Search for games using a UPC/EAN barcode by scraping PriceCharting."""
    try:
        data = request.get_json()
        barcode = data.get('barcode', '').strip()
        
        if not barcode:
            return jsonify({"error": "Barcode is required"}), 400
            
        # Validate barcode format
        cleaned_barcode = ''.join(filter(str.isdigit, barcode))
        valid_lengths = [8, 12, 13]  # UPC-E, UPC-A, EAN-13
        
        if len(cleaned_barcode) not in valid_lengths:
            return jsonify({"error": "Invalid barcode format. Must be 8, 12, or 13 digits."}), 400
        
        current_app.logger.info(f"Searching for barcode: {barcode}")
        
        # Search PriceCharting using their JSON API endpoint
        import requests
        import time
        
        search_url = "https://www.pricecharting.com/search-products"
        search_params = {
            'q': cleaned_barcode,
            'type': 'prices'
        }
        
        # Add realistic headers to avoid getting blocked
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'en-US,en;q=0.5',
            'Referer': 'https://www.pricecharting.com/',
            'Connection': 'keep-alive',
        }
        
        try:
            response = requests.get(search_url, params=search_params, headers=headers, timeout=10)
            response.raise_for_status()
            
            # Parse JSON response
            data = response.json()
            games = []
            
            # Extract products from the JSON response
            products = data.get('products', [])
            
            seen_games = set()
            for product in products:
                if product.get('category') != 'video-games':
                    continue
                    
                product_name = product.get('productName', '').strip()
                console_name = product.get('consoleName', '').strip()
                product_id = product.get('id', '')
                
                if not product_name or not console_name or not product_id:
                    continue
                
                # Create a unique key to avoid duplicates
                game_key = f"{product_name}|{console_name}"
                if game_key in seen_games:
                    continue
                seen_games.add(game_key)
                
                # Construct PriceCharting URL from the product data
                # Format: https://www.pricecharting.com/game/console/game-name
                from app.pricecharting_service import PricechartingService
                clean_console = PricechartingService.clean_system_name(console_name)
                clean_name = PricechartingService.clean_game_name(product_name)
                
                game_url = f"https://www.pricecharting.com/game/{clean_console}/{clean_name}"
                
                games.append({
                    'name': product_name,
                    'console': console_name,
                    'url': game_url,
                    'price': product.get('price1', 0)
                })
                
                # Limit results to prevent overwhelming the UI
                if len(games) >= 10:
                    break
            
            current_app.logger.info(f"Found {len(games)} games for barcode {barcode}")
            
            return jsonify({
                "success": True,
                "barcode": barcode,
                "games": games,
                "total": len(games)
            })
            
        except requests.exceptions.Timeout:
            current_app.logger.error(f"Timeout searching PriceCharting for barcode: {barcode}")
            return jsonify({"error": "Search timeout. Please try again."}), 504
            
        except requests.exceptions.RequestException as e:
            current_app.logger.error(f"Error searching PriceCharting for barcode {barcode}: {e}")
            return jsonify({"error": "Search service unavailable. Please try again later."}), 503
            
    except Exception as e:
        current_app.logger.error(f"Error in barcode search: {e}")
        return jsonify({"error": "An error occurred while searching"}), 500
