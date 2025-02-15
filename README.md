# Collecting Tools Web Application

A web interface for managing and tracking video game collections, designed to be deployed on AWS Elastic Beanstalk.

## Features

- Game collection management
- Authentication system
- Responsive web interface
- Database persistence
- AWS deployment ready

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
- SQLite for local development database
- Jinja2 for templating
- Authlib for authentication

## Deployment

The application is configured for AWS Elastic Beanstalk deployment:

1. Ensure you have the AWS CLI and EB CLI installed
2. Configure your AWS credentials
3. Deploy using the provided script:
```bash
./deploy-local.sh
```

## Project Structure

```
collecting-website/
├── .elasticbeanstalk/    # AWS EB configuration
├── app/                   # Application code
│   ├── __init__.py       # App initialization
│   ├── routes.py         # URL routes and views
│   ├── auth.py           # Authentication logic
│   ├── templates/        # Jinja2 templates
│   └── static/           # CSS, JS, and assets
├── .env                  # Environment variables (git-ignored)
├── .env.example          # Example environment configuration
├── application.py        # Application entry point
├── config.py            # Configuration settings
├── deploy-local.sh      # Deployment script
├── requirements.txt     # Python dependencies
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
