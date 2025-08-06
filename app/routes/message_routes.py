"""
Message routes for processing AI requests
"""
from flask import Blueprint, request, jsonify
from app.services.message_service import MessageService
from app.utils.exceptions import QueueNotFoundError, MessageNotFoundError

message_bp = Blueprint('message', __name__)

@message_bp.route('/message/create', methods=['POST'])
def create_message():
    """Create messages with batch_id and message_id generation - supports single message or batch of messages"""
    try:
        data = request.get_json()
        
        # Validate required fields
        if not data.get('queue_id'):
            return jsonify({'message': 'queue_id is required', 'success': False}), 400
        
        # Check if it's a single message or batch of messages
        if 'prompt' in data:
            # Single message
            if not data.get('prompt'):
                return jsonify({'message': 'prompt is required', 'success': False}), 400
            
            result = MessageService.create_message(data)
        elif 'messages' in data:
            # Batch of messages
            if not data.get('messages'):
                return jsonify({'message': 'messages list is required', 'success': False}), 400
            
            result = MessageService.create_batch_messages(data)
        else:
            return jsonify({'message': 'Either prompt (single message) or messages (batch) is required', 'success': False}), 400
        
        return jsonify(result), 201
    except QueueNotFoundError as e:
        return jsonify({
            'message': str(e),
            'registration_required': True,
            'success': False
        }), 404
    except Exception as e:
        return jsonify({'message': str(e), 'success': False}), 500

@message_bp.route('/message/read/<message_id>', methods=['GET'])
def read_message(message_id):
    """Read a message by message_id"""
    try:
        result = MessageService.get_message(message_id)
        return jsonify(result), 200
    except MessageNotFoundError as e:
        return jsonify({'message': str(e), 'success': False}), 404
    except Exception as e:
        return jsonify({'message': str(e), 'success': False}), 500

@message_bp.route('/message/delete/<message_id>', methods=['DELETE'])
def delete_message(message_id):
    """Delete a message by message_id"""
    try:
        result = MessageService.delete_message(message_id)
        return jsonify(result), 200
    except MessageNotFoundError as e:
        return jsonify({'message': str(e), 'success': False}), 404
    except Exception as e:
        return jsonify({'message': str(e), 'success': False}), 500

@message_bp.route('/batch/<batch_id>/messages', methods=['GET'])
def get_batch_messages(batch_id):
    """Get all messages for a batch"""
    try:
        result = MessageService.get_batch_messages(batch_id)
        return jsonify(result), 200
    except Exception as e:
        return jsonify({'message': str(e), 'success': False}), 500

@message_bp.route('/batch/<batch_id>/results', methods=['GET'])
def get_batch_results(batch_id):
    """Get batch results (CSV or JSON)"""
    try:
        from app.services.redis_service import RedisService
        
        # Get results from Redis
        results = RedisService.get_batch_results(batch_id)
        if not results:
            return jsonify({'message': 'Batch results not found', 'success': False}), 404
        
        # Check format parameter
        format_type = request.args.get('format', 'json')
        
        if format_type == 'csv':
            import csv
            import io
            
            output = io.StringIO()
            writer = csv.writer(output)
            
            # Write header
            writer.writerow(['message_id', 'status', 'prompt', 'result', 'error_message'])
            
            # Write data
            for result in results.get('results', []):
                writer.writerow([
                    result.get('message_id'),
                    result.get('status'),
                    result.get('prompt', ''),
                    result.get('result', ''),
                    result.get('error_message', '')
                ])
            
            from flask import Response
            return Response(
                output.getvalue(),
                mimetype='text/csv',
                headers={'Content-Disposition': f'attachment; filename=batch_{batch_id}.csv'}
            )
        else:
            return jsonify({
                'success': True,
                'data': results
            }), 200
            
    except Exception as e:
        return jsonify({'message': str(e), 'success': False}), 500 