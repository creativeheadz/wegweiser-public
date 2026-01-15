# Lynis Security Audit Agent Script

This document provides the complete agent script for deploying Lynis security audits on Linux and macOS systems.

## Overview

This Python script:
1. Downloads Lynis from the official GitHub repository (CISOfy/lynis)
2. Runs a comprehensive security audit on the system
3. Sends results back to Wegweiser for AI analysis
4. Automatically updates Lynis on subsequent runs

**Compatibility:** Linux and macOS only
**Distribution:** NOT by Wegweiser (customers download directly from GitHub)
**License:** Lynis is GPL v3 licensed

---

## Deployment Instructions

### Step 1: Create the Script in Wegweiser Admin

1. Navigate to **Administration → Snippets**
2. Click **Create New Snippet**
3. Fill in the following details:

| Field | Value |
|-------|-------|
| Name | `Lynis Security Audit` |
| Description | `Comprehensive security audit using Lynis. Compatible with Linux and macOS systems.` |
| Script Type | `Python` |
| Platform | `Linux, macOS` |
| metalogos_type | `lynis-audit` |
| Schedule | `Weekly` |
| Cost | Included in WegCoins calculation |

### Step 2: Copy the Script Content

Copy the complete script from the "Complete Python Script" section below and paste it into the Script Content field.

### Step 3: Save and Deploy

Click **Save**. The script will be automatically deployed to assigned devices on their next check-in.

---

## Complete Python Script

```python
# Lynis Security Audit Script for Wegweiser
# This script downloads Lynis from official GitHub repo and runs a security audit
# Platform: Linux, macOS
# metalogos_type: lynis-audit

import os
import sys
import json
import platform
import subprocess
import requests
from logzero import logger

def getAppDirs():
    """Get application directories based on OS"""
    if platform.system() == 'Windows':
        appDir = 'c:\\program files (x86)\\Wegweiser\\'
    else:
        appDir = '/opt/Wegweiser/'
    logDir = os.path.join(appDir, 'Logs', '')
    configDir = os.path.join(appDir, 'Config', '')
    filesDir = os.path.join(appDir, 'files', '')
    scriptsDir = os.path.join(appDir, 'Scripts', '')
    tempDir = os.path.join(appDir, 'Temp', '')
    lynisDir = os.path.join(appDir, 'lynis', '')
    return appDir, logDir, configDir, tempDir, filesDir, scriptsDir, lynisDir

def getDeviceUuid():
    """Read device UUID and server address from config"""
    appDir, logDir, configDir, tempDir, filesDir, scriptsDir, lynisDir = getAppDirs()
    with open(os.path.join(configDir, 'agent.config')) as f:
        agentConfigDict = json.load(f)
    deviceUuid = agentConfigDict['deviceuuid']
    if 'serverAddr' in agentConfigDict:
        host = agentConfigDict['serverAddr']
    else:
        host = 'app.wegweiser.tech'
    return deviceUuid, host

def check_os_compatibility():
    """Check if OS is compatible with Lynis"""
    os_name = platform.system()
    if os_name not in ['Linux', 'Darwin']:  # Darwin = macOS
        logger.error(f"Lynis is not compatible with {os_name}")
        return False
    return True

def install_lynis():
    """Download and install Lynis from official GitHub repository"""
    appDir, logDir, configDir, tempDir, filesDir, scriptsDir, lynisDir = getAppDirs()

    # Check if Lynis already exists
    lynis_binary = os.path.join(lynisDir, 'lynis')
    if os.path.exists(lynis_binary):
        logger.info("Lynis already installed, checking for updates...")
        try:
            # Update existing installation
            result = subprocess.run(
                ['git', '-C', lynisDir, 'pull'],
                capture_output=True,
                text=True,
                timeout=60
            )
            if result.returncode == 0:
                logger.info("Lynis updated successfully")
                return True
            else:
                logger.warning("Failed to update Lynis, will use existing version")
                return True
        except Exception as e:
            logger.warning(f"Could not update Lynis: {e}, using existing version")
            return True

    # Install fresh copy
    logger.info("Installing Lynis from official GitHub repository...")
    try:
        # Ensure parent directory exists
        os.makedirs(appDir, mode=0o755, exist_ok=True)

        # Clone from official repository
        result = subprocess.run(
            ['git', 'clone', 'https://github.com/CISOfy/lynis.git', lynisDir],
            capture_output=True,
            text=True,
            timeout=120
        )

        if result.returncode == 0:
            logger.info("Lynis installed successfully")
            return True
        else:
            logger.error(f"Failed to install Lynis: {result.stderr}")
            return False

    except subprocess.TimeoutExpired:
        logger.error("Lynis installation timed out")
        return False
    except Exception as e:
        logger.error(f"Error installing Lynis: {e}")
        return False

def run_lynis_audit():
    """Run Lynis security audit and return results"""
    appDir, logDir, configDir, tempDir, filesDir, scriptsDir, lynisDir = getAppDirs()
    lynis_binary = os.path.join(lynisDir, 'lynis')

    if not os.path.exists(lynis_binary):
        logger.error("Lynis binary not found")
        return None

    logger.info("Running Lynis security audit...")

    try:
        # Run Lynis audit
        # --quiet: Less verbose output
        # --quick: Skip wait for user input
        # --auditor "Wegweiser": Tag the audit
        result = subprocess.run(
            [lynis_binary, 'audit', 'system', '--quiet', '--quick', '--auditor', 'Wegweiser'],
            capture_output=True,
            text=True,
            timeout=300  # 5 minutes max
        )

        if result.returncode not in [0, 1]:  # Lynis returns 1 if warnings found (normal)
            logger.error(f"Lynis audit failed: {result.stderr}")
            return None

        # Parse the log file for results
        log_file = '/var/log/lynis.log'
        report_file = '/var/log/lynis-report.dat'

        audit_results = {
            'status': 'completed',
            'timestamp': int(subprocess.check_output(['date', '+%s']).decode().strip()),
            'os': platform.system(),
            'os_version': platform.release(),
            'hostname': platform.node(),
            'lynis_version': None,
            'hardening_index': None,
            'tests_performed': 0,
            'warnings': [],
            'suggestions': [],
            'findings': {},
            'raw_output': result.stdout
        }

        # Parse report file if it exists
        if os.path.exists(report_file):
            with open(report_file, 'r') as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith('#'):
                        continue

                    if '=' in line:
                        key, value = line.split('=', 1)
                        key = key.strip()
                        value = value.strip()

                        # Extract key information
                        if key == 'lynis_version':
                            audit_results['lynis_version'] = value
                        elif key == 'hardening_index':
                            audit_results['hardening_index'] = int(value)
                        elif key == 'tests_performed':
                            audit_results['tests_performed'] = int(value)
                        elif key.startswith('warning['):
                            audit_results['warnings'].append(value)
                        elif key.startswith('suggestion['):
                            audit_results['suggestions'].append(value)
                        else:
                            # Store other findings
                            if key not in audit_results['findings']:
                                audit_results['findings'][key] = []
                            audit_results['findings'][key].append(value)

        # Parse log file for additional details
        if os.path.exists(log_file):
            with open(log_file, 'r') as f:
                log_content = f.read()
                audit_results['log_excerpt'] = log_content[-5000:]  # Last 5000 chars

        logger.info(f"Lynis audit completed. Hardening Index: {audit_results.get('hardening_index', 'N/A')}")
        logger.info(f"Tests performed: {audit_results['tests_performed']}")
        logger.info(f"Warnings: {len(audit_results['warnings'])}")
        logger.info(f"Suggestions: {len(audit_results['suggestions'])}")

        return audit_results

    except subprocess.TimeoutExpired:
        logger.error("Lynis audit timed out after 5 minutes")
        return None
    except Exception as e:
        logger.error(f"Error running Lynis audit: {e}")
        return None

def send_to_wegweiser(deviceUuid, host, audit_data):
    """Send audit results to Wegweiser server"""
    body = {
        'deviceuuid': deviceUuid,
        'metalogos_type': 'lynis-audit',
        'metalogos': audit_data
    }

    url = f'https://{host}/ai/device/metadata'
    headers = {'Content-Type': 'application/json'}

    try:
        response = requests.post(url, headers=headers, data=json.dumps(body), timeout=30)
        if response.status_code == 200:
            logger.info("Lynis audit data sent successfully to Wegweiser")
            return True
        else:
            logger.error(f"Failed to send data: HTTP {response.status_code}")
            return False
    except Exception as e:
        logger.error(f"Error sending data to Wegweiser: {e}")
        return False

# Main execution
try:
    # Check OS compatibility
    if not check_os_compatibility():
        logger.error("This script requires Linux or macOS")
        sys.exit(1)

    # Get device configuration
    deviceUuid, host = getDeviceUuid()
    logger.info(f"Device UUID: {deviceUuid}")

    # Install/Update Lynis
    if not install_lynis():
        logger.error("Failed to install Lynis")
        sys.exit(1)

    # Run security audit
    audit_results = run_lynis_audit()
    if audit_results is None:
        logger.error("Failed to run Lynis audit")
        sys.exit(1)

    # Convert to JSON string for transmission
    data = json.dumps(audit_results)

    # Send to Wegweiser
    if send_to_wegweiser(deviceUuid, host, data):
        logger.info("Lynis security audit completed successfully")
        print("SUCCESS: Lynis audit completed and sent to Wegweiser")
    else:
        logger.error("Failed to send audit results to Wegweiser")
        sys.exit(1)

except Exception as e:
    logger.error(f"Fatal error in Lynis audit script: {e}")
    print(f"ERROR: {e}")
    sys.exit(1)
```

---

## Configuration

### Automatic Configuration

The script automatically reads the device configuration from:
- **Config File**: `/opt/Wegweiser/Config/agent.config`

The config file must contain:
```json
{
    "deviceuuid": "device-uuid-here",
    "serverAddr": "app.wegweiser.tech"  // optional, defaults to app.wegweiser.tech
}
```

### Environment Variables

No environment variables are required for this script.

---

## Output

The script sends audit results to `/ai/device/metadata` endpoint with:

```json
{
    "deviceuuid": "device-uuid",
    "metalogos_type": "lynis-audit",
    "metalogos": {
        "status": "completed",
        "timestamp": 1635000000,
        "os": "Linux",
        "os_version": "5.10.0-8-generic",
        "hostname": "server-name",
        "lynis_version": "3.0.6",
        "hardening_index": 65,
        "tests_performed": 247,
        "warnings": ["warning1", "warning2"],
        "suggestions": ["suggestion1", "suggestion2"],
        "findings": {},
        "raw_output": "..."
    }
}
```

---

## Scheduling

The script is scheduled to run:
- **Frequency**: Weekly (configurable)
- **Automatic Updates**: Lynis is updated on each run if changes are available
- **Error Handling**: Graceful fallback to cached version if updates fail

---

## Dependencies

The script requires:
- Python 3.7+
- `git` (for cloning Lynis repository)
- `logzero` (for logging)
- `requests` (for HTTP requests)
- Root/sudo access (for comprehensive security audit)

### Installation of Dependencies

These are typically already available on Linux and macOS systems used by Wegweiser agents.

---

## Troubleshooting

### Issue: "Lynis is not compatible with {os_name}"
- **Cause**: Script run on Windows system
- **Solution**: This script only works on Linux and macOS. Windows devices must use Windows-compatible security tools.

### Issue: "Failed to install Lynis"
- **Cause**: Git not installed or network connectivity issues
- **Solution**:
  - Verify Git is installed: `which git`
  - Check network connectivity to GitHub
  - Check firewall rules allow access to github.com

### Issue: "Lynis audit timed out"
- **Cause**: System is very slow or CPU constrained
- **Solution**:
  - Increase timeout value in script (line 143: `timeout=300`)
  - Run audit during off-peak hours
  - Check system load during audit

### Issue: "Failed to send data"
- **Cause**: Network issues or server unavailable
- **Solution**:
  - Check network connectivity to Wegweiser server
  - Verify server address in agent.config is correct
  - Check Wegweiser server status

---

## Security Considerations

1. **Data Privacy**: Lynis output contains sensitive system information
   - Downloaded directly by customer devices (not distributed by Wegweiser)
   - Transmitted securely (HTTPS) to Wegweiser
   - Stored encrypted in Wegweiser database

2. **GPL v3 License Compliance**:
   - Lynis is downloaded from official CISOfy GitHub repository
   - Wegweiser does not distribute or modify Lynis
   - Full license information available at https://www.gnu.org/licenses/gpl-3.0.en.html

3. **Authentication**:
   - Requires valid device UUID in agent.config
   - Only sends data to configured Wegweiser server

---

## Performance Impact

- **Installation Time**: ~2 minutes (first run only)
- **Update Time**: ~1 minute (subsequent runs)
- **Audit Execution**: 3-5 minutes (depending on system complexity)
- **Data Transmission**: ~10 seconds (depending on network speed)
- **Total Duration**: 4-7 minutes
- **CPU Impact**: High during audit, returns to normal after completion
- **Memory Impact**: ~100-200 MB during audit

---

## Monitoring

Monitor the following in Wegweiser:

1. **Audit Success Rate**: % of audits completing successfully
2. **Average Security Score**: Trend over time
3. **Critical Findings**: Monitor for system vulnerabilities
4. **Audit Frequency**: Ensure weekly/monthly execution is working

---

## Support

For issues with:
- **Lynis Tool**: See https://cisofy.com/lynis/
- **GPL v3 License**: See https://www.gnu.org/licenses/gpl-3.0.en.html
- **Wegweiser Integration**: Contact Wegweiser support team

---

## Version History

- **v1.0** (2025-10-25): Initial release for Lynis security audit integration
