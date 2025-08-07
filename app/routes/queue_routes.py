"""
Queue routes for managing message queues
"""
from flask import Blueprint, request, jsonify
from app.services.queue_service import QueueService
from app.utils.exceptions import QueueNotFoundError, QueueAlreadyExistsError
from app.apisix_gateway import apisix_gateway

queue_bp = Blueprint('queue', __name__)

@queue_bp.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    try:
        # Check APISIX health
        apisix_healthy = apisix_gateway._check_apisix_health()
        
        return jsonify({
            'success': True,
            'status': 'healthy',
            'apisix_healthy': apisix_healthy,
            'message': 'Service is running'
        }), 200
    except Exception as e:
        return jsonify({
            'success': False,
            'status': 'unhealthy',
            'error': str(e)
        }), 500

@queue_bp.route('/queues/', methods=['GET'])
def get_queues():
    """Get all queues"""
    try:
        result = QueueService.get_all_queues()
        return jsonify(result), 200
    except Exception as e:
        return jsonify({'message': str(e), 'success': False}), 500

@queue_bp.route('/queue/<queue_id>', methods=['GET'])
def get_queue(queue_id):
    """Get queue by ID"""
    try:
        result = QueueService.get_queue(queue_id)
        return jsonify(result), 200
    except QueueNotFoundError as e:
        return jsonify({'message': str(e), 'success': False}), 404
    except Exception as e:
        return jsonify({'message': str(e), 'success': False}), 500

@queue_bp.route('/queue/create', methods=['POST'])
def create_queue():
    """Create a new queue with providers using queue_name"""
    try:
        data = request.get_json()
        queue_name = data.get('queue_name')
        providers = data.get('providers', [])
        
        if not queue_name:
            return jsonify({'message': 'queue_name is required', 'success': False}), 400
        
        if not providers:
            return jsonify({'message': 'providers list is required', 'success': False}), 400
        
        # Validate each provider has required fields
        for i, provider in enumerate(providers):
            required_fields = ['provider_name', 'api_key', 'limit', 'time_window']
            missing_fields = []
            for field in required_fields:
                if not provider.get(field):
                    missing_fields.append(field)
            
            if missing_fields:
                return jsonify({
                    'message': f'Provider {i+1} ({provider.get("provider_name", "unknown")}) is missing required fields: {", ".join(missing_fields)}',
                    'success': False
                }), 400
        
        # Create queue with queue_name
        result = QueueService.create_queue(queue_name, providers)
        
        return jsonify(result), 201
    except QueueAlreadyExistsError as e:
        return jsonify({'message': str(e), 'success': False}), 400
    except ValueError as e:
        return jsonify({'message': str(e), 'success': False}), 400
    except Exception as e:
        return jsonify({'message': str(e), 'success': False}), 500

@queue_bp.route('/queue/delete/<queue_id>', methods=['DELETE'])
def delete_queue(queue_id):
    """Delete a queue"""
    try:
        result = QueueService.delete_queue(queue_id)
        return jsonify(result), 200
    except QueueNotFoundError as e:
        return jsonify({'message': str(e), 'success': False}), 404
    except Exception as e:
        return jsonify({'message': str(e), 'success': False}), 500

@queue_bp.route('/queue/clear/<queue_id>', methods=['POST'])
def clear_queue(queue_id):
    """Clear all messages and stop workers for a queue"""
    try:
        result = QueueService.clear_queue(queue_id)
        return jsonify(result), 200
    except QueueNotFoundError as e:
        return jsonify({'message': str(e), 'success': False}), 404
    except Exception as e:
        return jsonify({'message': str(e), 'success': False}), 500 