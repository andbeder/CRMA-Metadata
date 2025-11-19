#!/usr/bin/env python
"""
CRMA Metadata Extractor - Main entry point
"""
from app import create_app
from config import Config

app = create_app()

if __name__ == '__main__':
    print(f"Starting CRMA Metadata Extractor on http://{Config.HOST}:{Config.PORT}")
    app.run(host=Config.HOST, port=Config.PORT, debug=Config.DEBUG)
