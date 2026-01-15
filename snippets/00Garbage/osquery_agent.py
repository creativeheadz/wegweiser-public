# Filepath: snippets/unSigned/osquery_agent.py
# Agent script for handling osquery commands

import json
import logging
import os
import platform
import subprocess
import sys
import time
import uuid
import websocket
import ssl
import requests
from threading import Thread

# Configure logging
import logzero
from logzero import logger

# Set up logging
log_dir = os.path.join('c:\\program files (x86)\\Wegweiser\\Logs\\' if platform.system() == 'Windows' else '/var/log/Wegweiser/', 'osquery')
os.makedirs(log_dir, exist_ok=True)
log_file = os.path.join(log_dir, 'osquery_agent.log')
logzero.logfile(log_file, maxBytes=1e6, backupCount=3)
logger.info("Starting osquery agent")

def get_device_uuid():
    """Get device UUID from config file"""
    config_path = os.path.join('c:\\program files (x86)\\Wegweiser\\Config\\' if platform.system() == 'Windows' else '/opt/Wegweiser/Config/', 'agent.config')
    try:
        with open(config_path) as f:
            config = json.load(f)
        return (config['deviceuuid'], config.get('serverAddr', 'app.wegweiser.tech'))
    except Exception as e:
        logger.error(f"Failed to get device UUID: {e}")
        sys.exit(1)

def run_osquery(query):
    """Run osquery and return results"""
    try:
        if platform.system() == 'Windows':
            osquery_path = r'C:\Program Files\osquery\osqueryi.exe'
        else:
            osquery_path = '/usr/bin/osqueryi'

        cmd = [osquery_path, '--json', query]
        logger.debug(f"Running osquery: {' '.join(cmd)}")
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            logger.error(f"osquery error: {result.stderr}")
            return None
            
        return json.loads(result.stdout)
    except Exception as e:
        logger.error(f"Failed to run osquery. Reason: {e}")
        return None

def get_osquery_schema():
    """Get schema information from osquery"""
    try:
        schema_query = "SELECT * FROM sqlite_schema WHERE type = 'table'"
        tables = run_osquery(schema_query)
        
        if not tables:
            logger.error("Failed to get schema information")
            return None
        
        # Get column information for each table
        schema_data = []
        for table in tables:
            table_name = table.get('name')
            if table_name.startswith('sqlite_') or table_name == 'temp':
                continue
                
            columns_query = f"PRAGMA table_info({table_name})"
            columns = run_osquery(columns_query)
            
            if columns:
                schema_data.append({
                    'name': table_name,
                    'columns': [
                        {
                            'name': col.get('name'),
                            'type': col.get('type')
                        }
                        for col in columns
                    ]
                })
        
        return schema_data
    except Exception as e:
        logger.error(f"Failed to get schema: {e}")
        return None

def on_message(ws, message):
    """Handle incoming websocket messages"""
    try:
        data = json.loads(message)
        message_type = data.get('type')
        
        logger.info(f"Received message type: {message_type}")
        
        if message_type == 'command':
            command = data.get('command')
            command_id = data.get('command_id')
            params = data.get('params', {})
            
            if command == 'osquery':
                # Handle osquery command
                query = params.get('query')
                query_name = params.get('query_name', 'ad_hoc_query')
                
                if not query:
                    ws.send(json.dumps({
                        'type': 'command_response',
                        'command_id': command_id,
                        'response': {
                            'status': 'error',
                            'message': 'No query provided',
                            'query_name': query_name
                        }
                    }))
                    return
                
                # Run the query
                result = run_osquery(query)
                
                # Send response
                ws.send(json.dumps({
                    'type': 'command_response',
                    'command_id': command_id,
                    'response': {
                        'status': 'success',
                        'query_name': query_name,
                        'data': result
                    }
                }))
            
            elif command == 'osquery_schema':
                # Get schema information
                schema_data = get_osquery_schema()
                
                # Send schema data
                ws.send(json.dumps({
                    'type': 'osquery_schema',
                    'schema_data': schema_data
                }))
        
        elif message_type == 'error':
            logger.error(f"Error from server: {data.get('message')}")
    
    except json.JSONDecodeError:
        logger.error("Invalid JSON received")
    except Exception as e:
        logger.error(f"Error processing message: {e}")

def on_error(ws, error):
    """Handle websocket errors"""
    logger.error(f"WebSocket error: {error}")

def on_close(ws, close_status_code, close_msg):
    """Handle websocket close"""
    logger.info(f"WebSocket closed: {close_status_code} - {close_msg}")

def on_open(ws):
    """Handle websocket open"""
    logger.info("WebSocket connection established")
    
    # Send schema information on connect
    schema_data = get_osquery_schema()
    if schema_data:
        ws.send(json.dumps({
            'type': 'osquery_schema',
            'schema_data': schema_data
        }))
    
    # Start heartbeat thread
    def heartbeat_thread():
        while True:
            try:
                ws.send(json.dumps({
                    'type': 'heartbeat',
                    'timestamp': int(time.time())
                }))
                time.sleep(30)  # Send heartbeat every 30 seconds
            except Exception as e:
                logger.error(f"Heartbeat error: {e}")
                break
    
    Thread(target=heartbeat_thread, daemon=True).start()

def main():
    """Main function"""
    try:
        device_uuid, server_addr = get_device_uuid()
        
        # WebSocket URL
        ws_url = f"wss://{server_addr}/ws/agent/{device_uuid}"
        logger.info(f"Connecting to {ws_url}")
        
        # Create WebSocket connection
        ws = websocket.WebSocketApp(
            ws_url,
            on_open=on_open,
            on_message=on_message,
            on_error=on_error,
            on_close=on_close
        )
        
        # Connect with SSL verification
        ws.run_forever(sslopt={"cert_reqs": ssl.CERT_REQUIRED})
        
    except Exception as e:
        logger.error(f"Error in main: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
