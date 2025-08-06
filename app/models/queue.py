"""
Queue model for managing message queues
"""
from datetime import datetime
from app import db
from sqlalchemy.dialects.postgresql import UUID
import uuid

class Queue(db.Model):
    """Queue model for managing message queues"""
    
    __tablename__ = 'queues'
    
    id = db.Column(db.Integer, primary_key=True)
    queue_id = db.Column(UUID(as_uuid=True), unique=True, nullable=False, default=uuid.uuid4)
    queue_name = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    providers = db.relationship('Provider', backref='queue', lazy='dynamic', cascade='all, delete-orphan')
    messages = db.relationship('Message', backref='queue', lazy='dynamic', cascade='all, delete-orphan')
    workers = db.relationship('Worker', backref='queue', lazy='dynamic', cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<Queue {self.queue_id}>'
    
    def to_dict(self):
        """Convert to dictionary"""
        return {
            'queue_id': str(self.queue_id),
            'queue_name': self.queue_name,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        } 