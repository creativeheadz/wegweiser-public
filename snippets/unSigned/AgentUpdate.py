# Filepath: snippets/unSigned/AgentUpdate.py
#!/usr/bin/env python3
"""
Comprehensive Agent Update Snippet
Supports updating NATS agent, classical agent, or both
Supports immediate hot-reload or scheduled reboot
Backward compatible with v3.0.1 agents
"""

import hashlib
import json
import os
import platform
import shutil
import subprocess
import sys
import time
import datetime
from pathlib import Path

import requests
from logzero import logger, logfile


def log_message(msg):
    """Log a message with timestamp"""
    logger.info(f"AGENT_UPDATE: {msg}")


def get_app_dirs():
    """Get application directories based on platform"""
    system = platform.system()
    if system == 'Windows':
        app_dir = r"C:\Program Files (x86)\Wegweiser"
    elif system == 'Darwin':  # macOS
        app_dir = "/opt/Wegweiser"
    else:  # Linux
        app_dir = "/opt/Wegweiser"

    log_dir = os.path.join(app_dir, 'Logs')
    config_dir = os.path.join(app_dir, 'Config')
    agent_dir = os.path.join(app_dir, 'Agent')
    backup_dir = os.path.join(app_dir, '.backup')

    return app_dir, log_dir, config_dir, agent_dir, backup_dir


def get_device_config(config_dir):
    """Retrieve device UUID and server address from config file"""
    config_file = os.path.join(config_dir, 'agent.config')
    log_message(f"Reading config from {config_file}")

    try:
        with open(config_file, 'r') as f:
            config_dict = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        log_message(f"Error reading config: {e}")
        sys.exit(1)

    device_uuid = config_dict.get('deviceuuid')
    server_addr = config_dict.get('serverAddr', 'app.wegweiser.tech')

    return device_uuid, server_addr


def download_and_verify(url, expected_hash, temp_file):
    """Download update package and verify SHA256 hash"""
    log_message(f"Downloading update from {url}")

    try:
        response = requests.get(url, timeout=300, stream=True)
        response.raise_for_status()

        # Save to temp file
        with open(temp_file, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)

        log_message(f"Download complete, saved to {temp_file}")

        # Verify hash
        sha256_hash = hashlib.sha256()
        with open(temp_file, 'rb') as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)

        actual_hash = sha256_hash.hexdigest()
        log_message(f"Expected hash: {expected_hash}")
        log_message(f"Actual hash:   {actual_hash}")

        if actual_hash != expected_hash:
            raise ValueError(f"Hash mismatch! Update package may be corrupted.")

        log_message("Hash verification successful")
        return True

    except requests.RequestException as e:
        log_message(f"Download failed: {e}")
        return False
    except Exception as e:
        log_message(f"Verification failed: {e}")
        return False


def backup_current_installation(agent_dir, backup_dir):
    """Backup current installation for rollback"""
    timestamp = int(time.time())
    backup_path = os.path.join(backup_dir, f"agent-backup-{timestamp}")

    log_message(f"Creating backup at {backup_path}")

    try:
        os.makedirs(backup_path, exist_ok=True)

        # Copy entire Agent directory
        shutil.copytree(agent_dir, os.path.join(backup_path, 'Agent'), dirs_exist_ok=True)

        log_message(f"Backup created successfully")
        return backup_path

    except Exception as e:
        log_message(f"Backup failed: {e}")
        return None


def extract_update(temp_file, install_dir):
    """Extract update tarball to installation directory"""
    log_message(f"Extracting update to {install_dir}")

    try:
        # Ensure installation directory exists
        os.makedirs(install_dir, exist_ok=True)

        # Extract using tar command (tarball root is "Agent/" so we extract
        # directly into the application directory, e.g. C:\Program Files (x86)\Wegweiser
        # or /opt/Wegweiser)
        cmd = ['tar', '-xzf', temp_file, '-C', install_dir]

        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)

        if result.returncode != 0:
            raise Exception(f"tar command failed: {result.stderr}")

        log_message("Extraction complete")
        return True

    except Exception as e:
        log_message(f"Extraction failed: {e}")
        return False


def rollback_installation(backup_path, agent_dir):
    """Rollback to previous installation from backup"""
    log_message(f"Rolling back installation from {backup_path}")

    try:
        backup_agent = os.path.join(backup_path, 'Agent')

        # Remove current installation
        if os.path.exists(agent_dir):
            shutil.rmtree(agent_dir)

        # Restore from backup
        shutil.copytree(backup_agent, agent_dir)

        log_message("Rollback successful")
        return True

    except Exception as e:
        log_message(f"Rollback failed: {e}")
        return False


def restart_service_immediate():
    """Restart agent service immediately with verification and fallback"""
    system = platform.system()
    log_message(f"Restarting agent service on {system}")

    try:
        if system == "Linux":
            return restart_linux_service()
        elif system == "Darwin":  # macOS
            return restart_macos_service()
        elif system == "Windows":
            # On Windows the update snippet often runs inside the
            # WegweiserAgent service process (NATS agent). Stopping the
            # service directly from here would terminate this process before it
            # can start it again. Instead, delegate restart to a Task Scheduler
            # task that runs out-of-process under SYSTEM.
            return restart_windows_service()
        else:
            log_message(f"Unknown platform: {system}")
            return False

    except Exception as e:
        log_message(f"Service restart failed: {e}")
        return False


def restart_windows_service():
    """Schedule a Windows service restart via Task Scheduler.

    The update snippet typically runs inside the WegweiserAgent service
    process. If we tried to stop the service directly from here, Windows
    would terminate this process before it could start the service again.

    To avoid this, we create/update a Task Scheduler task that runs under
    SYSTEM and executes a small PowerShell command to restart the
    WegweiserAgent service out-of-process. We then trigger that task once.
    """

    task_name = "Wegweiser Agent Restart"

    # PowerShell command executed by the scheduled task. Using single quotes
    # inside the -Command argument keeps quoting simple.
    action = (
        "powershell.exe -NoProfile -ExecutionPolicy Bypass "
        "-Command 'Start-Sleep -Seconds 3; Restart-Service WegweiserAgent -Force'"
    )

    try:
        log_message("Creating/updating Task Scheduler job to restart WegweiserAgent...")

        create_cmd = [
            "schtasks", "\x2FCreate",  # use literal / to avoid escaping issues
            "/TN", task_name,
            "/SC", "ONCE",
            "/ST", "00:00",
            "/RU", "SYSTEM",
            "/RL", "HIGHEST",
            "/TR", action,
            "/F",
        ]

        # Normalize any escaped slash that might sneak in; schtasks expects '/'
        create_cmd = [arg.replace("\\x2F", "/") for arg in create_cmd]

        create_result = subprocess.run(
            create_cmd,
            capture_output=True,
            text=True,
            timeout=30,
        )

        if create_result.returncode != 0:
            log_message(
                "Failed to create/update restart task: "
                f"{create_result.stderr or create_result.stdout}"
            )
            return False

        log_message("Restart task created/updated successfully, triggering it now...")

        run_cmd = ["schtasks", "/Run", "/TN", task_name]
        run_result = subprocess.run(
            run_cmd,
            capture_output=True,
            text=True,
            timeout=30,
        )

        if run_result.returncode != 0:
            log_message(
                "Failed to run restart task: "
                f"{run_result.stderr or run_result.stdout}"
            )
            return False

        log_message(
            "Restart task triggered successfully; "
            "WegweiserAgent will be restarted by Task Scheduler."
        )
        return True

    except Exception as e:
        log_message(f"Windows service restart scheduling failed: {e}")
        return False


def restart_linux_service():
    """Restart Linux systemd services with verification"""
    log_message("Restarting Linux systemd services...")

    services = ["wegweiser-agent", "wegweiser-persistent-agent"]
    all_success = True

    for service in services:
        log_message(f"Restarting {service}...")
        result = subprocess.run(["systemctl", "restart", service],
                              capture_output=True, text=True, timeout=30)

        if result.returncode != 0:
            log_message(f"Failed to restart {service}: {result.stderr}")
            all_success = False
            continue

        # Verify it's running
        time.sleep(2)
        check = subprocess.run(["systemctl", "is-active", service],
                             capture_output=True, text=True, timeout=10)

        if check.stdout.strip() == "active":
            log_message(f"OK: {service} verified active")
        else:
            log_message(f"FAIL: {service} not active: {check.stdout.strip()}")
            all_success = False

    return all_success


def restart_macos_service():
    """Restart macOS LaunchDaemons with verification"""
    log_message("Restarting macOS LaunchDaemons...")

    services = [
        "tech.wegweiser.agent",
        "tech.wegweiser.persistent-agent"
    ]

    all_success = True

    for service in services:
        log_message(f"Restarting {service}...")

        # Stop
        subprocess.run(["launchctl", "stop", service], check=False)
        time.sleep(2)

        # Start
        start_result = subprocess.run(["launchctl", "start", service],
                                     capture_output=True, text=True, timeout=30)

        if start_result.returncode != 0:
            log_message(f"Failed to start {service}: {start_result.stderr}")
            all_success = False
            continue

        # Verify
        time.sleep(2)
        check = subprocess.run(["launchctl", "list"],
                             capture_output=True, text=True, timeout=10)

        if service in check.stdout:
            log_message(f"OK: {service} verified running")
        else:
            log_message(f"FAIL: {service} not found in launchctl list")
            all_success = False

    return all_success


def stage_update_for_reboot(temp_file, app_dir):
    """Stage update for application after next reboot"""
    system = platform.system()
    staging_file = os.path.join(app_dir, 'staged-update.tar.gz')

    log_message(f"Staging update for reboot on {system}")

    try:
        # Copy update package to staging area
        shutil.copy2(temp_file, staging_file)
        log_message(f"Update staged at {staging_file}")

        if system == "Linux":
            # Create oneshot systemd service to apply on next boot
            unit_content = f"""[Unit]
Description=Apply Wegweiser Agent Update
After=network.target

[Service]
Type=oneshot
ExecStart=/bin/tar -xzf {staging_file} -C {app_dir}
ExecStartPost=/bin/rm -f {staging_file}
ExecStartPost=/bin/systemctl restart wegweiser-persistent-agent
RemainAfterExit=yes

[Install]
WantedBy=multi-user.target
"""
            unit_file = '/etc/systemd/system/wegweiser-apply-update.service'
            with open(unit_file, 'w') as f:
                f.write(unit_content)

            subprocess.run(["systemctl", "daemon-reload"], check=True)
            subprocess.run(["systemctl", "enable", "wegweiser-apply-update.service"], check=True)
            log_message("Systemd unit created and enabled")

        elif system == "Windows":
            # Create scheduled task to run on startup
            # For now, just log that it's staged (can be enhanced with schtasks)
            log_message("Update staged for manual application after reboot")
            log_message("Windows scheduled task creation would go here")

        return True

    except Exception as e:
        log_message(f"Staging failed: {e}")
        return False




def send_update_status(device_uuid, server_addr, status, version, error_msg=None):
    """Send update status back to server"""
    try:
        url = f"https://{server_addr}/api/device/{device_uuid}/update-status"
        payload = {
            'status': status,
            'version': version,
            'timestamp': datetime.datetime.now(datetime.UTC).isoformat(),
            'error_message': error_msg,
        }

        response = requests.post(url, json=payload, timeout=30)
        log_message(f"Status sent to server: {status}")

    except Exception as e:
        log_message(f"Failed to send status to server: {e}")


####################### MAIN EXECUTION #######################

def main():
    """Main execution function"""

    # Get application directories
    app_dir, log_dir, config_dir, agent_dir, backup_dir = get_app_dirs()

    # Setup logging
    os.makedirs(log_dir, exist_ok=True)
    log_file_path = os.path.join(log_dir, 'agent_update.log')
    logfile(log_file_path)

    log_message("=== Agent Update Script Started ===")
    log_message(f"Platform: {platform.system()} {platform.release()}")

    # Get device configuration
    device_uuid, server_addr = get_device_config(config_dir)
    log_message(f"Device UUID: {device_uuid}")
    log_message(f"Server: {server_addr}")

    # Get parameters from environment variables (passed by agent executor)
    update_version = os.getenv('UPDATE_VERSION', '3.0.2')
    update_url = os.getenv('UPDATE_URL', f'https://{server_addr}/installerFiles/{platform.system()}/updates/agent-{update_version}.tar.gz')
    update_hash = os.getenv('UPDATE_HASH', '')
    apply_mode = os.getenv('APPLY_MODE', 'immediate')
    target_component = os.getenv('TARGET_COMPONENT', 'both')

    log_message(f"Update version: {update_version}")
    log_message(f"Update URL: {update_url}")
    log_message(f"Apply mode: {apply_mode}")
    log_message(f"Target component: {target_component}")

    if not update_hash:
        log_message("ERROR: No update hash provided, cannot verify package integrity")
        send_update_status(device_uuid, server_addr, 'failed', update_version, 'No hash provided')
        sys.exit(1)

    # Download update package
    temp_file = os.path.join(app_dir, 'Temp', f'update-{update_version}.tar.gz')
    os.makedirs(os.path.dirname(temp_file), exist_ok=True)

    if not download_and_verify(update_url, update_hash, temp_file):
        log_message("Download or verification failed")
        send_update_status(device_uuid, server_addr, 'failed', update_version, 'Download/verification failed')
        sys.exit(1)

    # Backup current installation
    backup_path = backup_current_installation(agent_dir, backup_dir)
    if not backup_path:
        log_message("Backup failed, aborting update")
        send_update_status(device_uuid, server_addr, 'failed', update_version, 'Backup failed')
        sys.exit(1)

    # Extract update
    if not extract_update(temp_file, app_dir):
        log_message("Extraction failed, attempting rollback")
        rollback_installation(backup_path, agent_dir)
        send_update_status(device_uuid, server_addr, 'failed', update_version, 'Extraction failed')
        sys.exit(1)

    # Apply update based on mode
    if apply_mode == 'immediate':
        log_message("Applying update immediately")

        if restart_service_immediate():
            log_message("Update applied successfully")
            send_update_status(device_uuid, server_addr, 'success', update_version)

            # Clean up temp file
            try:
                os.remove(temp_file)
            except:
                pass

        else:
            log_message("Service restart failed, attempting rollback")
            rollback_installation(backup_path, agent_dir)
            restart_service_immediate()  # Try to restart old version
            send_update_status(device_uuid, server_addr, 'failed', update_version, 'Service restart failed')
            sys.exit(1)

    elif apply_mode == 'scheduled_reboot':
        log_message("Staging update for reboot")

        if stage_update_for_reboot(temp_file, app_dir):
            log_message("Update staged successfully, will apply on next reboot")
            send_update_status(device_uuid, server_addr, 'staged', update_version)
        else:
            log_message("Staging failed")
            send_update_status(device_uuid, server_addr, 'failed', update_version, 'Staging failed')
            sys.exit(1)

    log_message("=== Agent Update Script Completed ===")


if __name__ == "__main__":
    main()
