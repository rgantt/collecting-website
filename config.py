import os
from pathlib import Path

class Config:
    SECRET_KEY = os.environ.get('FLASK_SECRET_KEY') or 'dev-key-please-change-in-production'
