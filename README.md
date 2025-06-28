# Collecting Tools Web Application

A web interface for managing and tracking video game collections, designed for self-hosted deployment on Ubuntu servers with automated S3 backup functionality.

## Features

- Game collection management
- Price tracking and updates
- Wishlist functionality
- Responsive web interface
- SQLite database persistence
- **Automated S3 database backups**
- Self-hosted deployment ready

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

## Development

The application uses:
- Flask 3.0.0 for the web framework
- SQLite for database persistence
- Jinja2 for templating
- Boto3 for AWS S3 integration
- Gunicorn for production deployment

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
│   ├── routes.py         # URL routes and views
│   ├── price_retrieval.py # Price update functionality
│   ├── templates/        # Jinja2 templates
│   └── static/           # CSS, JS, and assets
├── backup_to_s3.py       # S3 backup script
├── setup-backup-cron.sh  # Backup cron job setup
├── setup-aws-credentials.sh # AWS credentials setup
├── deploy-local-simple.sh # Local deployment script
├── deploy-github-actions.sh # GitHub Actions deployment
├── wsgi.py              # WSGI entry point
├── config.py            # Configuration settings
├── requirements.txt     # Python dependencies
├── BACKUP_SETUP.md      # Backup system documentation
└── README.md
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
