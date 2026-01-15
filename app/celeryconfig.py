# Filepath: app/celeryconfig.py
from celery import Celery
from app.utilities.app_logging_helper import log_with_route, LogLevelFilter
from flask import request, current_app, has_request_context
import logging
import os
from celery.schedules import crontab
from logging.handlers import RotatingFileHandler

def make_celery(app):
   celery = Celery(
       app.import_name,
       backend=app.config['result_backend'],
       broker=app.config['broker_url']  # Match the new name
   )

   # Update Celery config from Flask config
   celery.conf.update(app.config)

   # Required settings for reliable task processing
   celery.conf.update({
       'broker_url': app.config['broker_url'],
       'result_backend': app.config['result_backend'],
       'broker_connection_retry_on_startup': True,
       'worker_prefetch_multiplier': 1,
       'worker_max_tasks_per_child': 1,
       'task_acks_late': True,
       'task_reject_on_worker_lost': True,
       'task_time_limit': None,
       'task_soft_time_limit': None,
       'result_expires': 3600,
       'result_backend_transport_options': {'visibility_timeout': 3600},
       'task_track_started': True,
       'task_default_queue': 'celery',
       'task_default_exchange': 'celery',
       'task_default_routing_key': 'celery',
       'timezone': 'UTC',
       'enable_utc': True,
       'task_serializer': 'json',
       'accept_content': ['json'],
       'result_serializer': 'json',
       'worker_log_format': '[%(asctime)s: %(levelname)s/%(processName)s] %(message)s',
       'worker_task_log_format': '[%(asctime)s: %(levelname)s/%(processName)s] [%(task_name)s(%(task_id)s)] %(message)s'
   })

   class FlaskContextTask(celery.Task):
       abstract = True
       
       def __call__(self, *args, **kwargs):
           with app.app_context():
               if has_request_context():
                   log_with_route(logging.INFO, 
                       f'Task {self.name} started with args: {args} kwargs: {kwargs}', 
                       route=request.path)
               else:
                   log_with_route(logging.INFO, 
                       f'Task {self.name} started with args: {args} kwargs: {kwargs}')
               
               try:
                   result = self.run(*args, **kwargs)
                   if has_request_context():
                       log_with_route(logging.INFO, 
                           f'Task {self.name} completed with result: {result}', 
                           route=request.path)
                   else:
                       log_with_route(logging.INFO, 
                           f'Task {self.name} completed with result: {result}')
                   return result
               except Exception as e:
                   if has_request_context():
                       log_with_route(logging.ERROR, 
                           f'Task {self.name} failed with error: {str(e)}', 
                           route=request.path)
                   else:
                       log_with_route(logging.ERROR, 
                           f'Task {self.name} failed with error: {str(e)}')
                   raise

   celery.Task = FlaskContextTask

   # Configure Celery logging to respect logging_config.json
   def setup_celery_logging():
       """Configure Celery logging with rotation and level filtering"""
       celery_log_dir = 'wlog'
       celery_log_file = os.path.join(celery_log_dir, 'celery.log')

       # Ensure log directory exists
       if not os.path.exists(celery_log_dir):
           os.makedirs(celery_log_dir)

       # Get Celery's root logger
       celery_logger = logging.getLogger('celery')
       celery_logger.setLevel(logging.DEBUG)

       # Remove existing handlers to avoid duplicates
       for handler in celery_logger.handlers[:]:
           celery_logger.removeHandler(handler)

       # Add rotating file handler for Celery (15MB rollover)
       celery_handler = RotatingFileHandler(
           celery_log_file,
           maxBytes=15728640,  # 15MB
           backupCount=10,
           delay=False
       )
       celery_handler.setFormatter(logging.Formatter(
           '[%(asctime)s: %(levelname)s/%(name)s] %(message)s'
       ))
       # Apply LogLevelFilter to respect logging_config.json
       celery_handler.addFilter(LogLevelFilter())
       celery_logger.addHandler(celery_handler)
       celery_logger.propagate = False

   # Setup logging when celery is initialized
   setup_celery_logging()

   return celery