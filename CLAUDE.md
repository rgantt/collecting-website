# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

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

4. **Frontend Architecture**
   - Server-side rendering with Jinja2 templates
   - Progressive enhancement with vanilla JavaScript
   - Optimistic UI updates in `static/js/optimistic-updater.js`
   - State management in `static/js/state-manager.js`
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

### Testing Strategy

**Backend Tests**:
- Location: `tests/test_optimistic_ui.py`
- Framework: pytest with coverage reporting
- Test categories: API endpoints, error handling, rollback scenarios, concurrent operations
- Run with: `python run_tests.py` or `pytest tests/`
- Coverage goal: 40%+ with focus on critical paths

**Frontend Tests**:
- Location: `tests/test_optimistic_ui.html` 
- Framework: Custom test runner with mock fetch
- Test categories: State management, optimistic updates, UI interactions, rollbacks
- Run by: Opening HTML file in browser
- Includes mocked API responses for isolated testing

**Integration Testing**:
- Tests cover full optimistic update flow (UI → API → Database)
- Rollback scenarios verify proper error handling
- Concurrent operation tests ensure race condition handling

**CI/CD Integration**:
- GitHub Actions runs backend tests before deployment
- Tests must pass before merging changes
- Coverage reports generated automatically