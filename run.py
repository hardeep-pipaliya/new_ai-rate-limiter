#!/usr/bin/env python3
"""
AI Rate Limiter Application Entry Point
"""
import os
from app import create_app

app = create_app()

if __name__ == '__main__':
    host = os.getenv('SERVER_HOST', '0.0.0.0')
    port = int(os.getenv('SERVER_PORT', 8501))
    debug = os.getenv('FLASK_ENV') == 'development'
    
    app.run(host=host, port=port, debug=debug) 