# Filepath: app/utilities/sys_function_process_payloads.py
import os
import requests
import logging
from flask import current_app
from dotenv import load_dotenv
from app.utilities.app_logging_helper import log_with_route
from ..extensions import celery

# Load environment variables
load_dotenv()

def call_processpayloads_url():
    url = 'https://app.wegweiser.tech/payload/processpayloads'

    try:
        # Add timeout to prevent hanging indefinitely
        response = requests.get(url, timeout=30)
        if response.status_code == 200:
            log_with_route(logging.INFO, f'Successfully called {url}: {response.json()}', source_type="Celery Task")
        else:
            log_with_route(logging.ERROR, f'Failed to call {url}: {response.status_code} - {response.text}', source_type="Celery Task")
    except requests.exceptions.Timeout:
        log_with_route(logging.ERROR, f'Timeout occurred while calling {url} (30 seconds)', source_type="Celery Task")
    except Exception as e:
        log_with_route(logging.ERROR, f'Exception occurred while calling {url}: {e}', exc_info=True, source_type="Celery Task")


@celery.task
def call_processpayloads_task():
    with current_app.app_context():
        log_with_route(logging.INFO, 'Starting the process payloads task', source_type="Celery Task")
        try:
            call_processpayloads_url()
            log_with_route(logging.INFO, 'Successfully completed the process payloads task', source_type="Celery Task")
        except Exception as e:
            log_with_route(logging.ERROR, f'Error occurred in process payloads task: {e}', exc_info=True, source_type="Celery Task")
