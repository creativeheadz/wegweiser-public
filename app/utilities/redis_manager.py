# Filepath: app/utilities/redis_manager.py

from flask import current_app
import redis
from contextlib import contextmanager
import logging
from typing import Optional, Dict, List, Any, Union
import json
from app.utilities.app_logging_helper import log_with_route
import time
import backoff

class RedisError(Exception):
    """Base exception for Redis operations"""
    pass

class RedisConnectionError(RedisError):
    """Raised when Redis connection fails"""
    pass

class RedisOperationError(RedisError):
    """Raised when a Redis operation fails"""
    pass

class RedisManager:
    """Singleton Redis manager with connection pooling and error handling"""
    
    _instance = None
    _redis_client = None
    _initialized = False  # Track initialization state
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        pass  # Initialization happens lazily in `_initialize`

    def _initialize(self):
        """Initialize Redis connection and configuration"""
        if self._initialized:
            return
        
        try:
            config = current_app.config['REDIS_CONFIG']
            self.prefixes = current_app.config['REDIS_PREFIXES']
            self.ttl = current_app.config['REDIS_TTL']
            
            # Create connection pool
            pool = redis.ConnectionPool(
                host=config['host'],
                port=config['port'],
                password=config.get('password'),
                db=config['db'],
                socket_timeout=config.get('socket_timeout'),
                retry_on_timeout=config.get('retry_on_timeout', False),
                max_connections=100,
                health_check_interval=30
            )
            
            self._redis_client = redis.Redis(connection_pool=pool)
            
            # Test connection
            self._redis_client.ping()
            log_with_route(logging.INFO, "Redis connection initialized successfully")
            
            self._initialized = True
            
        except Exception as e:
            log_with_route(logging.ERROR, f"Failed to initialize Redis: {str(e)}")
            raise RedisConnectionError(f"Redis initialization failed: {str(e)}")
    
    @property
    def client(self):
        """Get Redis client with connection check"""
        if not self._initialized:
            self._initialize()
        return self._redis_client
    
    # All other methods remain unchanged

    
    def key(self, prefix: str, *parts: str) -> str:
        """Generate Redis key with prefix"""
        base = self.prefixes.get(prefix, 'wegweiser')
        return ':'.join([base, *parts])
    
    @contextmanager
    def pipeline(self):
        """Get Redis pipeline with error handling"""
        pipe = self.client.pipeline()
        try:
            yield pipe
            pipe.execute()
        except redis.RedisError as e:
            log_with_route(logging.ERROR, f"Redis pipeline error: {str(e)}")
            pipe.reset()
            raise RedisOperationError(f"Pipeline operation failed: {str(e)}")
    
    @backoff.on_exception(
        backoff.expo,
        (redis.RedisError, RedisOperationError),
        max_tries=3,
        max_time=10
    )
    def set_json(self, key: str, data: Any, ttl: Optional[int] = None) -> bool:
        """Set JSON data with retry"""
        try:
            serialized = json.dumps(data)
            result = self.client.set(key, serialized, ex=ttl)
            return bool(result)
        except (TypeError, json.JSONDecodeError) as e:
            log_with_route(logging.ERROR, f"JSON serialization error: {str(e)}")
            raise RedisOperationError(f"Failed to serialize data: {str(e)}")
        except redis.RedisError as e:
            log_with_route(logging.ERROR, f"Redis set error: {str(e)}")
            raise
    
    @backoff.on_exception(
        backoff.expo,
        (redis.RedisError, RedisOperationError),
        max_tries=3,
        max_time=10
    )
    def get_json(self, key: str) -> Optional[Any]:
        """Get JSON data with retry"""
        try:
            data = self.client.get(key)
            if data is None:
                return None
            return json.loads(data)
        except json.JSONDecodeError as e:
            log_with_route(logging.ERROR, f"JSON deserialization error: {str(e)}")
            raise RedisOperationError(f"Failed to deserialize data: {str(e)}")
        except redis.RedisError as e:
            log_with_route(logging.ERROR, f"Redis get error: {str(e)}")
            raise
    
    def update_tenant_settings(self, tenant_id: str, 
                             settings: Dict[str, Any]) -> bool:
        """Update tenant analysis settings"""
        key = self.key('tenant', str(tenant_id), 'settings')
        return self.set_json(key, settings)
    
    def get_tenant_settings(self, tenant_id: str) -> Optional[Dict[str, Any]]:
        """Get tenant analysis settings"""
        key = self.key('tenant', str(tenant_id), 'settings')
        return self.get_json(key)
    
    def queue_analysis(self, analysis_type: str, data: Dict[str, Any]) -> bool:
        """Queue an analysis task"""
        key = self.key('analysis', 'queue', analysis_type)
        return self.client.rpush(key, json.dumps(data))
    
    def get_queued_analyses(self, analysis_type: str, 
                           count: int = 10) -> List[Dict[str, Any]]:
        """Get queued analyses of a type"""
        key = self.key('analysis', 'queue', analysis_type)
        items = self.client.lrange(key, 0, count - 1)
        return [json.loads(item) for item in items]
    
    def remove_from_queue(self, analysis_type: str, 
                         data: Dict[str, Any]) -> bool:
        """Remove an item from the analysis queue"""
        key = self.key('analysis', 'queue', analysis_type)
        serialized = json.dumps(data)
        return bool(self.client.lrem(key, 1, serialized))
    
    def cleanup_expired(self):
        """Cleanup expired keys"""
        try:
            for prefix in self.prefixes.values():
                pattern = f"{prefix}:*"
                cursor = 0
                while True:
                    cursor, keys = self.client.scan(
                        cursor=cursor, 
                        match=pattern, 
                        count=100
                    )
                    for key in keys:
                        if not self.client.ttl(key):
                            self.client.delete(key)
                    if cursor == 0:
                        break
        except redis.RedisError as e:
            log_with_route(logging.ERROR, f"Cleanup error: {str(e)}")
            raise RedisOperationError(f"Cleanup failed: {str(e)}")

# Global instance
redis_manager = RedisManager()