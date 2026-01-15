# Filepath: gunicorn.conf.py
import multiprocessing
import os

# Basic config
bind = "unix:/opt/wegweiser/wegweiser.sock"
workers = 4  # Restored to original multi-worker configuration
worker_class = "sync"  # Restored to original sync worker
timeout = 120
graceful_timeout = 30  # Time to finish processing requests during restart
keepalive = 5  # How long to wait for requests on a Keep-Alive connection
max_requests = 1000  # Restart workers after handling this many requests
max_requests_jitter = 200  # Add randomness to max_requests to avoid all workers restarting at once
umask = 7

# Logging
accesslog = None  # Disable access logging to reduce log volume
errorlog = "/opt/wegweiser/wlog/gunicorn_error.log"
loglevel = "error"

# Process naming
proc_name = "wegweiser_app"

# Security
limit_request_line = 4094
limit_request_fields = 100
limit_request_field_size = 8190