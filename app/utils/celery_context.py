"""
Celery context utilities
"""
from functools import wraps
from app import create_app

def with_app_context(func):
    """Decorator to add Flask app context to Celery tasks"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        app = create_app()
        with app.app_context():
            return func(*args, **kwargs)
    return wrapper 