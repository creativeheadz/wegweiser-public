#!/usr/bin/env python3
"""
Wegweiser NATS Receiver Runner

Starts the always-on NATS listeners independent of Gunicorn:
- Tenant-scoped NATSMessageService (heartbeat/status/monitoring/response)
- Demo SystemMetricsHandler (demo.system.*.*)

This runner expects to be launched by systemd with an environment file
that sets APP_HOME, VENV_PYTHON, PYTHONPATH, etc.
"""

import asyncio
import logging
import os
import signal
import sys

# Ensure repo root is importable when run by systemd
APP_HOME = os.environ.get("APP_HOME", os.getcwd())
if APP_HOME not in sys.path:
    sys.path.insert(0, APP_HOME)

from app import create_app
from app.utilities.app_logging_helper import log_with_route
from app.handlers.nats.message_handlers import nats_message_service
from app.handlers.nats_demo.system_metrics import system_metrics_handler

logger = logging.getLogger("nats_receiver_runner")
logging.basicConfig(level=logging.WARNING, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')


async def _start_services():
    """Start both NATS services as background tasks and keep alive."""
    log_with_route(logging.INFO, "Starting NATSMessageService and SystemMetricsHandler")
    # Start as background tasks
    msg_task = asyncio.create_task(nats_message_service.start_message_processing())
    demo_task = asyncio.create_task(system_metrics_handler.start_monitoring())

    # Monitor tasks
    try:
        while True:
            await asyncio.sleep(5)
            # Log if any task crashed
            if msg_task.done():
                exc = msg_task.exception()
                if exc:
                    log_with_route(logging.ERROR, f"NATSMessageService task error: {exc}")
                # Attempt restart
                msg_task = asyncio.create_task(nats_message_service.start_message_processing())
                log_with_route(logging.WARNING, "Restarted NATSMessageService task")

            if demo_task.done():
                exc = demo_task.exception()
                if exc:
                    log_with_route(logging.ERROR, f"SystemMetricsHandler task error: {exc}")
                # Attempt restart
                demo_task = asyncio.create_task(system_metrics_handler.start_monitoring())
                log_with_route(logging.WARNING, "Restarted SystemMetricsHandler task")
    except asyncio.CancelledError:
        log_with_route(logging.INFO, "Shutdown requested; cancelling tasks...")
        for t in (msg_task, demo_task):
            if not t.done():
                t.cancel()
        await asyncio.gather(msg_task, demo_task, return_exceptions=True)


def main():
    log_with_route(logging.INFO, "NATS Receiver Runner starting up...")
    app = create_app()

    # Graceful shutdown via signals
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    stop_event = asyncio.Event()

    def _signal_handler(signum, frame):
        log_with_route(logging.INFO, f"Received signal {signum}, shutting down...")
        loop.call_soon_threadsafe(stop_event.set)

    for s in (signal.SIGINT, signal.SIGTERM):
        signal.signal(s, _signal_handler)

    try:
        with app.app_context():
            loop.create_task(_start_services())
            loop.run_until_complete(stop_event.wait())
    finally:
        try:
            loop.run_until_complete(asyncio.sleep(0.1))
        except Exception:
            pass
        loop.close()
        log_with_route(logging.INFO, "NATS Receiver Runner stopped.")


if __name__ == "__main__":
    main()

