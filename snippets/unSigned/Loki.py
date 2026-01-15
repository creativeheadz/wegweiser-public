# Filepath: snippets/unSigned/Loki.py
#!/usr/bin/env python3
import platform
from logzero import logger, logfile
import os
import json
import zipfile
import requests
import sys
import subprocess
import shutil
from datetime import datetime
import asyncio
import uuid
import time


# Replace the platform-specific BASE_DIR with a more flexible approach
BASE_DIR = os.getenv('WEGWEISER_BASE_DIR', '/opt/Wegweiser')

# Ensure Agent core is importable so we can use ToolManager from inside a snippet
AGENT_DIR = os.path.join(BASE_DIR, 'Agent')
if AGENT_DIR not in sys.path:
    sys.path.insert(0, AGENT_DIR)

try:
    from core.tool_manager import ToolManager
except ImportError:
    ToolManager = None


def log_message(msg):
    """Log a message using logzero logger"""
    logger.info(f"LOKI: {msg}")

def getAppDirs():
    """Get application directories based on BASE_DIR"""
    # Try to get directory from environment first
    appDir = os.getenv('WEGWEISER_BASE_DIR', BASE_DIR)

    # Ensure the base directory exists
    if not os.path.exists(appDir):
        fallback_dirs = [
            '/opt/Wegweiser',
            '/Applications/Wegweiser',
            r'C:\Program Files (x86)\Wegweiser'
        ]
        for d in fallback_dirs:
            if os.path.exists(d):
                appDir = d
                break

    if not appDir.endswith(os.sep):
        appDir += os.sep

    logDir = os.path.join(appDir, 'Logs', '')
    configDir = os.path.join(appDir, 'Config', '')
    filesDir = os.path.join(appDir, 'Files', '')
    scriptsDir = os.path.join(appDir, 'Scripts', '')
    tempDir = os.path.join(appDir, 'Temp', '')
    return appDir, logDir, configDir, tempDir, filesDir, scriptsDir

def check_network():
    """Check if the network is available by pinging an external URL"""
    try:
        requests.get("https://www.google.com", timeout=5)
        return True
    except requests.ConnectionError:
        return False

def getDeviceUuid():
    """Retrieve the device UUID and server address from the configuration file"""
    appDir, logDir, configDir, tempDir, filesDir, scriptsDir = getAppDirs()
    log_message(f"Reading config from {configDir}")

    # Add additional config file locations to try
    config_locations = [
        os.path.join(configDir, 'agent.config'),
        '/etc/wegweiser/agent.config',
        os.path.expanduser('~/.config/wegweiser/agent.config')
    ]

    for config_file in config_locations:
        try:
            with open(config_file) as f:
                agentConfigDict = json.load(f)
                log_message(f"Successfully read config from {config_file}")
                break
        except (FileNotFoundError, json.JSONDecodeError) as e:
            continue
    else:
        log_message("Error: Could not find valid agent.config in any location")
        sys.exit(1)

    deviceUuid = agentConfigDict.get('deviceuuid')
    host = agentConfigDict.get('serverAddr', 'app.wegweiser.tech')
    return deviceUuid, host

def parse_loki_output(output_text):
    """Parse Loki's CSV output into a structured format"""
    results = {
        'alerts': [],
        'warnings': [],
        'notices': [],
        'scan_time': datetime.now().isoformat(),
        'summary': {
            'total_alerts': 0,
            'total_warnings': 0,
            'total_notices': 0
        }
    }

    for line in output_text.split('\n'):
        if not line.strip():
            continue

        try:
            parts = line.split(',')
            if len(parts) >= 4:
                timestamp, hostname, level, message = parts[0:4]
                event = {
                    'timestamp': timestamp,
                    'message': message,
                    'details': ','.join(parts[4:]) if len(parts) > 4 else ''
                }

                if level == 'ALERT':
                    results['alerts'].append(event)
                    results['summary']['total_alerts'] += 1
                elif level == 'WARNING':
                    results['warnings'].append(event)
                    results['summary']['total_warnings'] += 1
                elif level == 'NOTICE':
                    results['notices'].append(event)
                    results['summary']['total_notices'] += 1

        except Exception as e:
            log_message(f"Error parsing line: {line}, Error: {str(e)}")

    return results

def send_metadata(deviceUuid, host, loki_results):
    """Send Loki results to the metadata endpoint"""
    try:
        body = {
            'deviceuuid': deviceUuid,
            'metalogos_type': 'loki-scan',
            'metalogos': loki_results
        }

        url = f'https://{host}/ai/device/metadata'
        headers = {'Content-Type': 'application/json'}
        response = requests.post(url, headers=headers, data=json.dumps(body))

        if response.status_code in [200, 201]:
            log_message("Successfully sent Loki results to server")
        else:
            log_message(f"Failed to send results. Status code: {response.status_code}")

        return response.status_code

    except Exception as e:
        log_message(f"Error sending metadata: {str(e)}")
        return None

def _get_queue_path(configDir):
    """Return path to Loki scan queue file."""
    return os.path.join(configDir, "loki_queue.json")


def _load_queue(queue_path):
    """Load Loki scan queue from JSON file."""
    if not os.path.exists(queue_path):
        return {"version": 1, "jobs": []}
    try:
        with open(queue_path, "r") as f:
            data = json.load(f)
        if not isinstance(data, dict):
            return {"version": 1, "jobs": []}
        jobs = data.get("jobs", [])
        if not isinstance(jobs, list):
            jobs = []
        data["jobs"] = jobs
        return data
    except Exception as e:
        log_message(f"Failed to load Loki queue from {queue_path}: {e}")
        return {"version": 1, "jobs": []}


def _save_queue(queue_path, queue_data):
    """Persist Loki queue atomically."""
    tmp_path = queue_path + ".tmp"
    try:
        os.makedirs(os.path.dirname(queue_path), exist_ok=True)
        with open(tmp_path, "w") as f:
            json.dump(queue_data, f, indent=2)
        os.replace(tmp_path, queue_path)
    except Exception as e:
        log_message(f"Failed to save Loki queue to {queue_path}: {e}")


def _get_next_pending_job(queue_data):
    """Return the first pending Loki job or None."""
    for job in queue_data.get("jobs", []):
        status = job.get("status", "pending")
        if status in (None, "pending"):
            return job
    return None


def _update_job_status(queue_data, job_id, status, error=None):
    """Update status metadata for a job in the Loki queue."""
    now = datetime.now().isoformat()
    for job in queue_data.get("jobs", []):
        if job.get("id") == job_id:
            job["status"] = status
            job["updated_at"] = now
            if error:
                job["last_error"] = str(error)
            break

def deploy_and_run_loki():
    """Queue-driven Loki execution entrypoint.

    This snippet is intentionally simple and immutable:
    - Reads a local JSON queue of scan jobs from Config/loki_queue.json
    - Uses ToolManager to download/locate the Loki tool bundle
    - Executes a single pending job (if any)
    """
    appDir, logDir, configDir, tempDir, filesDir, scriptsDir = getAppDirs()

    # Ensure log directory exists
    os.makedirs(logDir, exist_ok=True)

    # Set up logfile for the Loki worker
    log_file_path = os.path.join(logDir, "loki_worker.log")
    logfile(log_file_path)

    log_message("Starting Loki queue worker snippet")

    # Load queue and get next job
    queue_path = _get_queue_path(configDir)
    queue_data = _load_queue(queue_path)

    job = _get_next_pending_job(queue_data)
    if not job:
        # For now, if there is no pending job, enqueue a default test job so
        # the snippet can be used immediately for manual testing via the
        # scheduler. In future iterations, jobs will normally be created by
        # the NATS/command layer.
        job = {
            "id": str(uuid.uuid4()),
            "parameters": {"test": True},
            "status": "pending",
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
        }
        queue_data.setdefault("jobs", []).append(job)
        _save_queue(queue_path, queue_data)
        log_message(f"Enqueued default Loki test job {job['id']} as no jobs were pending.")

    # Initialize job metadata
    job_id = job.get("id") or str(uuid.uuid4())
    job["id"] = job_id
    now_iso = datetime.now().isoformat()
    job.setdefault("created_at", now_iso)
    job["updated_at"] = now_iso
    job["status"] = "running"
    _save_queue(queue_path, queue_data)

    if ToolManager is None:
        log_message("ToolManager is not available in this environment; cannot run Loki.")
        _update_job_status(queue_data, job_id, "failed", "ToolManager not available")
        _save_queue(queue_path, queue_data)
        return

    # Read device config to get server address for ToolManager
    try:
        deviceUuid, host = getDeviceUuid()
    except SystemExit:
        host = "app.wegweiser.tech"
        deviceUuid = None
        log_message("Failed to resolve device UUID from config; falling back to default host.")

    try:
        tm = ToolManager(BASE_DIR, host)

        parameters = job.get("parameters") or {}
        if not parameters:
            # Minimal safe default: quick test scan
            parameters = {"test": True}

        log_message(f"Running Loki job {job_id} with parameters: {parameters}")
        result = asyncio.run(tm.run_tool("loki", parameters))

        status = result.get("status", "error")
        returncode = result.get("returncode")
        stderr = result.get("stderr", "")

        if status == "success":
            log_message(f"Loki job {job_id} completed successfully (return code {returncode})")
            _update_job_status(queue_data, job_id, "completed")
        else:
            error_msg = f"Loki job {job_id} failed with return code {returncode}: {stderr[-500:] if stderr else ''}"
            log_message(error_msg)
            _update_job_status(queue_data, job_id, "failed", error_msg)

        _save_queue(queue_path, queue_data)

    except Exception as e:
        error_msg = f"Error during Loki queue worker execution for job {job_id}: {str(e)}"
        log_message(error_msg)
        _update_job_status(queue_data, job_id, "failed", error_msg)
        _save_queue(queue_path, queue_data)

if __name__ == "__main__":
    deploy_and_run_loki()