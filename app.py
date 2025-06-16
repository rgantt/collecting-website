#!/usr/bin/env python3
"""
Main application entry point for self-hosted deployment
"""
from app import create_app
import os

app = create_app()

if __name__ == '__main__':
    # For development
    app.run(host='0.0.0.0', port=8080, debug=True)
