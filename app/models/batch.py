"""
Batch model for managing batch processing
"""
from datetime import datetime
from app import db
from sqlalchemy.dialects.postgresql import UUID
import uuid

class Batch(db.Model):
    """Batch model for managing batch processing"""
    
    __tablename__ = 'batches'
    
    id = db.Column(db.Integer, primary_key=True)
    batch_id = db.Column(UUID(as_uuid=True), unique=True, nullable=False, default=uuid.uuid4)
    request_count = db.Column(db.Integer, default=0, nullable=False)
    response_count = db.Column(db.Integer, default=0, nullable=False)
    webhook_url = db.Column(db.String(500), nullable=True)
    webhook_event = db.Column(db.String(50), nullable=True)  # on_complete, on_error, on_partial
    webhook_status = db.Column(db.String(50), default='pending', nullable=False)
    webhook_last_called_at = db.Column(db.DateTime, nullable=True)
    status = db.Column(db.String(50), default='processing', nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    messages = db.relationship('Message', backref='batch', lazy='dynamic', cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<Batch {self.batch_id}>'
    
    def to_dict(self):
        """Convert to dictionary"""
        return {
            'batch_id': str(self.batch_id),
            'request_count': self.request_count,
            'response_count': self.response_count,
            'webhook_url': self.webhook_url,
            'webhook_event': self.webhook_event,
            'webhook_status': self.webhook_status,
            'webhook_last_called_at': self.webhook_last_called_at.isoformat() if self.webhook_last_called_at else None,
            'status': self.status,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
    
    @property
    def is_complete(self):
        """Check if batch is complete"""
        return self.response_count >= self.request_count
    
    @property
    def completion_percentage(self):
        """Get completion percentage"""
        if self.request_count == 0:
            return 0
        return (self.response_count / self.request_count) * 100 