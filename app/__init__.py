"""
AI Rate Limiter Application Factory
"""
import os
import time
from flask import Flask, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_cors import CORS
from celery import Celery
import psycopg2
from psycopg2 import OperationalError

# Initialize extensions
db = SQLAlchemy()
migrate = Migrate()
celery = Celery('ai_rate_limiter')

def wait_for_database(max_retries=30, retry_interval=2):
    """Wait for database to be ready"""
    print("⏳ Waiting for database to be ready...")
    
    for attempt in range(max_retries):
        try:
            # Try to connect to the database
            conn = psycopg2.connect(
                host=os.getenv('POSTGRES_HOST', 'postgres'),
                port=os.getenv('POSTGRES_PORT', '5432'),
                database=os.getenv('POSTGRES_DB', 'ai_rate_limiter'),
                user=os.getenv('POSTGRES_USER', 'postgres'),
                password=os.getenv('POSTGRES_PASSWORD', 'postgres')
            )
            conn.close()
            print("✅ Database is ready!")
            return True
        except OperationalError:
            print(f"Database is unavailable - attempt {attempt + 1}/{max_retries}")
            if attempt < max_retries - 1:
                time.sleep(retry_interval)
    
    print("❌ Database connection failed after all retries")
    return False

def create_app():
    """Application factory pattern"""
    app = Flask(__name__)
    
    # Load configuration
    app.config.from_object('app.config.config.Config')
    
    # Wait for database to be ready (only in production/container environment)
    if os.getenv('FLASK_ENV') != 'development':
        if not wait_for_database():
            print("⚠️  Continuing without database connection...")
    
    # Initialize extensions
    db.init_app(app)
    migrate.init_app(app, db)
    CORS(app)
    
    # Initialize Celery
    celery.conf.update(
        broker_url=app.config.get('CELERY_BROKER_URL'),
        result_backend=app.config.get('CELERY_RESULT_BACKEND'),
        task_serializer='json',
        accept_content=['json'],
        result_serializer='json',
        timezone='UTC',
        enable_utc=True,
        task_track_started=True,
        task_time_limit=30 * 60,  # 30 minutes
    )
    
    # Import tasks to register them with Celery
    # This is crucial - it registers the tasks with Celery
    from app.tasks import worker_tasks
    
    # Register blueprints
    from app.routes.queue_routes import queue_bp
    from app.routes.provider_routes import provider_bp
    from app.routes.worker_routes import worker_bp
    from app.routes.message_routes import message_bp

    app.register_blueprint(queue_bp, url_prefix='/api/v1')
    app.register_blueprint(provider_bp, url_prefix='/api/v1')
    app.register_blueprint(worker_bp, url_prefix='/api/v1')
    app.register_blueprint(message_bp, url_prefix='/api/v1')
    
    # Health check endpoint
    @app.route('/health')
    def health_check():
        return jsonify({
            'status': 'healthy',
            'service': 'ai-rate-limiter',
            'version': '1.0.0'
        })
    
    # Create database tables (with error handling)
    with app.app_context():
        try:
            db.create_all()
            print("✅ Database tables created successfully")
        except Exception as e:
            print(f"⚠️  Database initialization failed: {e}")

    return app 