# Filepath: app/routes/osquery/nats_utils.py
"""
Shared NATS utilities for osquery operations
"""

import asyncio
import uuid
import json
import time
import nats
import logging

from app.utilities.app_logging_helper import log_with_route

async def send_nats_command(tenantuuid: str, device_uuid: str, action: str, args: dict, user_email: str):
    """Shared function to send commands via NATS"""
    try:
        log_with_route(logging.INFO, f"[NATS] Connecting to NATS server...")
        nc = await nats.connect("tls://nats.wegweiser.tech:443")
        log_with_route(logging.INFO, f"[NATS] Connected successfully")

        request_id = str(uuid.uuid4())

        # Send command (using exact same format as working admin dashboard)
        command_subject = f"tenant.{tenantuuid}.device.{device_uuid}.command"
        command_payload = {
            'payload': {
                'command': action,
                'command_id': request_id,
                'parameters': args
            }
        }

        log_with_route(logging.INFO, f"[NATS] Publishing to subject: {command_subject}")
        log_with_route(logging.INFO, f"[NATS] Payload: {json.dumps(command_payload)}")
        log_with_route(logging.INFO, f"[NATS] Request ID: {request_id}")

        await nc.publish(command_subject, json.dumps(command_payload).encode())
        log_with_route(logging.INFO, f"[NATS] Command published successfully")

        # Listen for response
        response_subject = f"tenant.{tenantuuid}.device.{device_uuid}.response"
        log_with_route(logging.INFO, f"[NATS] Subscribing to response subject: {response_subject}")

        response_received = asyncio.Event()
        response_data = {}

        async def response_handler(msg):
            nonlocal response_data
            try:
                log_with_route(logging.INFO, f"[NATS] Response received on {msg.subject}")
                data = json.loads(msg.data.decode())
                log_with_route(logging.INFO, f"[NATS] Response data: {json.dumps(data)}")
                log_with_route(logging.INFO, f"[NATS] Looking for command_id: {request_id}")
                log_with_route(logging.INFO, f"[NATS] Response has command_id: {data.get('command_id')}")

                # Check if this is a response to our command
                if data.get('command_id') == request_id:
                    log_with_route(logging.INFO, f"[NATS] Command ID matches! Setting response")
                    response_data = data
                    response_received.set()
                else:
                    log_with_route(logging.WARNING, f"[NATS] Command ID mismatch - Expected: {request_id}, Got: {data.get('command_id')}")
                    # Also check nested result
                    if 'result' in data and isinstance(data['result'], dict):
                        nested_id = data['result'].get('command_id')
                        log_with_route(logging.INFO, f"[NATS] Checking nested command_id: {nested_id}")
                        if nested_id == request_id:
                            log_with_route(logging.INFO, f"[NATS] Nested command ID matches! Setting response")
                            response_data = data
                            response_received.set()
            except Exception as e:
                log_with_route(logging.ERROR, f"[NATS] Error parsing response: {e}")

        # Subscribe to response
        sub = await nc.subscribe(response_subject, cb=response_handler)
        log_with_route(logging.INFO, f"[NATS] Subscribed to response, waiting for reply (30s timeout)...")

        # Wait for response with timeout
        try:
            await asyncio.wait_for(response_received.wait(), timeout=30.0)
            log_with_route(logging.INFO, f"[NATS] Response received successfully")
            await sub.unsubscribe()
            return response_data.get('result', response_data)
        except asyncio.TimeoutError:
            log_with_route(logging.ERROR, f"[NATS] Timeout waiting for response from device")
            await sub.unsubscribe()
            return {'error': 'Command timeout - agent did not respond'}
        finally:
            await nc.close()
            log_with_route(logging.INFO, f"[NATS] Connection closed")

    except Exception as e:
        log_with_route(logging.ERROR, f"[NATS] Command error: {str(e)}")
        import traceback
        log_with_route(logging.ERROR, f"[NATS] Traceback: {traceback.format_exc()}")
        return {'error': f'Command failed: {str(e)}'}

def execute_async_command(coro):
    """Execute async command with proper event loop handling"""
    try:
        loop = asyncio.get_event_loop()
        if loop.is_closed():
            raise RuntimeError("Event loop is closed")
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    
    try:
        result = loop.run_until_complete(coro)
    except Exception as e:
        log_with_route(logging.ERROR, f"Event loop error: {str(e)}")
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            result = loop.run_until_complete(coro)
        finally:
            loop.close()
    finally:
        if not loop.is_running():
            loop.close()
    
    return result
