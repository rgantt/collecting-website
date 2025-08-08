# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

**Last Updated**: August 2025  
**Current Version**: Phase 5 - Comprehensive Testing Complete

## Common Development Commands

### Running the Application
```bash
# Development server
python3 wsgi.py
# or
python3 application.py

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

### Database Operations
```bash
# Manual database backup to S3
sudo -u www-data python3 /var/www/collecting-website/backup_to_s3.py

# Fix database schema issues
python3 fix_games_for_sale_schema.py
```

### Deployment
```bash
# Local Ubuntu deployment
sudo ./deploy-local-simple.sh

# GitHub Actions deployment
./deploy-github-actions.sh

# Debug mode
./debug-app.sh
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

3. **Database**
   - SQLite database (`games.db`) with tables for:
     - `purchased_games`: Collection items
     - `wishlist`: Wishlist items
     - `price_history`: Historical price tracking
     - `games_for_sale`: Items marked for sale
   - No ORM - uses direct SQLite connections with context managers

4. **Frontend Architecture** (✅ **Fully Optimistic UI - Phase 2 Complete**)
   - Server-side rendering with Jinja2 templates with progressive enhancement
   - **Optimistic UI System**: Immediate user feedback with background API calls
     - `static/js/state-manager.js`: Client-side game state management
     - `static/js/optimistic-updater.js`: Optimistic update framework with rollback
     - `static/js/error-handler.js`: Centralized error handling and notifications
     - `static/js/main.js`: All optimistic operation implementations
   - **Zero page refreshes** for all major operations (add, edit, remove, purchase, lent status)
   - Service worker for offline support

5. **API Design**
   - RESTful endpoints under `/api/`
   - JSON responses with consistent error handling
   - Supports pagination, sorting, and filtering via query parameters

### Key Technical Decisions

1. **No ORM**: Direct SQLite queries for simplicity and performance
2. **Service Layer**: Business logic separated from routes
3. **Optimistic UI**: Client-side state management for responsive UX
4. **Self-hosted focus**: Designed for Ubuntu deployment with systemd
5. **S3 Backups**: Automated database backups every 6 hours

### Deployment Architecture

1. **Production Stack**:
   - Gunicorn WSGI server
   - systemd service management
   - www-data user for web server
   - Automated S3 backups via cron

2. **GitHub Actions**: Self-hosted runner for CI/CD

### Database Schema Key Relationships

- `purchased_games` and `wishlist` share similar structure with game metadata
- `price_history` tracks price changes over time for both collections
- Conditions: "new", "loose", "complete", "box_only", "manual_only"
- Sorting supports multiple fields: name, console, acquisition_date, price, etc.

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

### Optimistic UI System Details

**Key Operations with Optimistic Updates**:
1. **Add Games**: `addToWishlistOptimistic()`, `addToCollectionOptimistic()`
2. **Remove Games**: `removeFromWishlistOptimistic()`, `removeFromCollectionOptimistic()`
3. **Purchase Conversion**: `purchaseWishlistGameOptimistic()`
4. **Lent Status**: `markGameAsLentOptimistic()`, `unmarkGameAsLentOptimistic()`
5. **Edit Details**: `editGameDetailsOptimistic()`
6. **Sale Status**: `markGameForSaleOptimistic()`, `unmarkGameForSaleOptimistic()`

**Optimistic Update Pattern**:
```javascript
// 1. Immediate UI update
const uiUpdateFn = () => { /* Update DOM immediately */ };

// 2. Background API call
const apiFn = async () => { /* Make API request */ };

// 3. Rollback on failure
const rollbackFn = () => { /* Restore previous state */ };

// 4. Apply optimistic update
await optimisticUpdater.applyOptimisticUpdate(id, operation, uiUpdateFn, apiFn, {
    rollbackFn, onSuccess, onError
});
```

**State Management**:
- `GameStateManager`: Centralized client-side state for all games
- Maintains consistency between DOM, state manager, and server
- Supports pending operations tracking for conflict resolution

### Testing Strategy

**Backend Tests** (Location: `tests/test_optimistic_ui.py`):
- Framework: pytest with coverage reporting and Flask test client
- Test categories: 
  - API endpoints (add, edit, remove, purchase, lent status)
  - Error handling and validation
  - Rollback scenarios and concurrent operations
- Run with: `python run_tests.py` (requires virtual environment activation)
- Current coverage: 50%+ with focus on critical paths
- **22 test cases** covering all optimistic operations

**Frontend Tests** (Location: `tests/test_optimistic_ui.html`):
- Framework: Custom test runner with mock fetch capabilities
- Test categories:
  - State management unit tests (GameStateManager, OptimisticUpdater)  
  - Optimistic update integration tests with mocked APIs
  - UI manipulation verification
  - Rollback scenario testing
- Run by: Opening HTML file in browser and clicking "Run All Tests"
- **25+ test cases** with success/failure scenarios for all operations

**Integration Testing**:
- Tests cover complete optimistic update flow: UI → State → API → Database
- Rollback scenarios verify proper error handling and state restoration
- Concurrent operation tests ensure race condition handling
- DOM manipulation verification ensures UI consistency

**✅ Task 5.1: Comprehensive Optimistic Update Testing - COMPLETED**:
- **Test File**: `tests/test_optimistic_updates_comprehensive.html`
- **Coverage**: 20+ comprehensive test scenarios with mock server infrastructure
- **Status**: ✅ **PRODUCTION READY** - All critical scenarios validated
- **Features**: Configurable success rates, network delays, timeout simulation
- **Test Categories**:
  - Successful operations (4 tests)
  - Failure rollback scenarios (3 tests) 
  - Rapid successive operations (2 tests)
  - Network timeout scenarios (1 test)
  - Batch operation failures (2 tests)
  - Loading state integration (8+ tests)
- **Result**: Optimistic UI system (Phases 1-4) validated for production use

**CI/CD Integration**:
- GitHub Actions runs backend tests before deployment
- Tests must pass before merging changes  
- Coverage reports generated automatically with htmlcov output