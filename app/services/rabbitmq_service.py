"""
RabbitMQ service for message queuing
"""
import json
import pika
from typing import Dict, Any, Callable
from app.config.config import Config

class RabbitMQService:
    """Service for RabbitMQ operations"""
    
    _connection = None
    _channel = None
    
    @classmethod
    def get_connection(cls):
        """Get RabbitMQ connection"""
        if cls._connection is None or cls._connection.is_closed:
            cls._connection = pika.BlockingConnection(
                pika.URLParameters(Config.RABBITMQ_URL)
            )
        return cls._connection
    
    @classmethod
    def get_channel(cls):
        """Get RabbitMQ channel"""
        if cls._channel is None or cls._channel.is_closed:
            connection = cls.get_connection()
            cls._channel = connection.channel()
        return cls._channel
    
    @classmethod
    def declare_queue(cls, queue_name: str) -> None:
        """Declare a queue"""
        channel = cls.get_channel()
        channel.queue_declare(queue=queue_name, durable=True)
    
    @classmethod
    def publish_message(cls, message_id: str, queue_name: str, message_data: Dict[str, Any] = None) -> None:
        """Publish message to queue"""
        channel = cls.get_channel()
        
        # Declare queue if it doesn't exist
        cls.declare_queue(queue_name)
        
        # Prepare message
        message = {
            'message_id': message_id,
            'queue_name': queue_name,
            'data': message_data or {}
        }
        
        # Publish message
        channel.basic_publish(
            exchange='',
            routing_key=queue_name,
            body=json.dumps(message),
            properties=pika.BasicProperties(
                delivery_mode=2,  # make message persistent
            )
        )
    
    @classmethod
    def publish_batch_complete(cls, batch_id: str) -> None:
        """Publish batch completion to aggregator queue"""
        channel = cls.get_channel()
        
        # Declare aggregator queue
        aggregator_queue = 'batch_aggregator'
        cls.declare_queue(aggregator_queue)
        
        # Publish batch completion
        message = {
            'batch_id': batch_id,
            'event': 'batch_complete'
        }
        
        channel.basic_publish(
            exchange='',
            routing_key=aggregator_queue,
            body=json.dumps(message),
            properties=pika.BasicProperties(
                delivery_mode=2,
            )
        )
    
    @classmethod
    def consume_messages(cls, queue_name: str, callback: Callable) -> None:
        """Consume messages from queue"""
        channel = cls.get_channel()
        
        # Declare queue
        cls.declare_queue(queue_name)
        
        # Set up consumer
        channel.basic_consume(
            queue=queue_name,
            on_message_callback=callback,
            auto_ack=False
        )
        
        print(f"Starting to consume messages from {queue_name}")
        channel.start_consuming()
    
    @classmethod
    def consume_batch_aggregator(cls, callback: Callable) -> None:
        """Consume batch completion messages"""
        cls.consume_messages('batch_aggregator', callback)
    
    @classmethod
    def close_connection(cls) -> None:
        """Close RabbitMQ connection"""
        if cls._channel and not cls._channel.is_closed:
            cls._channel.close()
        if cls._connection and not cls._connection.is_closed:
            cls._connection.close() 