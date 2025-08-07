# app/services/queue_service.py (Improved)
"""
Queue service for managing message queues with APISIX AI Gateway integration
"""
import uuid
import time
from typing import List, Optional, Dict, Any
from app import db
from app.models.queue import Queue
from app.models.provider import Provider
from app.utils.exceptions import QueueNotFoundError, QueueAlreadyExistsError
from app.apisix_gateway import create_route, update_route, delete_route

class QueueService:
    """Service for managing queues with APISIX AI Gateway"""
    
    @staticmethod
    def create_queue(queue_name: str, providers: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Create a new queue with queue_name and providers, auto-configure APISIX"""
        try:
            # Check if queue with same name already exists
            existing_queue = Queue.query.filter_by(queue_name=queue_name).first()
            if existing_queue:
                raise QueueAlreadyExistsError(f"Queue with name '{queue_name}' already exists")
            
            # Create queue with auto-generated queue_id
            queue = Queue(queue_name=queue_name)
            db.session.add(queue)
            db.session.flush()  # Get the queue ID
            
            # Create providers
            created_providers = []
            for provider_data in providers:
                # Validate required fields for each provider
                required_fields = ['provider_name', 'api_key', 'limit', 'time_window']
                for field in required_fields:
                    if not provider_data.get(field):
                        raise ValueError(f"Provider '{provider_data.get('provider_name', 'unknown')}' is missing required field: {field}")
                
                provider = Provider(
                    queue_id=queue.queue_id,
                    provider_name=provider_data['provider_name'],
                    provider_type=provider_data.get('provider_type', 'openai'),
                    api_key=provider_data['api_key'],
                    limit=provider_data['limit'],
                    time_window=provider_data['time_window'],
                    config=provider_data.get('config', {})
                )
                db.session.add(provider)
                created_providers.append(provider)
            
            db.session.commit()
            
            # Create APISIX AI Gateway route
            try:
                providers_data = [p.to_dict() for p in created_providers]
                print(f"🔧 Creating APISIX route for queue {queue.queue_id} with {len(providers_data)} providers")
                apisix_result = create_route(str(queue.queue_id), providers_data)
                routes_created = apisix_result.get('success', False)
                route_path = apisix_result.get('route_path', '')
                
                if routes_created:
                    print(f"✅ APISIX route created successfully for queue {queue.queue_id}")
                else:
                    error_msg = apisix_result.get('error', 'Unknown error')
                    print(f"⚠️  APISIX route creation failed for queue {queue.queue_id}: {error_msg}")
                    
            except Exception as e:
                print(f"⚠️  APISIX route creation failed: {e}")
                routes_created = False
                route_path = ''
            
            print(f"🔧 Route creation result: {routes_created}")
            result = {
                'success': True,
                'message': 'Queue and providers created successfully',
                'queue': queue.to_dict(),
                'providers': [p.to_dict() for p in created_providers],
                'apisix_routes_created': routes_created
            }
            
            if routes_created and route_path:
                result['route_path'] = route_path
                result['message'] = f'Queue and providers created successfully. Route available at: {route_path}'
            
            if not routes_created:
                result['warning'] = 'APISIX routes could not be created. Routes will be created on first message processing.'
            
            return result
            
        except Exception as e:
            db.session.rollback()
            raise e
    

    
    @staticmethod
    def ensure_queue_routes_exist(queue_id: str) -> bool:
        """Ensure all routes for a queue exist - can be called before processing messages"""
        try:
            # Handle special case for batch_aggregator
            if queue_id == 'batch_aggregator':
                print(f"ℹ️  Skipping APISIX route creation for batch_aggregator queue")
                return True
            
            queue_uuid = uuid.UUID(queue_id)
            
            # Get queue and providers
            queue = Queue.query.filter_by(queue_id=queue_uuid).first()
            if not queue:
                print(f"❌ Queue {queue_id} not found")
                return False
            
            providers = Provider.query.filter_by(queue_id=queue_uuid).all()
            if not providers:
                print(f"❌ No providers found for queue {queue_id}")
                return False
            
            # Create or update APISIX AI Gateway route
            try:
                providers_data = [p.to_dict() for p in providers]
                apisix_result = create_route(queue_id, providers_data)
                return apisix_result.get('success', False)
            except Exception as e:
                print(f"❌ Error creating APISIX route: {e}")
                return False
            
        except Exception as e:
            print(f"❌ Error ensuring queue routes exist: {e}")
            return False
    
    @staticmethod
    def get_queue(queue_id: str) -> Dict[str, Any]:
        """Get queue by ID with providers"""
        try:
            queue_uuid = uuid.UUID(queue_id)
        except ValueError:
            raise ValueError(f"Invalid UUID format: {queue_id}. Please provide a valid UUID.")
        
        queue = Queue.query.filter_by(queue_id=queue_uuid).first()
        if not queue:
            raise QueueNotFoundError(f"Queue {queue_id} not found")
        
        providers = Provider.query.filter_by(queue_id=queue_uuid).all()
        
        return {
            'success': True,
            'data': {
                **queue.to_dict(),
                'providers': [p.to_dict() for p in providers]
            }
        }
    
    @staticmethod
    def get_all_queues() -> Dict[str, Any]:
        """Get all queues with their providers"""
        queues = Queue.query.all()
        result = []
        
        for queue in queues:
            providers = Provider.query.filter_by(queue_id=queue.queue_id).all()
            queue_data = queue.to_dict()
            queue_data['providers'] = [p.to_dict() for p in providers]
            result.append(queue_data)
        
        return {
            'data': result
        }
    
    @staticmethod
    def delete_queue(queue_id: str) -> Dict[str, Any]:
        """Delete a queue and all its associated data"""
        try:
            queue_uuid = uuid.UUID(queue_id)
        except ValueError:
            raise ValueError(f"Invalid UUID format: {queue_id}. Please provide a valid UUID.")
        
        queue = Queue.query.filter_by(queue_id=queue_uuid).first()
        if not queue:
            raise QueueNotFoundError(f"Queue {queue_id} not found")
        
        # Delete APISIX AI Gateway route
        try:
            delete_route(queue_id)
        except Exception as e:
            print(f"⚠️  Warning: Could not delete APISIX route: {e}")
        
        db.session.delete(queue)
        db.session.commit()
        
        return {
            'success': True,
            'message': f"Queue {queue_id} deleted successfully"
        }
    
    @staticmethod
    def clear_queue(queue_id: str) -> Dict[str, Any]:
        """Clear all messages and stop workers for a queue"""
        try:
            queue_uuid = uuid.UUID(queue_id)
        except ValueError:
            raise ValueError(f"Invalid UUID format: {queue_id}. Please provide a valid UUID.")
        
        queue = Queue.query.filter_by(queue_id=queue_uuid).first()
        if not queue:
            raise QueueNotFoundError(f"Queue {queue_id} not found")
        
        # Delete all messages
        from app.models.message import Message
        messages_deleted = Message.query.filter_by(queue_id=queue_uuid).delete()
        
        # Stop all workers
        from app.models.worker import Worker
        workers_stopped = Worker.query.filter_by(queue_id=queue_uuid).delete()
        
        db.session.commit()
        
        return {
            'success': True,
            'message': f"Queue {queue_id} cleared and all workers stopped and removed messages successfully",
            'messages_deleted': messages_deleted,
            'workers_stopped': workers_stopped
        }