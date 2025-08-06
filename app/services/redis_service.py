"""
Redis service for caching and batch tracking
"""
import json
import redis
from typing import Dict, Any, Optional
from app.config.config import Config

class RedisService:
    """Service for Redis operations"""
    
    _redis_client = None
    
    @classmethod
    def get_client(cls):
        """Get Redis client"""
        if cls._redis_client is None:
            cls._redis_client = redis.from_url(Config.REDIS_URL)
        return cls._redis_client
    
    @classmethod
    def init_batch_counters(cls, batch_id: str, message_count: int) -> None:
        """Initialize batch counters in Redis"""
        client = cls.get_client()
        client.hset(f"batch:{batch_id}", "req.count", message_count)
        client.hset(f"batch:{batch_id}", "res.count", 0)
    
    @classmethod
    def increment_batch_response(cls, batch_id: str) -> int:
        """Increment batch response counter"""
        client = cls.get_client()
        return client.hincrby(f"batch:{batch_id}", "res.count", 1)
    
    @classmethod
    def get_batch_counters(cls, batch_id: str) -> Dict[str, int]:
        """Get batch counters"""
        client = cls.get_client()
        data = client.hgetall(f"batch:{batch_id}")
        return {
            'request_count': int(data.get(b'req.count', 0)),
            'response_count': int(data.get(b'res.count', 0))
        }
    
    @classmethod
    def store_message_result(cls, message_id: str, result: Dict[str, Any]) -> None:
        """Store message result in Redis"""
        client = cls.get_client()
        client.setex(f"message:{message_id}", 3600, json.dumps(result))  # 1 hour TTL
    
    @classmethod
    def get_message_result(cls, message_id: str) -> Optional[Dict[str, Any]]:
        """Get message result from Redis"""
        client = cls.get_client()
        data = client.get(f"message:{message_id}")
        return json.loads(data) if data else None
    
    @classmethod
    def store_batch_results(cls, batch_id: str, results: Dict[str, Any]) -> None:
        """Store batch results in Redis"""
        client = cls.get_client()
        client.setex(f"batch_results:{batch_id}", 86400, json.dumps(results))  # 24 hours TTL
    
    @classmethod
    def get_batch_results(cls, batch_id: str) -> Optional[Dict[str, Any]]:
        """Get batch results from Redis"""
        client = cls.get_client()
        data = client.get(f"batch_results:{batch_id}")
        return json.loads(data) if data else None 