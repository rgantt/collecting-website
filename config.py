import os
from pathlib import Path

class Config:
    SECRET_KEY = os.environ.get('FLASK_SECRET_KEY') or 'dev-key-please-change-in-production'
    DATABASE_PATH = os.environ.get('DATABASE_PATH') or str(Path(__file__).parent / "games.db")
    
    # S3 Photo Storage Configuration
    S3_PHOTOS_BUCKET = os.environ.get('S3_PHOTOS_BUCKET', 'collecting-photos-dev')
    S3_REGION = os.environ.get('S3_REGION', 'us-east-1')
    S3_ACCESS_KEY = os.environ.get('AWS_ACCESS_KEY_ID')
    S3_SECRET_KEY = os.environ.get('AWS_SECRET_ACCESS_KEY')
    
    # Photo upload constraints
    MAX_PHOTO_SIZE = int(os.environ.get('MAX_PHOTO_SIZE_MB', '5')) * 1024 * 1024  # 5 MiB default
    ALLOWED_PHOTO_TYPES = ['image/jpeg', 'image/png', 'image/webp']
    MAX_PHOTOS_PER_GAME = int(os.environ.get('MAX_PHOTOS_PER_GAME', '20'))
    PHOTO_UPLOAD_EXPIRY_MINUTES = int(os.environ.get('PHOTO_UPLOAD_EXPIRY_MINUTES', '15'))
