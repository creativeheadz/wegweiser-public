# Lynis Security Audit Integration for Wegweiser
## Comprehensive Implementation Guide

---

## Table of Contents
1. [Overview](#overview)
2. [Business Value](#business-value)
3. [Architecture](#architecture)
4. [Database Changes](#database-changes)
5. [Agent Script Implementation](#agent-script-implementation)
6. [API Endpoint](#api-endpoint)
7. [AI Analysis Prompt](#ai-analysis-prompt)
8. [UI Components](#ui-components)
9. [Health Score Integration](#health-score-integration)
10. [Testing](#testing)
11. [Deployment](#deployment)
12. [Premium Feature Configuration](#premium-feature-configuration)

---

## Overview

This document provides complete implementation details for integrating Lynis security auditing into Wegweiser. Lynis is a GPL v3 licensed security auditing tool that will be downloaded directly from the official GitHub repository by customer devices, not distributed by Wegweiser.

**Key Features:**
- Automated security audits for Linux/macOS devices
- Compliance checking (ISO27001, PCI-DSS, HIPAA)
- Vulnerability detection
- System hardening recommendations
- AI-powered analysis and health scoring

**Implementation Timeline:**
- Phase 1: Core Integration (1-2 weeks)
- Phase 2: AI Analysis (1 week)
- Phase 3: UI & Reporting (1 week)

---

## Business Value

### For MSP Customers:
- ✅ Automated security compliance audits
- ✅ Risk reduction through vulnerability identification
- ✅ Audit trails for compliance officers
- ✅ Competitive advantage with continuous security posture monitoring

### For Wegweiser:
- ✅ Premium feature monetization via WegCoins
- ✅ Market differentiation (security + monitoring)
- ✅ Upsell opportunities
- ✅ Appeal to security-conscious enterprise clients

---

## Architecture

### Data Flow

```
Customer Device (Linux/macOS)
    ↓
1. Wegweiser Agent downloads Lynis from GitHub
    ↓
2. Agent runs: lynis audit system --quiet
    ↓
3. Agent captures JSON output
    ↓
4. Agent sends to: POST /ai/device/metadata
    ↓
5. Wegweiser stores in DeviceMetadata table
    ↓
6. AI analyzes Lynis report
    ↓
7. Generates health score & recommendations
    ↓
8. Displays in UI (Security Audit tab)
```

### New metalogos_type:
- `lynis-audit` - Full Lynis audit report

---

## Database Changes

### No Schema Changes Needed!

The existing `DeviceMetadata` table already supports this:

```sql
-- Existing table structure (no changes needed)
CREATE TABLE devicemetadata (
    id SERIAL PRIMARY KEY,
    deviceuuid VARCHAR NOT NULL,
    metalogos_type VARCHAR NOT NULL,  -- Will use 'lynis-audit'
    metalogos TEXT,                    -- Will store Lynis JSON report
    ai_analysis TEXT,                  -- Will store AI analysis
    score INTEGER,                     -- Health score from AI
    created_at INTEGER NOT NULL,
    FOREIGN KEY (deviceuuid) REFERENCES devices(deviceuuid)
);
```

### Verification Query

```sql
-- Check if lynis-audit data exists
SELECT 
    d.devicename,
    dm.metalogos_type,
    dm.score,
    dm.created_at
FROM devicemetadata dm
JOIN devices d ON dm.deviceuuid = d.deviceuuid
WHERE dm.metalogos_type = 'lynis-audit'
ORDER BY dm.created_at DESC
LIMIT 10;
```

---

## Agent Script Implementation

### File Location
`app/routes/admin/admin_snippets.py` - Create new snippet via admin UI

### Complete Python Script for Agent

**Create this as a "Custom Script" snippet in Wegweiser admin:**

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

### Agent Script Deployment

**In Wegweiser Admin UI:**

1. Navigate to: **Administration → Snippets**
2. Click: **Create New Snippet**
3. Fill in:
   - **Name:** `Lynis Security Audit`
   - **Description:** `Comprehensive security audit using Lynis. Compatible with Linux and macOS systems.`
   - **Script Type:** `Python`
   - **Platform:** `Linux, macOS`
   - **metalogos_type:** `lynis-audit`
   - **Schedule:** `Weekly` (or as desired)
   - **Script Content:** [Paste the complete Python script above]

4. Click: **Save**

---

## API Endpoint

### Existing Endpoint (No Changes Needed)

The existing `/ai/device/metadata` endpoint already handles this:

**File:** `app/routes/ai.py`

The endpoint already accepts:
- `deviceuuid`
- `metalogos_type` (will use 'lynis-audit')
- `metalogos` (will contain Lynis JSON data)

### Verification

Ensure the endpoint processes Lynis data correctly by checking the route handles the new `metalogos_type`:

```python
# In app/routes/ai.py (verification only - no changes needed)

@ai_bp.route('/device/metadata', methods=['POST'])
@csrf.exempt
def receive_device_metadata():
    """
    Receives device metadata including Lynis audit results
    This endpoint already exists and handles all metalogos_type values
    """
    data = request.get_json()
    deviceuuid = data.get('deviceuuid')
    metalogos_type = data.get('metalogos_type')  # Will be 'lynis-audit'
    metalogos = data.get('metalogos')
    
    # ... existing processing logic
    # No changes needed - it already handles new types
```

---

## AI Analysis Prompt

### File Location
`app/tasks/security/prompts/lynis.prompt`

Create this new directory and file:

```bash
mkdir -p app/tasks/security/prompts
```

### Complete Prompt Template

**File:** `app/tasks/security/prompts/lynis.prompt`

```
# Filepath: app/tasks/security/prompts/lynis.prompt
# Lynis Security Audit Analysis for MSP Operations

Analyze the following Lynis security audit report for a managed device and provide a comprehensive security assessment suitable for MSP operations. Your analysis should be thorough, actionable, and prioritize findings based on risk and compliance impact.

## Analysis Structure Required

Structure your response in clean HTML format using <p>, <h3>, <h4>, <ul>, <li>, <strong>, and <br> tags for optimal readability in the Wegweiser UI.

### 1. Executive Summary (2-3 sentences)
Provide a high-level overview of the device's security posture, highlighting the most critical finding and overall risk level.

### 2. Security Posture Overview
- **Hardening Index**: {hardening_index}/100 - Interpret this score
- **Overall Security Grade**: Assign a letter grade (A-F) based on findings
- **Primary Risk Level**: Critical/High/Medium/Low
- **Compliance Status**: Summary of compliance-relevant findings

### 3. Critical Security Findings
List all critical security issues that require immediate attention:
- Describe each finding clearly for non-technical stakeholders
- Explain the potential impact and exploitation scenarios
- Provide immediate remediation steps
- Estimate remediation time and complexity

### 4. High-Priority Warnings
Analyze all warnings from the Lynis report:
- Categorize by severity and impact
- Explain why each warning matters
- Provide context for business risk
- Recommend remediation priority order

### 5. System Hardening Recommendations
Based on Lynis suggestions, provide prioritized hardening steps:
- **Quick Wins** (< 1 hour): Easy fixes with immediate security benefit
- **Standard Hardening** (1-4 hours): Important security improvements
- **Advanced Hardening** (> 4 hours): Comprehensive security enhancements
- For each recommendation: Explain the security benefit and implementation approach

### 6. Compliance Assessment
Evaluate findings against common compliance frameworks:
- **ISO27001 Controls**: Which controls are affected by findings
- **PCI-DSS Requirements**: Relevant PCI-DSS compliance gaps
- **HIPAA Requirements**: Healthcare-related security concerns (if applicable)
- **CIS Benchmarks**: Alignment with CIS security benchmarks
- Provide specific control references for audit documentation

### 7. Vulnerability Summary
Categorize all identified vulnerabilities:
- **Authentication & Access Control**: Login security, password policies, SSH configuration
- **Network Security**: Firewall, open ports, network services
- **Software Security**: Outdated packages, missing patches, vulnerable software
- **File System Security**: Permissions, encryption, sensitive data exposure
- **Audit & Logging**: Log configuration, audit trails, monitoring gaps
- **Kernel & System**: Kernel hardening, system configuration weaknesses

### 8. MSP Action Plan
Provide a clear, step-by-step action plan for MSP technicians:

**Immediate Actions (Within 24 hours):**
1. [Specific action with exact commands if possible]
2. [Next action]
3. [Continue...]

**Short-term Actions (Within 1 week):**
1. [Specific action]
2. [Next action]
3. [Continue...]

**Long-term Actions (Within 1 month):**
1. [Specific action]
2. [Next action]
3. [Continue...]

### 9. Monitoring & Maintenance Strategy
- **Key Security Metrics**: What to monitor continuously
- **Audit Frequency**: Recommended re-scan schedule
- **Alert Thresholds**: When to escalate security issues
- **Automated Remediation**: Opportunities for automation
- **Trend Analysis**: What to track over time

### 10. Risk Assessment
- **Data Breach Risk**: High/Medium/Low with justification
- **Compliance Risk**: High/Medium/Low with justification
- **Operational Risk**: High/Medium/Low with justification
- **Reputational Risk**: High/Medium/Low with justification

### 11. Health Score Justification
**Declare a health score between 1 and 100 where 100 is perfect security.**

Base the score on:
- Hardening Index weight: 40%
- Critical findings: -30 points each
- High warnings: -10 points each
- Medium warnings: -5 points each
- Missing security controls: -2 points each
- Positive security implementations: +5 points each

Explain the score calculation briefly.

### 12. Client Communication Summary
Provide a non-technical summary suitable for client reporting:
- Current security status in plain language
- What actions are being taken
- Expected improvements
- Timeline and next steps

## Important Analysis Guidelines

1. **Be Specific**: Don't say "improve security" - say "Enable UFW firewall with restrictive default policy"
2. **Prioritize Impact**: Focus on findings that could lead to actual security breaches
3. **Consider Context**: Some findings may be acceptable based on the device role
4. **Provide Commands**: Include exact shell commands for remediation when possible
5. **Think MSP**: Remember this is for managed service providers monitoring multiple clients
6. **Document Everything**: Provide audit trail documentation for compliance officers
7. **Balance Security vs Usability**: Note when recommendations might impact functionality
8. **Cost-Benefit Analysis**: Indicate the security ROI for major recommendations

## Lynis Audit Data:

{lynis_data}

## Additional Context:

- Device Name: {device_name}
- Operating System: {os_type}
- MSP Client: {client_name}
- Device Role: {device_role}
- Compliance Requirements: {compliance_requirements}

## Output Format:

Respond ONLY with HTML-formatted analysis as specified above. Use clean, semantic HTML. Make liberal use of <strong> tags for emphasis on critical items. Ensure all recommendations are actionable and specific.
```

---

## UI Components

### 1. Add Security Audit Tab to Device Page

**File:** `app/templates/devices/device_detail.html` (or similar)

Add new tab to the device navigation:

```html
<!-- Add this to the tab navigation section -->
<li class="nav-item">
    <a class="nav-link" id="security-tab" data-toggle="tab" href="#security" role="tab">
        <i class="fas fa-shield-alt"></i> Security Audit
    </a>
</li>

<!-- Add this to the tab content section -->
<div class="tab-pane fade" id="security" role="tabpanel">
    <div class="card">
        <div class="card-header">
            <h4><i class="fas fa-shield-alt"></i> Security Audit Report</h4>
            <small class="text-muted">Powered by Lynis Security Auditing Tool</small>
        </div>
        <div class="card-body">
            <div id="security-audit-content">
                <div class="text-center">
                    <i class="fas fa-spinner fa-spin fa-3x"></i>
                    <p>Loading security audit data...</p>
                </div>
            </div>
        </div>
    </div>
</div>
```

### 2. Add JavaScript to Fetch Security Data

**File:** `app/static/js/device_detail.js` (or inline in template)

```javascript
// Fetch and display security audit data
function loadSecurityAudit(deviceUuid) {
    const url = `/ui/device/${deviceUuid}/eventlog/lynis-audit`;
    
    fetch(url)
        .then(response => response.text())
        .then(html => {
            document.getElementById('security-audit-content').innerHTML = html;
        })
        .catch(error => {
            console.error('Error loading security audit:', error);
            document.getElementById('security-audit-content').innerHTML = 
                '<div class="alert alert-warning">No security audit data available. Run a Lynis audit on this device.</div>';
        });
}

// Load when security tab is clicked
document.getElementById('security-tab').addEventListener('click', function() {
    const deviceUuid = document.getElementById('device-uuid').value;
    loadSecurityAudit(deviceUuid);
});
```

### 3. Backend Route for Security Data

**File:** `app/routes/ui.py`

The existing `get_event_log` function already handles this, but verify it works with the new `metalogos_type`:

```python
# In app/routes/ui.py (verification - should already work)

@ui_bp.route('/device/<deviceuuid>/eventlog/<log_type>', methods=['GET'])
@login_required
def get_event_log(deviceuuid, log_type):
    """
    Fetch event log for a specific device and log type
    This already handles 'lynis-audit' as a log_type
    """
    tenantuuid = session.get('tenant_uuid')
    if not tenantuuid:
        return "Tenant UUID not found in session", 403

    # Existing query - already works for lynis-audit
    query = text("""
    SELECT dm.ai_analysis, dm.created_at
    FROM public.devicemetadata dm
    JOIN public.devices d ON dm.deviceuuid = d.deviceuuid
    WHERE dm.deviceuuid = :deviceuuid 
      AND d.tenantuuid = :tenantuuid 
      AND dm.metalogos_type = :log_type
    ORDER BY dm.created_at DESC
    LIMIT 1
    """)

    try:
        result = db.session.execute(query, {
            'deviceuuid': deviceuuid,
            'tenantuuid': tenantuuid,
            'log_type': log_type  # Will be 'lynis-audit'
        })
        row = result.fetchone()
        
        if row:
            eventlog, created_at = row
            readable_time = datetime.fromtimestamp(created_at).strftime('%Y-%m-%d %H:%M:%S')
            eventlog_html = f"<p><strong>Audit Date:</strong> {readable_time}</p>" + Markup(eventlog)
            return eventlog_html
        else:
            return Markup('<div class="alert alert-info">No security audit available yet. Schedule a Lynis audit to see security analysis.</div>')
    except Exception as e:
        log_with_route(logging.ERROR, f"Error fetching security audit: {str(e)}")
        return f"An error occurred while fetching security audit: {str(e)}", 500
```

### 4. Dashboard Widget (Optional)

Add a security overview widget to the main dashboard:

**File:** `app/templates/dashboard.html`

```html
<!-- Security Overview Widget -->
<div class="col-md-6 col-lg-4">
    <div class="card border-left-warning shadow h-100">
        <div class="card-body">
            <div class="row no-gutters align-items-center">
                <div class="col mr-2">
                    <div class="text-xs font-weight-bold text-warning text-uppercase mb-1">
                        Security Audits
                    </div>
                    <div class="h5 mb-0 font-weight-bold text-gray-800">
                        <span id="security-audit-count">--</span>
                    </div>
                    <div class="mt-2 text-xs">
                        <span id="critical-findings" class="text-danger">-- Critical</span> |
                        <span id="high-findings" class="text-warning">-- High</span>
                    </div>
                </div>
                <div class="col-auto">
                    <i class="fas fa-shield-alt fa-2x text-gray-300"></i>
                </div>
            </div>
        </div>
    </div>
</div>

<script>
// Fetch security statistics
fetch('/api/security/statistics')
    .then(response => response.json())
    .then(data => {
        document.getElementById('security-audit-count').textContent = data.total_audits;
        document.getElementById('critical-findings').textContent = `${data.critical_findings} Critical`;
        document.getElementById('high-findings').textContent = `${data.high_findings} High`;
    });
</script>
```

---

## Health Score Integration

### Update Health Score Calculation

**File:** `app/utilities/health_score.py` (or wherever health scoring is calculated)

Add Lynis security score to the overall device health score:

```python
# File: app/utilities/health_score.py

def calculate_device_health_score(device_uuid):
    """
    Calculate overall device health score including security audit
    
    Components:
    - Storage Health: 20%
    - Network Health: 15%
    - System Events: 25%
    - Security Audit (Lynis): 25%
    - Performance Metrics: 15%
    
    Total: 100%
    """
    from app.models import DeviceMetadata, Devices
    from sqlalchemy import text
    
    scores = {
        'storage': None,
        'network': None,
        'system_events': None,
        'security': None,
        'performance': None
    }
    
    # Get latest scores for each component
    query = text("""
        SELECT metalogos_type, score
        FROM devicemetadata
        WHERE deviceuuid = :device_uuid
        AND score IS NOT NULL
        AND metalogos_type IN ('storage', 'network', 'eventsFiltered-System', 'lynis-audit', 'performance')
        ORDER BY created_at DESC
    """)
    
    results = db.session.execute(query, {'device_uuid': device_uuid}).fetchall()
    
    for row in results:
        metalogos_type, score = row
        
        if metalogos_type == 'storage' and scores['storage'] is None:
            scores['storage'] = score
        elif metalogos_type == 'network' and scores['network'] is None:
            scores['network'] = score
        elif metalogos_type == 'eventsFiltered-System' and scores['system_events'] is None:
            scores['system_events'] = score
        elif metalogos_type == 'lynis-audit' and scores['security'] is None:
            scores['security'] = score
        elif metalogos_type == 'performance' and scores['performance'] is None:
            scores['performance'] = score
    
    # Calculate weighted average
    weights = {
        'storage': 0.20,
        'network': 0.15,
        'system_events': 0.25,
        'security': 0.25,
        'performance': 0.15
    }
    
    total_weight = 0
    weighted_sum = 0
    
    for component, score in scores.items():
        if score is not None:
            weighted_sum += score * weights[component]
            total_weight += weights[component]
    
    if total_weight == 0:
        return None  # No data available
    
    # Normalize to 100
    overall_score = int(weighted_sum / total_weight)
    
    return overall_score


def get_security_grade(security_score):
    """Convert security score to letter grade"""
    if security_score >= 90:
        return 'A', 'Excellent'
    elif security_score >= 80:
        return 'B', 'Good'
    elif security_score >= 70:
        return 'C', 'Fair'
    elif security_score >= 60:
        return 'D', 'Poor'
    else:
        return 'F', 'Critical'
```

---

## Testing

### 1. Manual Testing Checklist

**Prerequisites:**
- [ ] Linux or macOS test device available
- [ ] Wegweiser agent installed on test device
- [ ] Git installed on test device
- [ ] Internet connectivity for GitHub access

**Test Steps:**

1. **Deploy Agent Script**
   ```bash
   # On Wegweiser server
   # Navigate to Admin → Snippets
   # Create Lynis audit snippet
   # Assign to test device
   ```

2. **Trigger Manual Execution**
   ```bash
   # On test device
   cd /opt/Wegweiser/Scripts
   python3 lynis_audit_script.py
   ```

3. **Verify Lynis Installation**
   ```bash
   # On test device
   ls -la /opt/Wegweiser/lynis/lynis
   /opt/Wegweiser/lynis/lynis --version
   ```

4. **Check Data Collection**
   ```sql
   -- On Wegweiser database
   SELECT 
       d.devicename,
       dm.metalogos_type,
       length(dm.metalogos) as data_size,
       dm.created_at
   FROM devicemetadata dm
   JOIN devices d ON dm.deviceuuid = d.deviceuuid
   WHERE dm.metalogos_type = 'lynis-audit'
   ORDER BY dm.created_at DESC
   LIMIT 1;
   ```

5. **Verify AI Analysis**
   ```sql
   -- Check that AI analysis was generated
   SELECT 
       deviceuuid,
       score,
       length(ai_analysis) as analysis_size,
       created_at
   FROM devicemetadata
   WHERE metalogos_type = 'lynis-audit'
   AND ai_analysis IS NOT NULL
   ORDER BY created_at DESC
   LIMIT 1;
   ```

6. **Test UI Display**
   - Log into Wegweiser
   - Navigate to test device
   - Click "Security Audit" tab
   - Verify report displays correctly
   - Check that HTML formatting is clean

7. **Verify Health Score Update**
   ```sql
   SELECT 
       devicename,
       health_score
   FROM devices
   WHERE deviceuuid = 'YOUR_TEST_DEVICE_UUID';
   ```

### 2. Error Scenarios to Test

1. **Device without Git**
   - Expected: Script logs error and exits gracefully
   - Verify: No partial data sent to Wegweiser

2. **Network Connectivity Issues**
   - Test: Disconnect network during Lynis download
   - Expected: Script retries or uses cached version
   - Verify: Appropriate error logging

3. **Windows Device (Incompatible)**
   - Expected: Script detects OS and exits with clear message
   - Verify: No errors in Wegweiser logs

4. **Lynis Timeout**
   - Test: Device with very slow CPU
   - Expected: Script times out after 5 minutes
   - Verify: Partial results handled gracefully

5. **Malformed JSON**
   - Test: Manually send invalid JSON to API
   - Expected: API returns 400 error
   - Verify: Database remains consistent

### 3. Performance Testing

**Test Scenarios:**
- [ ] Lynis installation time (should be < 2 minutes)
- [ ] Audit execution time (should be < 5 minutes)
- [ ] AI analysis time (should be < 30 seconds)
- [ ] UI load time (should be < 2 seconds)

### 4. Compliance Testing

Verify that the Lynis integration provides meaningful compliance data:

1. **ISO27001**
   - [ ] Control A.12.6.1 (Technical vulnerability management)
   - [ ] Control A.12.2.1 (Controls against malware)
   - [ ] Control A.9.2.3 (Management of privileged access rights)

2. **PCI-DSS**
   - [ ] Requirement 2 (Default passwords)
   - [ ] Requirement 6 (Security vulnerabilities)
   - [ ] Requirement 10 (Logging and monitoring)

3. **HIPAA**
   - [ ] 164.312(a)(1) (Access control)
   - [ ] 164.312(b) (Audit controls)
   - [ ] 164.312(c)(1) (Integrity controls)

---

## Deployment

### Phase 1: Core Integration (Week 1-2)

**Day 1-2: Database & API Preparation**
```bash
# Verify database schema
psql wegweiser_db -c "\d devicemetadata"

# Test API endpoint
curl -X POST https://app.wegweiser.tech/ai/device/metadata \
  -H "Content-Type: application/json" \
  -d '{"deviceuuid":"test","metalogos_type":"lynis-audit","metalogos":"{}"}'
```

**Day 3-5: Agent Script Development**
- Create script in admin UI
- Test on development device
- Refine error handling
- Test update mechanism

**Day 6-7: Initial Testing**
- Deploy to 5 test devices
- Monitor for errors
- Collect feedback
- Fix issues

**Day 8-10: Documentation**
- Update admin documentation
- Create user guides
- Write troubleshooting guide

### Phase 2: AI Analysis (Week 3)

**Day 1-2: Prompt Development**
```bash
# Create prompt file
mkdir -p app/tasks/security/prompts
nano app/tasks/security/prompts/lynis.prompt
# [Paste complete prompt from earlier section]
```

**Day 3-4: AI Integration**
- Connect prompt to analysis pipeline
- Test with real Lynis data
- Refine prompt based on output quality
- Verify health score calculation

**Day 5: Testing**
- Run analysis on 10+ devices
- Review AI output quality
- Adjust prompt as needed
- Verify scores are reasonable

### Phase 3: UI & Reporting (Week 4)

**Day 1-2: UI Components**
- Add Security Audit tab to device page
- Create dashboard widget
- Implement JavaScript loading
- Style with Bootstrap

**Day 3-4: Reporting Features**
- Create compliance report generator
- Build trend analysis view
- Add export functionality (PDF/Excel)

**Day 5: Final Testing**
- End-to-end testing
- User acceptance testing
- Performance testing
- Security review

### Production Rollout

**Soft Launch (Week 5):**
1. Enable for beta customers only (10-20 devices)
2. Monitor closely for issues
3. Collect feedback
4. Fix any critical bugs

**General Availability (Week 6):**
1. Enable for all customers
2. Announce feature in release notes
3. Provide training materials
4. Monitor adoption metrics

### Monitoring Plan

**Metrics to Track:**
- Number of devices with Lynis installed
- Audit success rate
- Average audit execution time
- AI analysis success rate
- Average security score
- Number of critical findings
- Time to remediation
- User engagement with security tab

**Alerts to Configure:**
- Lynis installation failures > 5%
- Audit execution failures > 10%
- AI analysis failures > 2%
- Critical security findings detected
- Security score drops > 20 points

---

## Premium Feature Configuration

### WegCoins Integration

**File:** `app/models.py` (or wherever WegCoins are configured)

Add Lynis auditing as a premium feature:

```python
# WegCoins pricing configuration
WEGCOINS_FEATURES = {
    'lynis_audit_monthly': {
        'cost': 50,  # 50 WegCoins per device per month
        'description': 'Monthly Lynis security audits',
        'category': 'security'
    },
    'lynis_audit_weekly': {
        'cost': 150,  # 150 WegCoins per device per month
        'description': 'Weekly Lynis security audits',
        'category': 'security'
    },
    'compliance_reporting': {
        'cost': 100,  # 100 WegCoins per month
        'description': 'Automated compliance reporting (ISO27001, PCI-DSS, HIPAA)',
        'category': 'security'
    },
    'security_dashboard': {
        'cost': 200,  # 200 WegCoins per month
        'description': 'Advanced security analytics dashboard',
        'category': 'security'
    }
}
```

### Feature Gating

**File:** `app/utilities/feature_flags.py`

```python
def has_lynis_access(device_uuid=None, tenant_uuid=None):
    """
    Check if device or tenant has access to Lynis auditing
    
    Returns:
        bool: True if access is granted, False otherwise
    """
    from app.models import WegCoinsUsage, Tenants, Devices
    
    # Get tenant UUID if only device UUID provided
    if device_uuid and not tenant_uuid:
        device = Devices.query.get(device_uuid)
        if device:
            tenant_uuid = device.tenantuuid
    
    if not tenant_uuid:
        return False
    
    # Check if tenant has active Lynis subscription
    active_subscription = WegCoinsUsage.query.filter_by(
        tenantuuid=tenant_uuid,
        feature='lynis_audit_monthly',
        active=True
    ).first()
    
    if active_subscription:
        return True
    
    # Check for trial period (first 30 days free)
    tenant = Tenants.query.get(tenant_uuid)
    if tenant:
        account_age_days = (datetime.utcnow() - datetime.fromtimestamp(tenant.created_at)).days
        if account_age_days <= 30:
            return True
    
    return False


def get_lynis_audit_frequency(tenant_uuid):
    """
    Get the configured audit frequency for a tenant
    
    Returns:
        str: 'weekly', 'monthly', or None if not subscribed
    """
    from app.models import WegCoinsUsage
    
    weekly = WegCoinsUsage.query.filter_by(
        tenantuuid=tenant_uuid,
        feature='lynis_audit_weekly',
        active=True
    ).first()
    
    if weekly:
        return 'weekly'
    
    monthly = WegCoinsUsage.query.filter_by(
        tenantuuid=tenant_uuid,
        feature='lynis_audit_monthly',
        active=True
    ).first()
    
    if monthly:
        return 'monthly'
    
    return None
```

### Update Agent Script to Check Access

Add feature gating to the agent script snippet:

```python
# Add to the beginning of the Lynis script (after imports)

def check_feature_access(deviceUuid, host):
    """Check if this device has access to Lynis auditing"""
    url = f'https://{host}/api/features/check/lynis_audit'
    headers = {'Content-Type': 'application/json'}
    body = {'deviceuuid': deviceUuid}
    
    try:
        response = requests.post(url, headers=headers, data=json.dumps(body), timeout=10)
        if response.status_code == 200:
            data = response.json()
            return data.get('access', False)
        else:
            logger.warning(f"Feature access check returned: {response.status_code}")
            return False
    except Exception as e:
        logger.error(f"Error checking feature access: {e}")
        return False

# Then in main execution, before install_lynis():
if not check_feature_access(deviceUuid, host):
    logger.info("Lynis auditing not enabled for this device. Upgrade to premium for security audits.")
    print("INFO: Lynis security auditing requires a premium subscription")
    sys.exit(0)  # Exit gracefully, not an error
```

### API Endpoint for Feature Check

**File:** `app/routes/api.py`

```python
@api_bp.route('/features/check/<feature_name>', methods=['POST'])
def check_feature_access(feature_name):
    """
    Check if a device has access to a specific feature
    
    POST /api/features/check/lynis_audit
    Body: {"deviceuuid": "xxx-xxx-xxx"}
    
    Returns: {"access": true/false, "reason": "..."}
    """
    data = request.get_json()
    deviceuuid = data.get('deviceuuid')
    
    if not deviceuuid:
        return jsonify({'access': False, 'reason': 'No device UUID provided'}), 400
    
    # Get device and tenant
    device = Devices.query.get(deviceuuid)
    if not device:
        return jsonify({'access': False, 'reason': 'Device not found'}), 404
    
    # Check access based on feature
    if feature_name == 'lynis_audit':
        access = has_lynis_access(device_uuid=deviceuuid, tenant_uuid=device.tenantuuid)
        
        if access:
            frequency = get_lynis_audit_frequency(device.tenantuuid)
            return jsonify({
                'access': True,
                'frequency': frequency,
                'reason': f'Active subscription: {frequency} audits'
            })
        else:
            return jsonify({
                'access': False,
                'reason': 'No active Lynis subscription. Upgrade to premium.'
            })
    
    return jsonify({'access': False, 'reason': 'Unknown feature'}), 400
```

---

## Maintenance & Operations

### Scheduled Maintenance Tasks

**Weekly:**
- Review audit success rates
- Check for Lynis updates
- Monitor storage usage for audit data
- Review critical findings across all devices

**Monthly:**
- Generate compliance reports
- Analyze security trends
- Update Lynis on all devices
- Review and update AI prompt if needed

**Quarterly:**
- Comprehensive security posture review
- Update compliance mappings
- Customer security briefings
- Feature enhancement planning

### Troubleshooting Guide

#### Issue: Lynis Installation Fails

**Symptoms:** Agent reports "Failed to install Lynis"

**Diagnosis:**
```bash
# On affected device
cd /opt/Wegweiser
git clone https://github.com/CISOfy/lynis.git test-lynis
```

**Solutions:**
1. Check internet connectivity
2. Verify Git is installed: `which git`
3. Check disk space: `df -h /opt`
4. Check permissions: `ls -la /opt/Wegweiser`
5. Check firewall rules for GitHub access

#### Issue: Audit Times Out

**Symptoms:** Lynis audit doesn't complete within 5 minutes

**Diagnosis:**
```bash
# Run manually
/opt/Wegweiser/lynis/lynis audit system --quick
```

**Solutions:**
1. Increase timeout in script (line 139)
2. Use `--quick` flag to skip slow tests
3. Check CPU load during audit
4. Consider scheduling during off-peak hours

#### Issue: AI Analysis Not Generated

**Symptoms:** Data collected but no AI analysis

**Diagnosis:**
```sql
SELECT 
    deviceuuid,
    metalogos_type,
    length(metalogos) as data_size,
    ai_analysis IS NULL as missing_analysis
FROM devicemetadata
WHERE metalogos_type = 'lynis-audit'
ORDER BY created_at DESC
LIMIT 10;
```

**Solutions:**
1. Check Azure OpenAI API status
2. Review Wegweiser logs for AI errors
3. Verify prompt file exists and is valid
4. Check API rate limits
5. Manually trigger AI analysis via admin UI

#### Issue: Security Score Not Updating

**Symptoms:** Device health score doesn't include security component

**Diagnosis:**
```sql
SELECT 
    d.devicename,
    d.health_score,
    dm.score as security_score
FROM devices d
LEFT JOIN devicemetadata dm ON d.deviceuuid = dm.deviceuuid
WHERE dm.metalogos_type = 'lynis-audit'
ORDER BY dm.created_at DESC;
```

**Solutions:**
1. Verify health score calculation includes Lynis
2. Trigger manual health score recalculation
3. Check if score is NULL in database
4. Review health score calculation logs

#### Issue: UI Not Displaying Report

**Symptoms:** Security Audit tab shows loading spinner indefinitely

**Diagnosis:**
```javascript
// In browser console
fetch('/ui/device/DEVICE_UUID/eventlog/lynis-audit')
  .then(r => r.text())
  .then(console.log)
```

**Solutions:**
1. Check browser console for JavaScript errors
2. Verify API endpoint returns data
3. Check CORS settings if applicable
4. Clear browser cache
5. Verify user permissions for device access

### Backup & Recovery

**What to Backup:**
- `/opt/Wegweiser/lynis/` directory (on devices)
- DeviceMetadata table (lynis-audit entries)
- AI analysis results
- Compliance reports

**Backup Schedule:**
- Database: Hourly (included in standard backups)
- Lynis directory: Not necessary (can re-download)
- Reports: Weekly

**Recovery Procedure:**
1. Restore database from backup
2. Re-install Lynis on affected devices
3. Re-run audits if needed
4. Regenerate reports from stored data

---

## Security Considerations

### Data Privacy

**Lynis Output May Contain:**
- System configurations
- User account information
- Network topology
- Installed software inventory
- Security vulnerabilities

**Privacy Measures:**
- Store data encrypted at rest
- Limit access via RBAC
- Anonymize in reports when possible
- Comply with data retention policies
- Include in data processing agreements

### Compliance Requirements

**GDPR Considerations:**
- Lynis data may contain personal data
- Ensure proper consent from device owners
- Provide data export/deletion capabilities
- Document data processing activities

**Industry-Specific:**
- Healthcare: Ensure HIPAA compliance
- Finance: Meet PCI-DSS requirements
- Government: Consider FedRAMP requirements

### Access Control

**Who Should Access Security Audits:**
- ✅ MSP security team
- ✅ MSP management
- ✅ Client security officers (with permission)
- ✅ Compliance auditors (with authorization)
- ❌ General MSP technicians (without training)
- ❌ Client end-users

**Implement Role-Based Access:**
```python
# Example access control
REQUIRED_ROLE_FOR_SECURITY = ['admin', 'security_analyst', 'compliance_officer']

@ui_bp.route('/device/<deviceuuid>/eventlog/lynis-audit')
@login_required
@role_required(REQUIRED_ROLE_FOR_SECURITY)
def get_security_audit(deviceuuid):
    # ... existing code
```

---

## Future Enhancements

### Phase 4: Advanced Features (Future)

**Automated Remediation:**
- Ansible playbooks for common fixes
- One-click remediation for simple issues
- Scheduled remediation windows
- Rollback capabilities

**Trend Analysis:**
- Security posture over time
- Comparative analysis across devices
- Predictive security alerts
- Benchmark against industry standards

**Integration Enhancements:**
- SIEM integration (Splunk, ELK)
- Ticketing system integration (Jira, ServiceNow)
- Slack/Teams notifications for critical findings
- Custom compliance framework support

**Reporting Improvements:**
- Executive dashboards
- Automated monthly security reports
- Client-facing security portals
- Compliance certification packages

**Machine Learning:**
- Anomaly detection in security trends
- Predictive vulnerability identification
- Automated false positive reduction
- Risk scoring refinement

---

## Success Metrics

### Technical Metrics
- **Audit Coverage:** % of devices with recent audits
- **Success Rate:** % of audits completing successfully
- **Average Score:** Mean security score across all devices
- **Critical Findings:** Number of critical issues identified
- **Time to Remediation:** Average time to fix issues

### Business Metrics
- **Feature Adoption:** % of customers using Lynis
- **WegCoins Revenue:** Revenue from security features
- **Customer Satisfaction:** NPS score for security features
- **Compliance Value:** Number of compliance reports generated
- **Competitive Advantage:** Win rate vs competitors

### Target Goals (6 months)
- 80% audit coverage across all Linux/macOS devices
- 95% audit success rate
- Average security score improvement of 15 points
- 90% of critical findings remediated within 7 days
- 50% of customers subscribed to security features

---

## Support & Documentation

### User Documentation

**Create these documents:**

1. **Admin Guide:**
   - How to deploy Lynis to devices
   - How to schedule audits
   - How to interpret results
   - Troubleshooting common issues

2. **MSP Technician Guide:**
   - Understanding security scores
   - Remediation procedures
   - Escalation criteria
   - Best practices

3. **Client-Facing:**
   - What is Lynis auditing
   - Why security audits matter
   - How to read reports
   - FAQ

### Training Materials

**Create training modules for:**
- MSP security team
- MSP technicians
- Sales team (for upselling)
- Customers (optional)

### Support Channels

**Establish:**
- Internal documentation wiki
- Video tutorials
- Regular training webinars
- Dedicated Slack/Teams channel for questions
- Email support for premium features

---

## Conclusion

This comprehensive guide provides everything needed to successfully integrate Lynis security auditing into Wegweiser. The integration leverages existing infrastructure, respects the GPL v3 license, and provides significant value to MSPs and their clients.

### Key Takeaways

1. **No Distribution Issues:** Devices download Lynis directly from GitHub
2. **Leverages Existing Architecture:** Uses current DeviceMetadata system
3. **Premium Revenue Opportunity:** WegCoins-based monetization
4. **Compliance Value:** Automated ISO27001/PCI-DSS/HIPAA checking
5. **Competitive Advantage:** Security + monitoring in one platform

### Next Steps

1. ✅ Review this document thoroughly
2. ✅ Set up development environment
3. ✅ Deploy Phase 1 (Core Integration)
4. ✅ Test with beta customers
5. ✅ Deploy Phase 2 (AI Analysis)
6. ✅ Deploy Phase 3 (UI & Reporting)
7. ✅ Launch to all customers
8. ✅ Monitor, iterate, and improve

### Questions or Issues?

- Review the Troubleshooting section
- Check Lynis official documentation: https://cisofy.com/lynis/
- Consult GPL v3 license: https://www.gnu.org/licenses/gpl-3.0.en.html
- Contact Wegweiser development team

---

**Document Version:** 1.0  
**Last Updated:** 2025-10-25  
**Author:** Wegweiser Development Team  
**Status:** Ready for Implementation

---

## Appendix A: Complete File Checklist

Files to create or modify:

**New Files:**
- [ ] `app/tasks/security/prompts/lynis.prompt` - AI analysis prompt
- [ ] Agent script via admin UI - Lynis audit collection
- [ ] `app/utilities/health_score.py` - Health score integration (may exist)
- [ ] `app/utilities/feature_flags.py` - Feature gating (may exist)

**Existing Files to Verify (No Changes Needed):**
- [ ] `app/routes/ai.py` - Metadata endpoint
- [ ] `app/routes/ui.py` - Event log display
- [ ] `app/models.py` - DeviceMetadata model
- [ ] `app/templates/devices/device_detail.html` - Add security tab

**Configuration Files:**
- [ ] Update WegCoins pricing
- [ ] Update feature flags configuration
- [ ] Update documentation

## Appendix B: SQL Queries Reference

**Check Lynis Data:**
```sql
SELECT 
    d.devicename,
    dm.metalogos_type,
    dm.score,
    length(dm.metalogos) as data_size,
    to_timestamp(dm.created_at) as audit_time
FROM devicemetadata dm
JOIN devices d ON dm.deviceuuid = d.deviceuuid
WHERE dm.metalogos_type = 'lynis-audit'
ORDER BY dm.created_at DESC
LIMIT 20;
```

**Security Score Distribution:**
```sql
SELECT 
    CASE 
        WHEN score >= 90 THEN 'A (90-100)'
        WHEN score >= 80 THEN 'B (80-89)'
        WHEN score >= 70 THEN 'C (70-79)'
        WHEN score >= 60 THEN 'D (60-69)'
        ELSE 'F (0-59)'
    END as grade,
    COUNT(*) as device_count
FROM devicemetadata
WHERE metalogos_type = 'lynis-audit'
AND created_at > EXTRACT(EPOCH FROM NOW() - INTERVAL '30 days')
GROUP BY grade
ORDER BY grade;
```

**Critical Findings Report:**
```sql
SELECT 
    d.devicename,
    o.orgname,
    dm.score,
    to_timestamp(dm.created_at) as last_audit
FROM devicemetadata dm
JOIN devices d ON dm.deviceuuid = d.deviceuuid
JOIN groups g ON d.groupuuid = g.groupuuid
JOIN organisations o ON g.orguuid = o.orguuid
WHERE dm.metalogos_type = 'lynis-audit'
AND dm.score < 60
ORDER BY dm.score ASC;
```

## Appendix C: Lynis Command Reference

**Basic Commands:**
```bash
# Full audit
./lynis audit system

# Quick audit (skip slow tests)
./lynis audit system --quick

# Quiet mode (less output)
./lynis audit system --quiet

# Non-interactive mode
./lynis audit system --quick --quiet

# Check version
./lynis --version

# Update Lynis
git pull

# View last audit report
cat /var/log/lynis-report.dat

# View detailed log
cat /var/log/lynis.log
```

**Report Locations:**
- Main log: `/var/log/lynis.log`
- Report data: `/var/log/lynis-report.dat`
- Archives: `/var/log/lynis/`

---

## END OF DOCUMENT

This implementation guide is complete and ready for use with Claude Code or manual implementation.
