"""
Provider model for AI service providers
"""
from datetime import datetime
from app import db
from sqlalchemy.dialects.postgresql import UUID, JSON
import uuid
import json

class Provider(db.Model):
    """Provider model for AI service providers"""
    
    __tablename__ = 'providers'
    
    id = db.Column(db.Integer, primary_key=True)
    provider_id = db.Column(UUID(as_uuid=True), unique=True, nullable=False, default=uuid.uuid4)
    queue_id = db.Column(UUID(as_uuid=True), db.ForeignKey('queues.queue_id'), nullable=False)
    provider_name = db.Column(db.String(255), nullable=False)
    provider_type = db.Column(db.String(50), nullable=False)
    api_key = db.Column(db.String(500), nullable=False)
    limit = db.Column(db.Integer, nullable=False, default=1000)
    time_window = db.Column(db.Integer, nullable=False, default=3600)  # seconds
    config = db.Column(JSON, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    messages = db.relationship('Message', backref='provider', lazy='dynamic', cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<Provider {self.provider_name}>'
    
    def to_dict(self):
        """Convert to dictionary"""
        return {
            'provider_id': str(self.provider_id),
            'queue_id': str(self.queue_id),
            'provider_name': self.provider_name,
            'provider_type': self.provider_type,
            'api_key': self.api_key,
            'limit': self.limit,
            'time_window': self.time_window,
            'config': self.config,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
    
    @property
    def config_dict(self):
        """Get config as dictionary"""
        if isinstance(self.config, str):
            return json.loads(self.config)
        return self.config or {}
    
    @config_dict.setter
    def config_dict(self, value):
        """Set config from dictionary"""
        if isinstance(value, dict):
            self.config = value
        else:
            self.config = json.loads(value) if isinstance(value, str) else {} 