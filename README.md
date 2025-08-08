# Collecting Tools Web Application

A web interface for managing and tracking video game collections, designed for self-hosted deployment on Ubuntu servers with automated S3 backup functionality.

## Features

### ✨ **Phase 2 Complete - Full Optimistic UI Experience**
- **Zero page refreshes**: All major operations provide immediate visual feedback
- **Optimistic updates**: Add, edit, remove, purchase conversion, and lent status changes happen instantly
- **Smart rollback**: Automatic error handling restores UI state if API calls fail
- **Real-time state management**: Client-side state keeps UI perfectly in sync

### Core Functionality
- **Game collection management**: Add, edit, remove games from your collection
- **Wishlist functionality**: Track games you want to purchase with price monitoring
- **Purchase conversion**: Seamlessly convert wishlist items to owned games
- **Lent status tracking**: Keep track of games you've lent out to friends
- **Price tracking and updates**: Automatic price monitoring from PriceCharting.com
- **Comprehensive testing**: 40+ test cases ensure reliability
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

### Technology Stack
- **Backend**: Flask 3.0.0 web framework with service layer architecture
- **Frontend**: Vanilla JavaScript with optimistic UI system
  - State management (`static/js/state-manager.js`)
  - Optimistic updater framework (`static/js/optimistic-updater.js`)
  - Error handling system (`static/js/error-handler.js`)
  - All operations implemented in `static/js/main.js`
- **Database**: SQLite with direct queries (no ORM)
- **Templates**: Jinja2 with progressive enhancement
- **Testing**: pytest (backend) + custom test runner (frontend)
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
│   ├── test_optimistic_ui.py   # Backend tests (22 test cases)
│   └── test_optimistic_ui.html # Frontend tests (25+ test cases)
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
