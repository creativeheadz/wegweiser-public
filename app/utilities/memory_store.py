# Filepath: app/utilities/memory_store.py

import redis
from typing import Dict, List, Any, Optional
import json
import time
from app.config.memory_store import MemoryStoreConfig
from app.utilities.app_logging_helper import log_with_route
import logging

class MemoryStore:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(MemoryStore, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        if not hasattr(self, '_initialized'):
            try:
                self.redis_client = redis.Redis(
                    host=MemoryStoreConfig.REDIS_HOST,
                    port=MemoryStoreConfig.REDIS_PORT,
                    password=MemoryStoreConfig.REDIS_PASSWORD,
                    decode_responses=MemoryStoreConfig.REDIS_DECODE_RESPONSES
                )
                self._initialized = True
            except Exception as e:
                log_with_route(logging.ERROR, f"Failed to initialize Redis: {str(e)}")
                raise

    def get_conversation_key(self, conversation_uuid: str) -> str:
        """Generate Redis key for conversation"""
        return f"chat:conversation:{conversation_uuid}"
    
    def store_conversation_context(self, conversation_uuid: str, context: Dict[str, Any]):
        """Store recent conversation context in Redis"""
        try:
            key = self.get_conversation_key(conversation_uuid)
            self.redis_client.setex(
                key,
                MemoryStoreConfig.CONVERSATION_TTL,  # 5 days
                json.dumps(context)
            )
        except Exception as e:
            log_with_route(logging.ERROR, f"Error storing conversation context: {str(e)}")

    def get_conversation_context(self, conversation_uuid: str) -> Optional[Dict[str, Any]]:
        """Get recent conversation context from Redis"""
        try:
            key = self.get_conversation_key(conversation_uuid)
            data = self.redis_client.get(key)
            if data:
                # Refresh TTL when accessed
                self.redis_client.expire(key, MemoryStoreConfig.CONVERSATION_TTL)
                return json.loads(data)
            return None
        except Exception as e:
            log_with_route(logging.ERROR, f"Error getting conversation context: {str(e)}")
            return None

    def clear_conversation(self, conversation_uuid: str):
        """Clear conversation context from Redis"""
        try:
            key = self.get_conversation_key(conversation_uuid)
            self.redis_client.delete(key)
        except Exception as e:
            log_with_route(logging.ERROR, f"Error clearing conversation: {str(e)}")

    def health_check(self) -> Dict[str, Any]:
        """Check health of memory store (Redis)"""
        try:
            # Test Redis connection
            self.redis_client.ping()

            # Get Redis info
            info = self.redis_client.info()

            return {
                'status': 'healthy',
                'redis_version': info.get('redis_version', 'unknown'),
                'used_memory_mb': round(info.get('used_memory', 0) / 1024 / 1024, 2),
                'connected_clients': info.get('connected_clients', 0),
                'uptime_seconds': info.get('uptime_in_seconds', 0)
            }
        except Exception as e:
            log_with_route(logging.ERROR, f"Memory store health check failed: {str(e)}")
            return {
                'status': 'unhealthy',
                'error': str(e)
            }