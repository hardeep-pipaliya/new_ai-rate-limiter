"""
Message model for processing AI requests
"""
from datetime import datetime
from app import db
from sqlalchemy.dialects.postgresql import UUID, JSON
import uuid
import json

class Message(db.Model):
    """Message model for processing AI requests"""
    
    __tablename__ = 'messages'
    
    id = db.Column(db.Integer, primary_key=True)
    message_id = db.Column(UUID(as_uuid=True), unique=True, nullable=False, default=uuid.uuid4)
    batch_id = db.Column(UUID(as_uuid=True), db.ForeignKey('batches.batch_id'), nullable=True)
    queue_id = db.Column(UUID(as_uuid=True), db.ForeignKey('queues.queue_id'), nullable=False)
    provider_id = db.Column(UUID(as_uuid=True), db.ForeignKey('providers.provider_id'), nullable=True)
    status = db.Column(db.String(50), default='pending', nullable=False)
    prompt = db.Column(db.Text, nullable=False)
    system_prompt = db.Column(db.Text, nullable=True)
    result = db.Column(db.Text, nullable=True)
    supportive_variable = db.Column(JSON, nullable=True)
    error_message = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f'<Message {self.message_id}>'
    
    def to_dict(self):
        """Convert to dictionary"""
        return {
            'message_id': str(self.message_id),
            'batch_id': str(self.batch_id) if self.batch_id else None,
            'queue_id': str(self.queue_id),
            'provider_id': str(self.provider_id) if self.provider_id else None,
            'status': self.status,
            'prompt': self.prompt,
            'system_prompt': self.system_prompt,
            'result': self.result,
            'supportive_variable': self.supportive_variable,
            'error_message': self.error_message,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
    
    @property
    def supportive_variable_dict(self):
        """Get supportive_variable as dictionary"""
        if isinstance(self.supportive_variable, str):
            return json.loads(self.supportive_variable)
        return self.supportive_variable or {}
    
    @supportive_variable_dict.setter
    def supportive_variable_dict(self, value):
        """Set supportive_variable from dictionary"""
        if isinstance(value, dict):
            self.supportive_variable = value
        else:
            self.supportive_variable = json.loads(value) if isinstance(value, str) else {} 