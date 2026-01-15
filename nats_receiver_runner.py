#!/usr/bin/env python3
"""
Wegweiser NATS Receiver Runner

Always-on background process to subscribe to NATS demo/system subjects
and feed Redis buffers for the UI charts. Decoupled from Gunicorn/Flask
workers so charts keep working regardless of web app restarts.

- Initializes Flask app context for DB access (Tenants query)
- Starts SystemMetricsHandler subscription
- Runs an asyncio loop until terminated
"""
import asyncio
import logging
import os
import signal
import sys
from logging.handlers import RotatingFileHandler

# Ensure we can import the app
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)

# Configure logging early
LOG_DIR = os.path.join(SCRIPT_DIR, 'wlog')
os.makedirs(LOG_DIR, exist_ok=True)
LOG_PATH = os.path.join(LOG_DIR, 'wegweiser.log')

logger = logging.getLogger('nats_receiver_runner')
logger.setLevel(logging.INFO)

_formatter = logging.Formatter('%(asctime)s | %(levelname)-8s | %(name)-30s | %(message)s')
_file = RotatingFileHandler(LOG_PATH, maxBytes=5*1024*1024, backupCount=3)
_file.setFormatter(_formatter)
_stream = logging.StreamHandler(sys.stdout)
_stream.setFormatter(_formatter)

root_logger = logging.getLogger()
root_logger.setLevel(logging.INFO)
root_logger.addHandler(_file)
root_logger.addHandler(_stream)

# Import after logging setup
from app import create_app
from app.utilities.app_logging_helper import log_with_route
from app.handlers.nats_demo.system_metrics import system_metrics_handler


async def main_async(app):
    # Start system metrics monitoring (subscribes to demo.system.*.*)
    await system_metrics_handler.start_monitoring()
    # Keep running
    while True:
        await asyncio.sleep(5)


def main():
    log_with_route(logging.INFO, 'Starting Wegweiser NATS Receiver Runner')

    # Build Flask app and push app context
    app = create_app()
    ctx = app.app_context()
    ctx.push()

    # Handle graceful shutdown
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    stop_event = asyncio.Event()

    def _signal_handler(signum, frame):
        log_with_route(logging.INFO, f'Received signal {signum}, shutting down...')
        loop.call_soon_threadsafe(stop_event.set)

    signal.signal(signal.SIGINT, _signal_handler)
    signal.signal(signal.SIGTERM, _signal_handler)

    async def runner():
        task = asyncio.create_task(main_async(app))
        await stop_event.wait()
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass

    try:
        loop.run_until_complete(runner())
    finally:
        # Cleanup
        try:
            loop.run_until_complete(system_metrics_handler.stop())
        except Exception:
            pass
        loop.close()
        ctx.pop()
        log_with_route(logging.INFO, 'Wegweiser NATS Receiver Runner stopped')


if __name__ == '__main__':
    main()
