import os
from pathlib import Path

class Config:
    SECRET_KEY = os.environ.get('FLASK_SECRET_KEY') or 'dev-key-please-change-in-production'
    DATABASE_PATH = os.environ.get('DATABASE_PATH') or str(Path(__file__).parent / "games.db")
