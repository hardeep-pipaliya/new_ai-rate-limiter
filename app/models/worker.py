"""
Worker model for managing Celery workers
"""
from datetime import datetime
from app import db
from sqlalchemy.dialects.postgresql import UUID
import uuid

class Worker(db.Model):
    """Worker model for managing Celery workers"""
    
    __tablename__ = 'workers'
    
    id = db.Column(db.Integer, primary_key=True)
    worker_id = db.Column(UUID(as_uuid=True), unique=True, nullable=False, default=uuid.uuid4)
    queue_id = db.Column(UUID(as_uuid=True), db.ForeignKey('queues.queue_id'), nullable=False)
    pid = db.Column(db.Integer, nullable=False)
    status = db.Column(db.String(50), default='running', nullable=False)
    log_file = db.Column(db.String(255), nullable=True)
    started_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_heartbeat = db.Column(db.DateTime, default=datetime.utcnow)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f'<Worker {self.worker_id}>'
    
    def to_dict(self):
        """Convert to dictionary"""
        return {
            'worker_id': str(self.worker_id),
            'queue_id': str(self.queue_id),
            'pid': self.pid,
            'status': self.status,
            'log_file': self.log_file,
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'last_heartbeat': self.last_heartbeat.isoformat() if self.last_heartbeat else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        } 