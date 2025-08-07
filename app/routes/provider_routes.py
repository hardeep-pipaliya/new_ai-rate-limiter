"""
Provider routes for managing AI providers
"""
from flask import Blueprint, request, jsonify
from app import db
from app.models.provider import Provider
from app.models.queue import Queue
from app.utils.exceptions import ProviderNotFoundError, QueueNotFoundError
from app.apisix_gateway import update_route

provider_bp = Blueprint('provider', __name__)

def update_apisix_routes_for_queue(queue_id: str) -> bool:
    """Update APISIX routes for a queue with all its providers"""
    try:
        # Get all providers for the queue
        providers = Provider.query.filter_by(queue_id=queue_id).all()
        if not providers:
            print(f"⚠️  No providers found for queue {queue_id}")
            return False
        
        # Convert providers to dict format
        providers_data = [p.to_dict() for p in providers]
        
        print(f"🔧 Updating APISIX routes for queue {queue_id} with {len(providers_data)} providers")
        
        # Update APISIX route
        apisix_result = update_route(queue_id, providers_data)
        routes_updated = apisix_result.get('success', False)
        
        if routes_updated:
            print(f"✅ Updated APISIX routes for queue {queue_id}")
        else:
            error_msg = apisix_result.get('error', 'Unknown error')
            print(f"⚠️  Failed to update APISIX routes for queue {queue_id}: {error_msg}")
            
            # Try to create the route if update failed
            print(f"🔧 Attempting to create route for queue {queue_id}")
            from app.apisix_gateway import create_route
            create_result = create_route(queue_id, providers_data)
            if create_result.get('success'):
                print(f"✅ Created APISIX route for queue {queue_id}")
                return True
        
        return routes_updated
        
    except Exception as e:
        print(f"❌ Error updating APISIX routes for queue {queue_id}: {e}")
        return False

@provider_bp.route('/providers', methods=['GET'])
def get_providers():
    """List all providers"""
    try:
        queue_id = request.args.get('queue_id')
        
        if queue_id:
            providers = Provider.query.filter_by(queue_id=queue_id).all()
        else:
            providers = Provider.query.all()
        
        return jsonify({
            'success': True,
            'data': [provider.to_dict() for provider in providers]
        }), 200
    except Exception as e:
        return jsonify({'message': str(e), 'success': False}), 500

@provider_bp.route('/provider/create', methods=['POST'])
def create_provider():
    """Create a new provider"""
    try:
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['queue_id', 'provider_name', 'api_key', 'limit', 'time_window']
        for field in required_fields:
            if not data.get(field):
                return jsonify({'message': f'{field} is required', 'success': False}), 400
        
        # Check if queue exists
        queue = Queue.query.filter_by(queue_id=data['queue_id']).first()
        if not queue:
            raise QueueNotFoundError(f"Queue {data['queue_id']} not found")
        
        # Create provider
        provider = Provider(
            queue_id=data['queue_id'],
            provider_name=data['provider_name'],
            provider_type=data.get('provider_type', 'openai'),
            api_key=data['api_key'],
            limit=data['limit'],
            time_window=data['time_window'],
            config=data.get('config', {})
        )
        
        db.session.add(provider)
        db.session.commit()
        
        # Update APISIX routes for the queue
        apisix_updated = update_apisix_routes_for_queue(data['queue_id'])
        
        return jsonify({
            'success': True,
            'message': 'Provider added successfully',
            'apisix_routes_updated': apisix_updated
        }), 201
    except QueueNotFoundError as e:
        return jsonify({'message': str(e), 'success': False}), 404
    except Exception as e:
        return jsonify({'message': str(e), 'success': False}), 500

@provider_bp.route('/provider/update/<provider_id>', methods=['PATCH'])
def update_provider(provider_id):
    """Update a provider"""
    try:
        data = request.get_json()
        
        provider = Provider.query.filter_by(provider_id=provider_id).first()
        if not provider:
            raise ProviderNotFoundError(f"Provider {provider_id} not found")
        
        # Update fields
        if 'queue_id' in data:
            provider.queue_id = data['queue_id']
        if 'provider_name' in data:
            provider.provider_name = data['provider_name']
        if 'api_key' in data:
            provider.api_key = data['api_key']
        if 'limit' in data:
            provider.limit = data['limit']
        if 'time_window' in data:
            provider.time_window = data['time_window']
        if 'config' in data:
            provider.config = data['config']
        
        db.session.commit()
        
        # Update APISIX routes for the queue
        apisix_updated = update_apisix_routes_for_queue(provider.queue_id)
        
        return jsonify({
            'success': True,
            'message': 'Provider updated successfully',
            'apisix_routes_updated': apisix_updated
        }), 200
    except ProviderNotFoundError as e:
        return jsonify({'message': str(e), 'success': False}), 404
    except Exception as e:
        return jsonify({'message': str(e), 'success': False}), 500

@provider_bp.route('/provider/delete/<provider_id>', methods=['DELETE'])
def delete_provider(provider_id):
    """Delete a provider"""
    try:
        provider = Provider.query.filter_by(provider_id=provider_id).first()
        if not provider:
            raise ProviderNotFoundError(f"Provider {provider_id} not found")
        
        # Store queue_id before deleting provider
        queue_id = provider.queue_id
        
        db.session.delete(provider)
        db.session.commit()
        
        # Update APISIX routes for the queue (with remaining providers)
        apisix_updated = update_apisix_routes_for_queue(queue_id)
        
        return jsonify({
            'success': True,
            'message': f'Provider {provider_id} deleted successfully',
            'apisix_routes_updated': apisix_updated
        }), 200
    except ProviderNotFoundError as e:
        return jsonify({'message': str(e), 'success': False}), 404
    except Exception as e:
        return jsonify({'message': str(e), 'success': False}), 500 