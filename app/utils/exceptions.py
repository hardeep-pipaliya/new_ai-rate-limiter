"""
Custom exceptions for the AI Rate Limiter application
"""

class AIRateLimiterError(Exception):
    """Base exception for AI Rate Limiter"""
    pass

class QueueNotFoundError(AIRateLimiterError):
    """Raised when queue is not found"""
    pass

class QueueAlreadyExistsError(AIRateLimiterError):
    """Raised when queue already exists"""
    pass

class MessageNotFoundError(AIRateLimiterError):
    """Raised when message is not found"""
    pass

class ProviderNotFoundError(AIRateLimiterError):
    """Raised when provider is not found"""
    pass

class WorkerNotFoundError(AIRateLimiterError):
    """Raised when worker is not found"""
    pass

class BatchNotFoundError(AIRateLimiterError):
    """Raised when batch is not found"""
    pass

class RateLimitExceededError(AIRateLimiterError):
    """Raised when rate limit is exceeded"""
    pass

class RedisError(AIRateLimiterError):
    """Raised when Redis operation fails"""
    pass

class RabbitMQError(AIRateLimiterError):
    """Raised when RabbitMQ operation fails"""
    pass 