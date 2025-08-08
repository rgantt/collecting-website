# Collecting Tools Web Application

A web interface for managing and tracking video game collections, designed for self-hosted deployment on Ubuntu servers with automated S3 backup functionality.

## Features

### ✨ **100% Complete - Production Ready Optimistic UI System**
- **Zero page refreshes**: All major operations provide immediate visual feedback ✅ **ACHIEVED**
- **Optimistic updates**: Add, edit, remove, purchase conversion, and lent status changes happen instantly
- **Smart rollback**: Automatic error handling restores UI state if API calls fail
- **Professional loading states**: Visual feedback with animations and progress indicators
- **Background data sync**: Automatic accuracy validation without interrupting user experience
- **Conflict resolution**: Professional UI for handling server vs client data conflicts
- **Comprehensive testing**: 40+ test scenarios validate production readiness
- **Real-time state management**: Client-side state keeps UI perfectly in sync

### Core Functionality
- **Game collection management**: Add, edit, remove games from your collection
- **Wishlist functionality**: Track games you want to purchase with price monitoring
- **Purchase conversion**: Seamlessly convert wishlist items to owned games
- **Lent status tracking**: Keep track of games you've lent out to friends
- **Price tracking and updates**: Automatic price monitoring from PriceCharting.com
- **Comprehensive testing**: 50+ test cases covering optimistic UI, rollback scenarios, and performance
- **Responsive web interface**: Works perfectly on desktop and mobile
- **SQLite database persistence**: Reliable local data storage
- **Automated S3 database backups**: Never lose your data
- **Self-hosted deployment ready**: Full Ubuntu deployment automation

## Setup

1. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Set up environment variables:
```bash
cp .env.example .env
# Edit .env with your configuration
```

4. Run the development server:
```bash
python3 application.py
```

5. Run tests to verify everything works:
```bash
python run_tests.py  # Backend tests
# Open tests/test_optimistic_ui.html in browser for frontend tests
```

## Development

### Optimistic UI Architecture

This application implements a comprehensive optimistic UI system that eliminates page refreshes and provides immediate user feedback:

#### **Core Pattern: Optimistic Updates**
```
User Action → Immediate UI Update → Background API Call → Selective Refresh
```

**Key Components:**

1. **GameStateManager** - Client-side state management independent of DOM
2. **OptimisticUpdater** - Handles immediate UI updates with rollback capability  
3. **ErrorHandler** - Professional notifications and automatic error recovery
4. **LoadingStateManager** - Visual feedback with animations and progress indicators
5. **Conflict Resolution** - User choice when server data differs from client state

#### **Developer Patterns**

**Standard Optimistic Operation:**
```javascript
async function optimisticOperation(gameId, data) {
    const originalState = window.gameStateManager.getGame(gameId);
    
    try {
        // 1. Apply immediate UI changes
        updateGameCardUI(gameId, data);
        
        // 2. Update client state
        window.gameStateManager.updateGame(gameId, data);
        
        // 3. Background API call
        const response = await fetch(apiEndpoint, options);
        
        // 4. Show success and queue refresh
        window.errorHandler.showSuccessToast('Success!');
        queueGameRefresh(gameId);
        
    } catch (error) {
        // 5. Rollback on failure
        updateGameCardUI(gameId, originalState);
        window.gameStateManager.updateGame(gameId, originalState);
        window.errorHandler.showErrorToast(error.message);
    }
}
```

**Conflict Resolution:**
- Critical conflicts (name, console, purchase_price, lent status) trigger user choice modal
- Non-critical conflicts (current_price, condition) are auto-applied
- User can choose "Keep My Version" or "Use Server Version"

**Background Refresh System:**
- Selective refresh of individual games after operations
- Batch refresh with debouncing for multiple rapid operations
- Differential updates - only change what's different
- Automatic conflict detection and resolution

#### **Testing Strategy**

The system includes comprehensive test coverage:
- **Backend Tests**: 25+ test cases for all API endpoints and operations
- **Frontend Tests**: 20+ test scenarios for optimistic UI behavior
- **Loading State Tests**: Visual feedback and animation validation
- **Conflict Resolution Tests**: Interactive modal and user choice testing
- **Integration Tests**: Full optimistic operation cycles with rollback scenarios

### Technology Stack
- **Backend**: Flask 3.0.0 web framework with service layer architecture
- **Frontend**: Vanilla JavaScript with complete optimistic UI system
  - **State management** (`static/js/state-manager.js`) - Client-side game state tracking
  - **Optimistic updater** (`static/js/optimistic-updater.js`) - Immediate UI updates with rollback
  - **Error handling** (`static/js/error-handler.js`) - Professional toast notifications and recovery
  - **Loading states** (`static/js/main.js`) - Visual feedback and progress indicators
  - **Conflict resolution** (`static/js/main.js`) - User choice for server vs client data conflicts
  - **Comprehensive operations** (`static/js/main.js`) - All CRUD operations with optimistic patterns
- **Database**: SQLite with direct queries (no ORM)
- **Templates**: Jinja2 with progressive enhancement
- **Testing**: pytest (backend) + custom test runner (frontend) + conflict resolution tests
- **Deployment**: Gunicorn + systemd service
- **Backups**: Boto3 for AWS S3 integration

## Deployment

The application is designed for self-hosted Ubuntu deployment:

### Quick Deployment
1. Deploy using the provided script:
```bash
sudo ./deploy-local-simple.sh
```

### Manual Setup
1. Ensure you have Python 3.8+ and required system packages
2. Configure your environment variables
3. Install dependencies and set up the service

### GitHub Actions Deployment
For automated deployment, see `GITHUB_ACTIONS_SETUP.md`

## S3 Database Backup

The application includes automated S3 backup functionality:

### Features
- Automated backups every 6 hours via cron job
- Current backup stored as `games.db` in S3
- Historical backups stored with timestamps
- Comprehensive logging and error handling

### Setup
1. Configure AWS credentials:
```bash
sudo ./setup-aws-credentials.sh
```

2. Set up the backup system:
```bash
sudo ./setup-backup-cron.sh
```

### Manual Backup
```bash
sudo -u www-data python3 /var/www/collecting-website/backup_to_s3.py
```

For detailed backup configuration, see `BACKUP_SETUP.md`.

## Troubleshooting

### Optimistic UI Issues

**Problem: UI updates but server state is different**
- **Cause**: Conflict between optimistic update and server state
- **Solution**: System automatically detects conflicts during background refresh and shows resolution modal for critical conflicts
- **Debug**: Check browser console for conflict detection logs

**Problem: Operations appear to "hang" or don't complete**
- **Cause**: Network issues or server errors during background API calls
- **Solution**: System automatically rolls back optimistic changes on failure
- **Debug**: Check Network tab in browser dev tools for failed requests

**Problem: Game data becomes inconsistent**
- **Cause**: Background refresh failed or was interrupted
- **Solution**: Manually refresh the page or use "Update Price" button to force data sync
- **Prevention**: System queues background refreshes automatically after operations

**Problem: Loading states don't appear**
- **Cause**: LoadingStateManager not initialized properly
- **Solution**: Check browser console for JavaScript errors on page load
- **Debug**: Verify `window.LoadingStateManager` exists in console

**Problem: Toast notifications not showing**
- **Cause**: ErrorHandler not configured or Bootstrap JS not loaded
- **Solution**: Check that Bootstrap 5.x JavaScript is loaded and ErrorHandler is initialized
- **Debug**: Test with `window.errorHandler.showSuccessToast('test')` in console

### Performance Issues

**Problem: Slow UI updates with large collections (1000+ games)**
- **Solution**: System uses differential updates and DOM targeting to minimize reflows
- **Optimization**: Background refreshes are batched and debounced automatically
- **Monitor**: Check browser Performance tab for render bottlenecks

**Problem: Memory usage grows over time**
- **Cause**: Game state manager accumulating data
- **Solution**: Page refresh clears client state (system is designed for single-page sessions)
- **Prevention**: State manager only stores essential game data, not full DOM

### Data Synchronization

**Problem: Server has different data than UI shows**
- **Automatic**: Background refresh detects conflicts and shows resolution modal
- **Manual**: Use browser refresh or individual game "Update Price" buttons
- **Debug**: Check `window.gameStateManager.getAllGames()` vs server data

**Problem: Conflict resolution modal doesn't appear**
- **Cause**: Only critical conflicts trigger modal (name, console, purchase_price, lent status)
- **Behavior**: Non-critical conflicts are auto-applied silently
- **Debug**: Check console logs for conflict detection messages

For more detailed technical information, see `OPTIMISTIC_UI_IMPLEMENTATION_PLAN.md`.

## Project Structure

```
collecting-website/
├── .github/              # GitHub Actions workflows
├── app/                  # Application code
│   ├── __init__.py       # App initialization
│   ├── routes.py         # API routes and views (40+ endpoints)
│   ├── *_service.py      # Service layer (collection, wishlist, pricecharting)
│   ├── price_retrieval.py # Price update functionality
│   ├── templates/        # Jinja2 templates
│   │   └── index.html    # Main UI with optimistic updates
│   └── static/js/        # Optimistic UI system
│       ├── state-manager.js      # Client-side state management
│       ├── optimistic-updater.js # Optimistic update framework
│       ├── error-handler.js      # Error handling system
│       └── main.js              # All optimistic operations
├── tests/                # Comprehensive test suite
│   ├── test_optimistic_ui.py          # Backend tests (25+ test cases)
│   ├── test_optimistic_ui.html        # Frontend tests (25+ test cases)  
│   ├── test_loading_states.html       # Loading state tests (20+ test cases)
│   ├── test_optimistic_updates_comprehensive.html # Full integration tests (20+ scenarios)
│   ├── test_no_page_refreshes.html    # Page refresh detection tests
│   └── test_conflict_resolution.html   # Conflict resolution tests
├── backup_to_s3.py       # S3 backup script
├── CLAUDE.md            # Development guidance
├── OPTIMISTIC_UI_IMPLEMENTATION_PLAN.md # Phase 2 complete!
├── deploy-*.sh          # Deployment scripts
├── wsgi.py              # WSGI entry point
├── config.py            # Configuration settings
├── requirements.txt     # Python dependencies
└── Documentation files (*.md)
```

## Requirements

See `requirements.txt` for a complete list of dependencies. Key requirements:
- Python 3.x
- Flask 3.0.0
- Authlib 1.3.0
- Gunicorn 21.2.0

## Contributing

1. Create a feature branch
2. Make your changes
3. Run tests before committing
4. Submit a pull request

## License

Proprietary - All rights reserved
