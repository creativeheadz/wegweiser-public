# Filepath: app/config/redis_config.py
from redis import Redis
from flask import current_app
import json

class RedisConfig:
    HOST = "10.0.0.6"  # Your Redis host
    PORT = 6379
    DB = 0
    DECODE_RESPONSES = True
    SOCKET_TIMEOUT = 5
    SOCKET_CONNECT_TIMEOUT = 5

class RedisClient:
    _instance = None

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = Redis(
                host=RedisConfig.HOST,
                port=RedisConfig.PORT,
                db=RedisConfig.DB,
                decode_responses=RedisConfig.DECODE_RESPONSES,
                socket_timeout=RedisConfig.SOCKET_TIMEOUT,
                socket_connect_timeout=RedisConfig.SOCKET_CONNECT_TIMEOUT
            )
        return cls._instance

    @classmethod
    def set_json(cls, key: str, value: dict, expiry: int = None):
        client = cls.get_instance()
        try:
            json_data = json.dumps(value)
            if expiry:
                client.setex(key, expiry, json_data)
            else:
                client.set(key, json_data)
            return True
        except Exception as e:
            current_app.logger.error(f"Redis set error: {str(e)}")
            return False

    @classmethod
    def get_json(cls, key: str):
        client = cls.get_instance()
        try:
            data = client.get(key)
            return json.loads(data) if data else None
        except Exception as e:
            current_app.logger.error(f"Redis get error: {str(e)}")
            return None