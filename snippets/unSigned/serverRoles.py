# Filepath: snippets/unSigned/serverRoles.py
import os
import subprocess
import json
import platform
import requests

def getAppDirs():
    if platform.system() == 'Windows':
        appDir = 'c:\\program files (x86)\\Wegweiser\\'
    else:
        appDir = '/opt/Wegweiser/'
    logDir = os.path.join(appDir, 'Logs', '')
    configDir = os.path.join(appDir, 'Config', '')
    filesDir = os.path.join(appDir, 'files', '')
    scriptsDir = os.path.join(appDir, 'Scripts', '')
    tempDir = os.path.join(appDir, 'Temp', '')
    return(appDir, logDir, configDir, tempDir, filesDir, scriptsDir)

def getDeviceUuid():
    appDir, logDir, configDir, tempDir, filesDir, scriptsDir = getAppDirs()
    with open(os.path.join(configDir, 'agent.config')) as f:
        agentConfigDict = json.load(f)
    deviceUuid = agentConfigDict['deviceuuid']
    if 'serverAddr' in agentConfigDict:
        host = agentConfigDict['serverAddr']
    else:
        host = 'app.wegweiser.tech'
    return(deviceUuid, host)

def send_server_roles_as_tags(server_roles, device_uuid):
    url = 'https://app.wegweiser.tech/payload/serverroles'
    headers = {'Content-Type': 'application/json'}
    payload = {
        "deviceuuid": device_uuid,
        "ServerRoles": server_roles
    }
    response = requests.post(url, headers=headers, data=json.dumps(payload))
    if response.status_code == 200:
        print("Server roles successfully sent as tags.")
    else:
        print(f"Failed to send server roles as tags. Status code: {response.status_code}")

# Initialize variables
SCRIPT_URL = 'https://app.wegweiser.tech/download/serverroles.ps1'
PS_SCRIPT_PATH = r'C:\temp\serverroles.ps1'

if platform.system() == 'Windows':
    try:
        # Get device UUID and host
        deviceUuid, host = getDeviceUuid()
        
        # Download the PowerShell script
        response = requests.get(SCRIPT_URL)
        if response.status_code == 200:
            # Save the script to specified directory
            with open(PS_SCRIPT_PATH, 'wb') as f:
                f.write(response.content)
            print(f"Downloaded PowerShell script to: {PS_SCRIPT_PATH}")
            
            # Run PowerShell script
            command = [r'C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe', '-ExecutionPolicy', 'Bypass', '-File', PS_SCRIPT_PATH]
            result = subprocess.run(command, 
                                 stdout=subprocess.PIPE, 
                                 stderr=subprocess.PIPE, 
                                 universal_newlines=True)
            print(f"STDOUT: {result.stdout}")
            print(f"STDERR: {result.stderr}")
            
            # Read the generated JSON from stdout
            try:
                server_roles_data = json.loads(result.stdout)
            except json.JSONDecodeError:
                server_roles_data = {
                    "error": "Failed to parse JSON output",
                    "stdout": result.stdout,
                    "stderr": result.stderr
                }
            
            # Prepare the metadata payload
            body = {
                'deviceuuid': deviceUuid,
                'metalogos_type': 'server-roles',
                'metalogos': server_roles_data
            }
            
            # Send to server
            url = f'https://{host}/ai/device/metadata'
            headers = {'Content-Type': 'application/json'}
            response = requests.post(url, headers=headers, data=json.dumps(body))
            print(f"Server roles data collected and sent. Response: {response.status_code}")
            
            # Send server roles as tags
            if "ServerRoles" in server_roles_data:
                send_server_roles_as_tags(server_roles_data["ServerRoles"], deviceUuid)
            
        else:
            print(f"Failed to download PowerShell script: {response.status_code}")
            
    except Exception as e:
        print(f"Error during execution: {str(e)}")
        
    finally:
        # Clean up
        if os.path.exists(PS_SCRIPT_PATH):
            try:
                os.remove(PS_SCRIPT_PATH)
            except Exception as e:
                print(f"Failed to delete temp script: {str(e)}")
else:
    print("Not a Windows system - server roles collection skipped")