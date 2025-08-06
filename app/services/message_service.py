"""
Message service for processing AI requests
"""
import uuid
import json
from typing import List, Dict, Any, Optional
from app import db
from app.models.message import Message
from app.models.queue import Queue
from app.models.provider import Provider
from app.models.batch import Batch
from app.utils.exceptions import QueueNotFoundError, MessageNotFoundError
from app.services.redis_service import RedisService
from app.services.rabbitmq_service import RabbitMQService

class MessageService:
    """Service for managing messages"""
    
    @staticmethod
    def create_message(message_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a single message with individual batch_id and message_id"""
        queue_id = message_data.get('queue_id')
        
        # Check if queue exists
        queue = Queue.query.filter_by(queue_id=queue_id).first()
        if not queue:
            raise QueueNotFoundError(f"Queue {queue_id} not registered please register it first")
        
        # Generate batch_id and message_id for single message
        batch_id = uuid.uuid4()
        message_id = uuid.uuid4()
        
        # Create batch entry
        batch = Batch(
            batch_id=batch_id,
            request_count=1,  # Single message = 1 request
            response_count=0,
            status='processing'
        )
        db.session.add(batch)
        
        # Create message
        message = Message(
            message_id=message_id,
            batch_id=batch_id,
            queue_id=queue_id,
            prompt=message_data.get('prompt'),
            system_prompt=message_data.get('system_prompt'),
            supportive_variable=message_data.get('supportive_variable', {}),
            status='pending'
        )
        
        db.session.add(message)
        db.session.commit()
        
        # Initialize Redis counters for this batch
        RedisService.init_batch_counters(str(batch_id), 1)
        
        # Queue message for processing using Celery task
        from app.tasks.worker_tasks import process_message
        # Send to specific queue based on queue_id
        process_message.apply_async(args=[str(message_id)], queue=str(queue_id))
        
        return {
            'success': True,
            'message': 'Message created successfully',
            'batch_id': str(batch_id),
            'message_id': str(message_id)
        }
    
    @staticmethod
    def create_batch_messages(batch_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create batch of messages with same batch_id but different message_ids"""
        queue_id = batch_data.get('queue_id')
        messages = batch_data.get('messages', [])
        webhook_url = batch_data.get('webhook_url')
        webhook_event = batch_data.get('webhook_event', 'on_complete')
        
        # Check if queue exists
        queue = Queue.query.filter_by(queue_id=queue_id).first()
        if not queue:
            raise QueueNotFoundError(f"Queue {queue_id} not registered please register it first")
        
        # Generate single batch_id for all messages in the batch
        batch_id = uuid.uuid4()
        
        # Create batch entry
        batch = Batch(
            batch_id=batch_id,
            request_count=len(messages),
            response_count=0,
            webhook_url=webhook_url,
            webhook_event=webhook_event,
            status='processing'
        )
        db.session.add(batch)
        db.session.flush()
        
        # Create messages with same batch_id but different message_ids
        created_messages = []
        for msg_data in messages:
            message_id = uuid.uuid4()  # Generate unique message_id for each message
            
            message = Message(
                message_id=message_id,
                batch_id=batch_id,  # Same batch_id for all messages in batch
                queue_id=queue_id,
                prompt=msg_data.get('prompt'),
                system_prompt=msg_data.get('system_prompt'),
                supportive_variable=msg_data.get('supportive_variable', {}),
                status='pending'
            )
            db.session.add(message)
            created_messages.append(message)
        
        db.session.commit()
        
        # Initialize Redis counters for this batch
        RedisService.init_batch_counters(str(batch_id), len(messages))
        
        # Queue messages for processing using Celery tasks
        from app.tasks.worker_tasks import process_message
        for message in created_messages:
            # Send to specific queue based on queue_id
            process_message.apply_async(args=[str(message.message_id)], queue=str(queue_id))
        
        return {
            'success': True,
            'message': 'Batch created successfully',
            'batch_id': str(batch_id),
            'message_count': len(created_messages),
            'message_ids': [str(msg.message_id) for msg in created_messages]
        }
    
    @staticmethod
    def get_message(message_id: str) -> Dict[str, Any]:
        """Get message by ID"""
        message = Message.query.filter_by(message_id=message_id).first()
        if not message:
            raise MessageNotFoundError(f"Message {message_id} not found")
        
        return {
            'success': True,
            'data': message.to_dict()
        }
    
    @staticmethod
    def delete_message(message_id: str) -> Dict[str, Any]:
        """Delete message by ID"""
        message = Message.query.filter_by(message_id=message_id).first()
        if not message:
            raise MessageNotFoundError(f"Message {message_id} not found")
        
        db.session.delete(message)
        db.session.commit()
        
        return {
            'success': True,
            'message': 'Message deleted successfully'
        }
    
    @staticmethod
    def get_batch_messages(batch_id: str) -> Dict[str, Any]:
        """Get all messages for a batch"""
        messages = Message.query.filter_by(batch_id=batch_id).all()
        
        return {
            'success': True,
            'data': [msg.to_dict() for msg in messages]
        }
    
    @staticmethod
    def update_message_status(message_id: str, status: str, result: str = None, error_message: str = None) -> None:
        """Update message status and result"""
        message = Message.query.filter_by(message_id=message_id).first()
        if message:
            message.status = status
            if result:
                message.result = result
            if error_message:
                message.error_message = error_message
            db.session.commit() 