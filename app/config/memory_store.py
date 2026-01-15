# Filepath: app/config/memory_store.py

class MemoryStoreConfig:
    # Redis connection settings
    REDIS_HOST = "10.0.0.6"
    REDIS_PORT = 6379
    REDIS_PASSWORD = None
    REDIS_DECODE_RESPONSES = True
    
    # Memory retention settings
    CONVERSATION_TTL = 432000  # 5 days in seconds
    MAX_MESSAGES_PER_CONVERSATION = 1000
    IMPORTANCE_THRESHOLD = 0.7
    
    # Entity memory keys format
    MEMORY_KEY_FORMAT = {
        'device': 'memory:device:{}',
        'group': 'memory:group:{}',
        'organisation': 'memory:org:{}',
        'tenant': 'memory:tenant:{}'
    }
    
    # Chat context settings
    MAX_CONTEXT_MESSAGES = 10  # Number of recent messages to keep in immediate context
    MAX_CONTEXT_AGE = 432000  # How old context messages can be (5 days)