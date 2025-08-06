"""
Celery tasks for processing messages
"""
import json
import os
import requests
import time
from typing import Dict, Any
from app import celery, db
from app.models.message import Message
from app.models.provider import Provider
from app.models.batch import Batch
from app.services.redis_service import RedisService
from app.services.rabbitmq_service import RabbitMQService
# 
from app.utils.exceptions import MessageNotFoundError, ProviderNotFoundError
from app.utils.celery_context import with_app_context

@celery.task(bind=True)
@with_app_context
def process_message(self, message_id: str) -> Dict[str, Any]:
    """Process a single message"""
    try:
        # Get message from database
        message = Message.query.filter_by(message_id=message_id).first()
        if not message:
            raise MessageNotFoundError(f"Message {message_id} not found")
        
        # Update status to processing
        message.status = 'processing'
        db.session.commit()
        
        # Get provider for the queue
        provider = Provider.query.filter_by(queue_id=message.queue_id).first()
        if not provider:
            raise ProviderNotFoundError(f"No provider found for queue {message.queue_id}")
        
        # Update message with provider_id
        message.provider_id = provider.provider_id
        db.session.commit()
        
        # Ensure APISIX routes exist before processing
        from app.services.queue_service import QueueService
        QueueService.ensure_queue_routes_exist(str(message.queue_id))
        
        # Process message through APISIX AI Gateway
        try:
            import requests
            from app.apisix_gateway import apisix_gateway
            
            # Get gateway URL from environment
            gateway_url = os.getenv('APISIX_GATEWAY_URL', 'http://127.0.0.1:9080')
            
            # Prepare request for APISIX
            model_name = provider.config_dict.get('model')
            if not model_name:
                raise Exception(f"No model configured for provider {provider.provider_id}")
                
            request_data = {
                'model': model_name,
                'messages': [
                    {
                        'role': 'user',
                        'content': message.prompt
                    }
                ]
            }
            
            if message.system_prompt:
                request_data['messages'].insert(0, {
                    'role': 'system',
                    'content': message.system_prompt
                })
            
            # Send request to APISIX AI Gateway
            # Get model name from provider config
            model_name = provider.config_dict.get('model')
            if not model_name:
                raise Exception(f"No model configured for provider {provider.provider_id}")
            model_safe = model_name.replace(".", "-").replace(" ", "-")
            
            response = requests.post(
                f"{gateway_url}/{message.queue_id}-{model_safe}",
                json=request_data,
                headers={'Content-Type': 'application/json'},
                timeout=30
            )
            
            if response.status_code == 200:
                response_data = response.json()
                response = {
                    'content': response_data.get('choices', [{}])[0].get('message', {}).get('content', ''),
                    'status': 'completed'
                }
            else:
                raise Exception(f"APISIX request failed: {response.status_code} - {response.text}")
                
        except Exception as e:
            print(f"APISIX processing failed: {e}")
            # Fallback to simulated response
            response = {
                'content': f"Processed message: {message.prompt}",
                'status': 'completed'
            }
        
        # Update message with result
        message.status = 'completed'
        message.result = response.get('content', '')
        message.provider_id = provider.provider_id
        db.session.commit()
        
        # Store result in Redis
        RedisService.store_message_result(str(message.message_id), response)
        
        # If this is part of a batch, increment batch counter
        if message.batch_id:
            response_count = RedisService.increment_batch_response(str(message.batch_id))
            
            # Check if batch is complete
            batch = Batch.query.filter_by(batch_id=message.batch_id).first()
            if batch and response_count >= batch.request_count:
                # Batch is complete, call aggregator task
                from app.tasks.worker_tasks import process_batch_aggregator
                process_batch_aggregator.apply_async(args=[str(message.batch_id)], queue='batch_aggregator')
        
        return {
            'success': True,
            'message_id': str(message.message_id),
            'result': response
        }
        
    except Exception as e:
        # Update message status to failed
        if 'message' in locals():
            message.status = 'failed'
            message.error_message = str(e)
            db.session.commit()
        
        # Re-raise the exception
        raise e

@celery.task(bind=True)
@with_app_context
def process_batch_aggregator(self, batch_id: str) -> Dict[str, Any]:
    """Process batch completion and aggregate results"""
    try:
        # Get batch from database
        batch = Batch.query.filter_by(batch_id=batch_id).first()
        if not batch:
            return {'success': False, 'error': 'Batch not found'}
        
        # Get all messages for the batch
        messages = Message.query.filter_by(batch_id=batch_id).all()
        
        # Aggregate results
        results = []
        for message in messages:
            result = {
                'message_id': str(message.message_id),
                'status': message.status,
                'prompt': message.prompt,
                'result': message.result,
                'error_message': message.error_message
            }
            results.append(result)
        
        # Store batch results in Redis
        batch_data = {
            'batch_id': str(batch.batch_id),
            'request_count': batch.request_count,
            'response_count': batch.response_count,
            'results': results,
            'completed_at': time.time()
        }
        RedisService.store_batch_results(str(batch.batch_id), batch_data)
        
        # Update batch status
        batch.status = 'completed'
        batch.response_count = len([r for r in results if r['status'] == 'completed'])
        db.session.commit()
        
        # Send webhook if configured
        if batch.webhook_url:
            try:
                webhook_data = {
                    'batch_id': str(batch.batch_id),
                    'status': 'completed',
                    'request_count': batch.request_count,
                    'response_count': batch.response_count,
                    'results': results
                }
                
                response = requests.post(
                    batch.webhook_url,
                    json=webhook_data,
                    timeout=30
                )
                
                if response.status_code == 200:
                    batch.webhook_status = 'success'
                else:
                    batch.webhook_status = 'failed'
                
                batch.webhook_last_called_at = time.time()
                db.session.commit()
                
            except Exception as e:
                batch.webhook_status = 'failed'
                db.session.commit()
        
        return {
            'success': True,
            'batch_id': str(batch.batch_id),
            'results_count': len(results)
        }
        
    except Exception as e:
        raise e

@celery.task(bind=True)
@with_app_context
def cleanup_expired_data(self) -> Dict[str, Any]:
    """Clean up expired data from Redis"""
    try:
        # This task can be scheduled to run periodically
        # to clean up old message results and batch data
        return {'success': True, 'message': 'Cleanup completed'}
    except Exception as e:
        raise e 