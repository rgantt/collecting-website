# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

**Last Updated**: August 2025  
**Current Version**: Complete Photo Upload System + API-First System with Enhanced Mobile UI - Production Ready ✅  
**Default Dev Port**: 8082
**Recent Updates**: Photo upload/viewing feature, S3 integration, complementary details expansion, enhanced mobile support

## Common Development Commands

### Running the Application
```bash
# Development server (preferred) - runs on port 8082 by default
python3 wsgi.py

# Override port with environment variable
FLASK_RUN_PORT=8081 python3 wsgi.py

# Production server with Gunicorn
gunicorn --workers 4 --bind 0.0.0.0:8080 wsgi:app
```

### Virtual Environment Setup
```bash
# Create and activate virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### Testing Commands
```bash
# Run all backend tests with coverage
python run_tests.py

# Run specific test file
python3 -m pytest tests/test_optimistic_ui.py -v

# Run single test
python3 -m pytest tests/test_optimistic_ui.py::TestAddGameOptimistic::test_add_to_wishlist_success -v

# Generate coverage report
python3 -m pytest tests/ --cov=app --cov-report=html
```

### Database Operations
```bash
# Manual database backup to S3
sudo -u www-data python3 /var/www/collecting-website/backup_to_s3.py

# Fix database schema issues
python3 fix_games_for_sale_schema.py

# Apply photo feature migration
sqlite3 games.db < add_photo_tables.sql
```

### Environment Variables
Required for photo upload functionality:
```bash
S3_PHOTOS_BUCKET=your-photos-bucket-name
S3_REGION=us-west-2
AWS_ACCESS_KEY_ID=your-access-key
AWS_SECRET_ACCESS_KEY=your-secret-key
```

### Deployment
```bash
# Local Ubuntu deployment
sudo ./deploy-local-simple.sh

# GitHub Actions deployment
./deploy-github-actions.sh
```

## Architecture Overview

### Application Structure
This is a Flask-based web application for managing video game collections with the following key components:

1. **Core Application** (`app/`)
   - Flask application factory pattern in `__init__.py`
   - Single blueprint for routes in `routes.py`
   - Service layer pattern for business logic

2. **Service Layer**
   - `collection_service.py`: Manages game collection operations
   - `wishlist_service.py`: Handles wishlist functionality
   - `pricecharting_service.py`: Integrates with PriceCharting.com API for price data
   - `price_retrieval.py`: Handles price updates and history tracking
   - `photo_service.py`: Game photo CRUD operations and S3 key management
   - `s3_service.py`: AWS S3 integration for photo storage and pre-signed URLs

3. **Database Architecture**
   - SQLite database (`games.db`) with normalized schema:
     - `physical_games`: Core game entities (name, console)
     - `purchased_games`: Collection items linked to physical_games
     - `wanted_games`: Wishlist items linked to physical_games  
     - `pricecharting_games`: Price tracking cache
     - `physical_games_pricecharting_games`: Junction table linking games to price data
     - `lent_games`: Tracking games lent out
     - `games_for_sale`: Items marked for sale
     - `game_photos`: Photo metadata with S3 references
     - `physical_game_photos`: Junction table linking photos to games
   - **No ORM**: Direct SQLite queries with context managers for automatic cleanup
   - **Configurable database path**: Tests use temporary databases, production uses `games.db`

4. **Frontend Architecture** (✅ **API-First System with Enhanced Mobile UI**)
   - Server-side rendering with Jinja2 templates + progressive enhancement
   - **API-First Pattern**: Server confirmation before UI updates (eliminates hanging modals)
     - `static/js/state-manager.js`: Client-side game state management
     - `static/js/error-handler.js`: Centralized error handling with toast notifications  
     - `static/js/main.js`: All API-first operation implementations
   - **Zero page refreshes** for all operations (add, edit, remove, purchase, lent status, price updates)
   - **Immediate UI feedback** after successful server responses
   - **Enhanced Mobile Support**:
     - Complementary details expansion (eliminates redundancy between table and expanded view)
     - Compact summary layout with efficient horizontal information flow
     - Expandable metadata section for complete game information access
     - Mobile-friendly Quick Actions section with consistent button styling
   - **Advanced Search Features**:
     - Persistent filters across page reloads (search terms, status, console, condition)
     - URL parameter encoding for bookmarkable/shareable searches (`/?search=mario&status=wanted`)
     - Real-time filtering with debounced search input
   - **Immediate Price Updates**: Price refresh updates all UI elements without page reload (table, summary, metadata)

5. **API Design**
   - RESTful endpoints under `/api/`
   - JSON responses with consistent error handling
   - Supports pagination, sorting, and filtering via query parameters

### Key Technical Decisions

1. **No ORM**: Direct SQLite queries for simplicity and performance
2. **Service Layer**: Business logic separated from routes
3. **API-First UI**: Server confirmation before UI updates for reliability
4. **Self-hosted focus**: Designed for Ubuntu deployment with systemd
5. **S3 Integration**: Photo storage with direct client uploads and automated database backups every 6 hours

### Deployment Architecture

1. **Production Stack**:
   - Gunicorn WSGI server
   - systemd service management
   - www-data user for web server
   - Automated S3 backups via cron

2. **GitHub Actions**: Self-hosted runner for CI/CD

### Database Schema Key Relationships

- **Core Entity**: `physical_games` is the central table (name, console)
- **Relationships**: All other tables link to `physical_games` via foreign keys
- **Junction Pattern**: `physical_games_pricecharting_games` links games to price data
- **Legacy Support**: `wishlist` table exists alongside `wanted_games` for backward compatibility
- **Conditions**: "new", "loose", "complete", "box_only", "manual_only"
- **Sorting**: Supports multiple fields: name, console, acquisition_date, price, etc.

### Error Handling Patterns

- Database connections use context managers for automatic cleanup
- API endpoints return consistent JSON error responses
- Frontend has centralized error handling in `error-handler.js`
- Logging configured at INFO level with structured format

### Security Considerations

- Environment variables for sensitive configuration
- CSRF protection via Flask's built-in mechanisms
- Input validation on all user-submitted data
- No direct SQL string concatenation (parameterized queries)

### API-First System Details

**Key JavaScript Operations** (all use API-first pattern):
1. **Add Games**: `addToWishlistOptimistic()`, `addToCollectionOptimistic()`
2. **Remove Games**: `removeFromWishlistOptimistic()`, `removeFromCollectionOptimistic()`
3. **Purchase Conversion**: `purchaseWishlistGameOptimistic()`
4. **Lent Status**: `markGameAsLentOptimistic()`, `unmarkGameAsLentOptimistic()`
5. **Edit Details**: `editGameDetailsOptimistic()` - Now includes condition editing
6. **Price Updates**: `updateGamePrice()` - Updates all UI elements immediately (table, summary, metadata)
7. **Photo Management**: `uploadPhotos()`, `deletePhoto()`, `openPhotoViewer()` - Full S3 integration
8. **Search/Filtering**: `applyFilters()`, `updateUrlParameters()` - Persistent and shareable
9. **UI Interactions**: Metadata toggle buttons, complementary expansion system

Note: Function names contain "Optimistic" for historical reasons, but they now implement API-first pattern.

**Enhanced UI Components**:
- **Complementary Details Expansion**: Shows only non-redundant information from table row
- **Compact Summary Layout**: Horizontal flow with purchase → current price display
- **Expandable Metadata Tables**: Complete game information accessible on mobile
- **Unified Quick Actions**: All game actions consolidated with consistent outline button styling
- **Real-time Price Synchronization**: Updates summary, metadata, and table simultaneously

**API-First Pattern** (eliminates hanging modals and data inconsistency):
```javascript
// 1. Make API call first
const response = await fetch('/api/endpoint', { method: 'POST', ... });
const data = await response.json();

if (!response.ok) {
    throw new Error(data.error || 'Operation failed');
}

// 2. Update UI only after server success
updateDOM(data);
updateStateManager(data);
showSuccessMessage();
closeModal();
```

**State Management**:
- `GameStateManager`: Centralized client-side state for all games
- Updates only after server confirmation
- No rollback complexity or pending operation tracking needed

### Testing Strategy

**Backend Tests**:
- **Framework**: pytest with Flask test client and coverage reporting
- **Schema Management**: Tests use `test_schema.sql` (extracted from production database) for consistency
- **Database Isolation**: Each test uses temporary database with production schema
- **Test Categories**: 
  - API endpoints (add, edit, remove, purchase, lent status operations)
  - Error handling and validation
  - Concurrent operations and race conditions
- **Coverage**: 32 test cases with 54% code coverage focusing on critical API paths
- **Run Command**: `python run_tests.py` (backend tests only, requires virtual environment)

**Key Testing Pattern**:
```python
@pytest.fixture
def app():
    """Create isolated test environment"""
    db_fd, db_path = tempfile.mkstemp(suffix='.db')
    app = create_app()
    app.config['TESTING'] = True
    app.config['DATABASE_PATH'] = db_path  # Override for tests
    
    # Load production schema from SQL file
    with app.app_context():
        init_test_db()  # Executes test_schema.sql
    
    yield app
    # Cleanup temporary database
```

**Test Database Architecture**:
- **Single Source of Truth**: `test_schema.sql` contains exact production schema
- **No Schema Drift**: Tests automatically use current production database structure
- **Temporary Isolation**: Each test gets clean database, no interference between tests
- **Configurable Paths**: App supports different database paths via `DATABASE_PATH` config

**Frontend Testing**:
- Currently no automated frontend tests (HTML-based tests were removed)
- Future consideration: Implement automated UI testing with tools like Playwright or Cypress
- Manual testing: Use browser developer tools to verify API-first operations

## Key Implementation Details

**Database Configuration Architecture**:
- `config.py`: Defines `DATABASE_PATH` setting with environment variable support
- `app/routes.py`: Uses `get_db_path()` function to retrieve configurable database path
- **Production**: Uses `games.db` in application root directory
- **Tests**: Override with temporary database paths for isolation
- **CI/CD**: Works without requiring actual `games.db` file (uses schema SQL)

**Critical Database Pattern**:
```python
# In app/routes.py
def get_db_path():
    """Get database path from app config or fallback to default"""
    if current_app:
        return current_app.config.get('DATABASE_PATH', 
                                     Path(__file__).parent.parent / "games.db")
    return Path(__file__).parent.parent / "games.db"

@contextmanager
def get_db():
    conn = sqlite3.connect(get_db_path())  # Uses configurable path
    try:
        yield conn
    finally:
        conn.close()
```

**API-First Operation Pattern**:
All game operations follow this reliable pattern:
```javascript
// 1. Make API call first (no optimistic updates)
const response = await fetch('/api/endpoint', { method: 'POST', ... });
const data = await response.json();

if (!response.ok) {
    throw new Error(data.error || 'Operation failed');
}

// 2. Update UI only after server success
updateDOM(data);
updateStateManager(data);
showSuccessMessage();
closeModal();  // Prevents hanging modals
```

**Current Production Status**:
- ✅ **Reliable Operations**: No hanging modals, no data inconsistency
- ✅ **Zero Page Refreshes**: All operations work without browser refreshes  
- ✅ **Clean Codebase**: Optimistic UI complexity removed
- ✅ **Robust Testing**: 32 automated tests with production schema consistency
- ✅ **CI/CD Ready**: Tests pass in GitHub Actions without requiring database files
- ✅ **Advanced Search**: Persistent filters, URL parameters, immediate filtering
- ✅ **Real-time Price Updates**: Immediate UI updates without page reloads
- ✅ **Enhanced Mobile UI**: Complementary expansion, compact layouts, expandable metadata
- ✅ **Complete Data Access**: All game information available on mobile through metadata tables
- ✅ **Photo Upload System**: Direct S3 uploads, gallery view, modal viewer, proxy serving to avoid CORS

**CI/CD Integration**:
- GitHub Actions runs backend tests before deployment
- Tests must pass before merging changes  
- Coverage reports generated automatically with htmlcov output

## Important Files and Locations

**Core Application**:
- `wsgi.py` - WSGI entry point, preferred for development server
- `app/routes.py` - Main Flask routes and API endpoints (500+ lines)
- `app/routes.py:get_db_path()` - Critical function for database path resolution
- `config.py` - Application configuration including DATABASE_PATH

**Database**:
- `games.db` - Production database (not in version control, auto-downloaded from S3)
- `test_schema.sql` - Production schema export for tests (single source of truth)
- Service layer: `*_service.py` files handle business logic
- `add_photo_tables.sql` - Photo feature database migration

**Frontend**:
- `app/templates/index.html` - Main UI template with complementary expansion system and mobile-optimized layouts
- `app/static/js/main.js` - All API-first operations (8+ major functions including enhanced price updates)
- `app/static/js/state-manager.js` - Client-side state management
- `app/static/js/error-handler.js` - Toast notifications and error handling
- **Key Functions**: `window.formatCurrency()`, `window.formatValueChange()` - Global formatting utilities
- **UI Features**: Metadata toggle handlers, complementary details expansion, unified Quick Actions

**Testing**:
- `run_tests.py` - Main test runner script (backend tests only)
- `tests/test_*.py` - Backend tests (32 test cases, 54% coverage)
- `test_schema.sql` - Production database schema for test isolation

**Development Workflow**:
1. Activate virtual environment: `source venv/bin/activate`
2. Run tests: `python run_tests.py`
3. Start development server: `python3 wsgi.py` (port 8082)
4. Access application: http://localhost:8082