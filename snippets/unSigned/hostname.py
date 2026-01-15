# Filepath: snippets/unSigned/hostname.py

import os
import subprocess
import json
import platform
import requests
import tempfile

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

if platform.system() == 'Windows':
    try:
        deviceUuid, host = getDeviceUuid()
        
        ps_script = """
# Get the local machine's IP address
$localIP = [System.Net.Dns]::GetHostAddresses([System.Net.Dns]::GetHostName()) | Where-Object { $_.AddressFamily -eq 'InterNetwork' } | Select-Object -First 1

# Perform GetHostByAddress using the local IP address
$hostName = [System.Net.Dns]::GetHostByAddress($localIP).HostName

# Output the hostname
$hostName

"""
        
        # Save PowerShell script
        ps_file = tempfile.NamedTemporaryFile(delete=False, suffix='.ps1')
        ps_file.write(ps_script.encode())
        ps_file.close()
        
        # Execute PowerShell script
        command = ['powershell.exe', '-ExecutionPolicy', 'Bypass', '-File', ps_file.name]
        result = subprocess.run(command, 
                             stdout=subprocess.PIPE, 
                             stderr=subprocess.PIPE, 
                             universal_newlines=True)
        
        try:
            data = json.loads(result.stdout)
        except json.JSONDecodeError:
            data = {
                "error": "Failed to parse JSON output",
                "stdout": result.stdout,
                "stderr": result.stderr
            }
        
        body = {
            'deviceuuid': deviceUuid,
            'metalogos_type': 'hostname',
            'metalogos': data
        }
        
        url = f'https://{host}/ai/device/metadata'
        headers = {'Content-Type': 'application/json'}
        response = requests.post(url, headers=headers, data=json.dumps(body))
        print(f"Data collected and sent. Response: {response.status_code}")
        
    except Exception as e:
        print(f"Error during execution: {str(e)}")
        
    finally:
        if os.path.exists(ps_file.name):
            os.unlink(ps_file.name)
else:
    print("Not a Windows system - PowerShell execution skipped")
