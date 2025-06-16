from flask import Flask
from pathlib import Path
from config import Config
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def create_app(config_class=Config):
    app = Flask(__name__)
    app.debug = True
    app.config.from_object(config_class)

    from app.routes import main, update_url_params
    app.register_blueprint(main)
    app.template_filter('update_url_params')(update_url_params)

    # Add built-in functions to Jinja environment
    app.jinja_env.globals.update(min=min, max=max, range=range)

    return app
