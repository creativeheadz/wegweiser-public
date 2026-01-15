# Filepath: snippets/unSigned/updateAgentWithPersistent.py
import subprocess
import platform
import os
import json
from logzero import logger

def getDeviceConfig(configFile):
    logger.info(f'Attempting to read config file: {configFile}...')
    if os.path.isfile(configFile):
        try:
            with open(configFile, 'r') as f:
                configDict = json.load(f)
            logger.info(f'Successfully read {configFile}')
            deviceUuid = configDict['deviceuuid']

            # The config file doesn't store groupuuid, we need to get it from the device registration
            # For now, we'll use a placeholder and let the script handle device lookup
            # The installAgent.sh script only needs groupuuid for NEW registrations
            # For existing devices, it will skip registration and just update
            groupUuid = 'existing-device'  # Placeholder for existing installations

            logger.info(f'Device UUID: {deviceUuid}')
            return deviceUuid, groupUuid, configDict
        except Exception as e:
            logger.error(f'Failed to read {configFile}: {e}')
            return None, None, None
    else:
        logger.error(f'{configFile} does not exist.')
        return None, None, None

def getAppDirs():
    if platform.system() == 'Windows':
        appDir = 'c:\\program files (x86)\\Wegweiser\\'
    else:
        appDir = '/opt/Wegweiser/'
    configDir = os.path.join(appDir, 'Config', '')
    return appDir, configDir

def runAgentUpdate():
    """Run the enhanced installAgent.sh script to update both agents"""
    
    # Only run on Linux systems
    if platform.system() != 'Linux':
        logger.info('Enhanced agent update only supported on Linux systems')
        return False
    
    # Get device configuration
    appDir, configDir = getAppDirs()
    configFile = os.path.join(configDir, 'agent.config')
    deviceUuid, groupUuid, configDict = getDeviceConfig(configFile)

    if not deviceUuid:
        logger.error('Could not determine device UUID from config')
        return False

    logger.info(f'Updating agent for device {deviceUuid}')

    try:
        # Stop persistent agent service first if it's running
        logger.info('Checking and stopping persistent agent service...')
        try:
            service_status = subprocess.run(['sudo', 'systemctl', 'is-active', 'wegweiser-persistent-agent.service'],
                                          capture_output=True, text=True)
            if service_status.returncode == 0:
                logger.info('Stopping persistent agent service before update...')
                stop_result = subprocess.run(['sudo', 'systemctl', 'stop', 'wegweiser-persistent-agent.service'],
                                           capture_output=True, text=True, timeout=30)
                if stop_result.returncode == 0:
                    logger.info('Persistent agent service stopped successfully')
                else:
                    logger.warning(f'Failed to stop service: {stop_result.stderr}')
            else:
                logger.info('Persistent agent service is not running')
        except Exception as e:
            logger.warning(f'Could not check/stop persistent agent service: {e}')

        # Use the Wegweiser temp directory which should be writable
        import time
        temp_dir = '/opt/Wegweiser/Temp'

        # Ensure temp directory exists
        os.makedirs(temp_dir, exist_ok=True)

        # Create unique temp script name
        temp_script = os.path.join(temp_dir, f'installAgent_{int(time.time())}.sh')

        # Download the script first
        logger.info('Downloading enhanced installation script...')
        download_cmd = f'curl -o {temp_script} https://app.wegweiser.tech/download/installAgent.sh'
        download_result = subprocess.run(download_cmd, shell=True, capture_output=True, text=True, timeout=60)

        if download_result.returncode != 0:
            logger.error(f'Failed to download script: {download_result.stderr}')
            return False

        # Make it executable
        os.chmod(temp_script, 0o755)

        # For existing devices, we can use any group UUID as placeholder since registration will be skipped
        placeholder_group = 'existing-device-update'

        # Run the installation script
        logger.info(f'Running enhanced installation script...')
        run_cmd = f'sudo {temp_script} {placeholder_group}'

        logger.info(f'Executing: {run_cmd}')
        result = subprocess.run(run_cmd, shell=True, capture_output=True, text=True, timeout=300)

        # Clean up temp script
        try:
            os.remove(temp_script)
        except Exception as e:
            logger.warning(f'Could not remove temp script {temp_script}: {e}')
        
        if result.returncode == 0:
            logger.info('Agent update completed successfully')
            logger.info(f'Update output: {result.stdout}')

            # Wait a moment for service to start
            import time
            time.sleep(5)

            # Check if persistent agent service is running
            try:
                service_status = subprocess.run(['sudo', 'systemctl', 'is-active', 'wegweiser-persistent-agent.service'],
                                              capture_output=True, text=True)
                if service_status.returncode == 0:
                    logger.info('Persistent agent service is running after update')

                    # Also check service logs for any immediate errors
                    log_check = subprocess.run(['sudo', 'journalctl', '-u', 'wegweiser-persistent-agent.service', '--since', '1 minute ago', '-n', '10'],
                                             capture_output=True, text=True, timeout=10)
                    if log_check.returncode == 0:
                        logger.info('Recent service logs:')
                        logger.info(log_check.stdout)
                else:
                    logger.warning('Persistent agent service is not running after update')
                    # Try to get service status for debugging
                    status_check = subprocess.run(['sudo', 'systemctl', 'status', 'wegweiser-persistent-agent.service'],
                                                capture_output=True, text=True, timeout=10)
                    if status_check.returncode != 0:
                        logger.error(f'Service status: {status_check.stdout}')
            except Exception as e:
                logger.error(f'Could not check persistent agent service status: {e}')

            return True
        else:
            logger.error(f'Agent update failed with return code {result.returncode}')
            logger.error(f'Error output: {result.stderr}')
            return False
            
    except subprocess.TimeoutExpired:
        logger.error('Agent update timed out after 5 minutes')
        return False
    except Exception as e:
        logger.error(f'Error running agent update: {e}')
        return False

####################### MAIN #######################

logger.info('Starting enhanced agent update (cron + persistent)')

success = runAgentUpdate()

if success:
    logger.info('Enhanced agent update completed successfully')
    logger.info('Both cron-based and persistent agents have been updated')
    logger.info('The persistent agent service should now be running with the latest code')
else:
    logger.error('Enhanced agent update failed')
    logger.info('Check the logs above for details')
