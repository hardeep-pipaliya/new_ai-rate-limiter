"""
Worker routes for managing Celery workers
"""
import os
import subprocess
import psutil
import uuid
from flask import Blueprint, request, jsonify
from app import db
from app.models.worker import Worker
from app.models.queue import Queue
from app.utils.exceptions import WorkerNotFoundError, QueueNotFoundError

worker_bp = Blueprint('worker', __name__)

@worker_bp.route('/worker/create/<queue_id>', methods=['POST'])
def create_worker(queue_id):
    """Create and start worker process"""
    try:
        data = request.get_json() or {}
        count = data.get('count', 1)
        
        # Handle special case for batch_aggregator
        if queue_id == 'batch_aggregator':
            # Create a virtual queue for batch aggregator
            queue = Queue(
                queue_id=uuid.uuid4(),
                queue_name='batch_aggregator'
            )
            db.session.add(queue)
            db.session.commit()
        else:
            # Check if queue exists
            queue = Queue.query.filter_by(queue_id=queue_id).first()
            if not queue:
                raise QueueNotFoundError(f"Queue {queue_id} not found")
        
        # Get existing workers for this queue
        existing_workers = Worker.query.filter_by(queue_id=queue_id).all()
        previous_count = len(existing_workers)
        
        # Start new workers
        new_workers = []
        for i in range(count):
            # Start Celery worker process
            cmd = [
                'celery', '-A', 'app.celery', 'worker',
                '--loglevel=info',
                '--queues=' + queue_id,
                '--hostname=worker@%h'
            ]
            
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                preexec_fn=os.setsid
            )
            
            # Create worker record - use queue.queue_id for batch_aggregator
            worker_queue_id = queue.queue_id if queue_id == 'batch_aggregator' else queue_id
            worker = Worker(
                queue_id=worker_queue_id,
                pid=process.pid,
                status='running',
                log_file=f'worker_{process.pid}.log'
            )
            
            db.session.add(worker)
            new_workers.append(worker)
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'queue_id': queue_id,
            'previous_count': previous_count,
            'current_count': previous_count + count,
            'target_count': count,
            'workers_added': count,
            'workers_removed': 0,
            'workers': [w.to_dict() for w in new_workers]
        }), 200
    except QueueNotFoundError as e:
        return jsonify({'message': str(e), 'success': False}), 404
    except Exception as e:
        return jsonify({'message': str(e), 'success': False}), 500

@worker_bp.route('/worker/logs/<worker_id>', methods=['GET'])
def get_worker_logs(worker_id):
    """Get worker logs"""
    try:
        worker = Worker.query.filter_by(worker_id=worker_id).all()
        if not worker:
            raise WorkerNotFoundError(f"Worker {worker_id} not found")
        
        return jsonify({
            'data': [w.to_dict() for w in worker]
        }), 200
    except WorkerNotFoundError as e:
        return jsonify({'message': str(e), 'success': False}), 404
    except Exception as e:
        return jsonify({'message': str(e), 'success': False}), 500

@worker_bp.route('/worker/delete/<worker_id>', methods=['DELETE'])
def delete_worker(worker_id):
    """Delete a worker"""
    try:
        worker = Worker.query.filter_by(worker_id=worker_id).first()
        if not worker:
            raise WorkerNotFoundError(f"Worker {worker_id} not found")
        
        # Kill the process
        try:
            process = psutil.Process(worker.pid)
            process.terminate()
            process.wait(timeout=5)
        except (psutil.NoSuchProcess, psutil.TimeoutExpired):
            # Process already dead or not responding
            pass
        
        # Delete worker record
        db.session.delete(worker)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'Worker {worker_id} deleted successfully',
            'worker_id': worker_id
        }), 200
    except WorkerNotFoundError as e:
        return jsonify({'message': str(e), 'success': False}), 404
    except Exception as e:
        return jsonify({'message': str(e), 'success': False}), 500 