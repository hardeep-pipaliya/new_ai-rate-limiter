"""
Logging configuration for the AI Rate Limiter application
"""
import os
import logging
from logging.handlers import RotatingFileHandler
from flask import Flask

def setup_logger(app: Flask):
    """Setup logging configuration"""
    
    # Create logs directory if it doesn't exist
    log_dir = os.path.dirname(app.config['LOG_FILE'])
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
    
    # Set log level
    log_level = getattr(logging, app.config['LOG_LEVEL'].upper())
    
    # Configure root logger
    logging.basicConfig(level=log_level)
    
    # Create file handler
    file_handler = RotatingFileHandler(
        app.config['LOG_FILE'],
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=5
    )
    file_handler.setLevel(log_level)
    
    # Create formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    file_handler.setFormatter(formatter)
    
    # Add handler to app logger
    app.logger.addHandler(file_handler)
    app.logger.setLevel(log_level)
    
    # Also add to root logger
    logging.getLogger().addHandler(file_handler)
    
    return app.logger 