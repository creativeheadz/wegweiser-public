# Lynis Integration - Developer Quick Start

**Quick Reference for Wegweiser Developers**

---

## File Locations

### Core Implementation Files

```
app/tasks/lynis_audit/
├── analyzer.py          # LynisAuditAnalyzer class
├── definition.py        # ANALYSIS_CONFIG with WegCoins cost
└── prompts/lynis.prompt # AI analysis prompt template

app/utilities/
└── lynis_feature_flags.py    # Feature access control functions

app/routes/api/
└── lynis_features.py         # API endpoints (/api/lynis/*)

app/routes/ui.py              # Modified to support lynis-audit
```

### Documentation Files

```
ROOT/
├── LYNIS_INTEGRATION_GUIDE.md         # Comprehensive implementation guide
├── LYNIS_IMPLEMENTATION_SUMMARY.md    # What was implemented
├── LYNIS_AGENT_SCRIPT.md              # Agent script deployment guide
└── LYNIS_DEVELOPER_QUICK_START.md     # This file
```

---

## Quick Commands

### Test Feature Access

```python
from app.utilities.lynis_feature_flags import has_lynis_access, check_lynis_availability_for_device

# Check device access
has_access, reason = has_lynis_access(device_uuid="device-id")
print(f"Access: {has_access}, Reason: {reason}")

# Comprehensive check
has_access, details = check_lynis_availability_for_device("device-id")
print(details)
```

### Deploy Agent Script

1. Navigate to Admin UI → Snippets
2. Create New Snippet:
   - **Name**: Lynis Security Audit
   - **Type**: Python
   - **Platform**: Linux, macOS
   - **Schedule**: Weekly
   - **metalogos_type**: lynis-audit
3. Paste script from `LYNIS_AGENT_SCRIPT.md`
4. Assign to test devices

### Check Database

```sql
-- View latest Lynis audits
SELECT d.devicename, dm.score, dm.created_at
FROM devicemetadata dm
JOIN devices d ON dm.deviceuuid = d.deviceuuid
WHERE dm.metalogos_type = 'lynis-audit'
ORDER BY dm.created_at DESC
LIMIT 10;

-- Check for analysis failures
SELECT deviceuuid, metalogos_type, processing_status, created_at
FROM devicemetadata
WHERE metalogos_type = 'lynis-audit'
AND processing_status != 'processed'
ORDER BY created_at DESC;
```

---

## Key Classes & Functions

### LynisAuditAnalyzer

```python
from app.tasks.lynis_audit.analyzer import LynisAuditAnalyzer

# Instantiate
analyzer = LynisAuditAnalyzer(device_id="uuid", metadata_id="id")

# Get configuration
config = analyzer.config  # Returns ANALYSIS_CONFIG

# Get cost
cost = analyzer.get_cost()  # Returns 10 (WegCoins)

# Create prompt
prompt = analyzer.create_prompt(current_data, context)

# Parse response
result = analyzer.parse_response(ai_response)  # Returns {'analysis': html, 'score': int}
```

### Feature Flags

```python
from app.utilities.lynis_feature_flags import *

# Check access
has_access, reason = has_lynis_access(device_uuid="id")
has_access, reason = has_lynis_access(tenant_uuid="id")

# Get frequency
frequency = get_lynis_audit_frequency(tenant_uuid="id")  # 'weekly', 'monthly', or None

# Enable/Disable
success, msg = enable_lynis_for_tenant(tenant_uuid="id")
success, msg = disable_lynis_for_tenant(tenant_uuid="id")

# Get cost
cost = get_lynis_cost()  # Returns 10

# Comprehensive check
has_access, details = check_lynis_availability_for_device(device_uuid="id")
```

---

## API Endpoints

### Check Device Access

```bash
GET /api/lynis/check-access/<device_uuid>

Response (200):
{
    "access": true,
    "details": {
        "has_access": true,
        "access_message": "Access granted",
        "device_name": "server-01",
        "device_uuid": "...",
        "tenant_uuid": "...",
        "available_wegcoins": 150,
        "cost_per_audit": 10,
        "audit_frequency": "weekly",
        "os": "Linux"
    }
}
```

### Check Tenant Access

```bash
GET /api/lynis/tenant-access

Response (200):
{
    "access": true,
    "reason": "Access granted",
    "frequency": "weekly",
    "cost_per_audit": 10,
    "available_wegcoins": 150,
    "can_afford_one_audit": true,
    "tenant_uuid": "..."
}
```

### Enable Lynis

```bash
POST /api/lynis/enable

Response (200):
{
    "success": true,
    "message": "Lynis auditing enabled for tenant",
    "tenant_uuid": "..."
}
```

### Get Cost

```bash
GET /api/lynis/cost

Response (200):
{
    "cost": 10,
    "currency": "WegCoins",
    "description": "Cost per Lynis security audit"
}
```

---

## Configuration Examples

### Enable Lynis for a Tenant (Python)

```python
from flask import current_app
from app.utilities.lynis_feature_flags import enable_lynis_for_tenant

with current_app.app_context():
    success, message = enable_lynis_for_tenant("tenant-uuid")
    print(f"Success: {success}, Message: {message}")
```

### Modify Analysis Cost

Edit `app/tasks/lynis_audit/definition.py`:

```python
ANALYSIS_CONFIG = {
    "cost": 15,  # Change from 10 to 15 WegCoins
    ...
}
```

### Modify Schedule

Edit `app/tasks/lynis_audit/definition.py`:

```python
ANALYSIS_CONFIG = {
    "schedule": 259200,  # Change from 604800 (weekly) to 259200 (3 days)
    ...
}
```

---

## Debugging Tips

### Check Analyzer Registration

```python
from app.tasks.base.definitions import AnalysisDefinitions

# Load all definitions
AnalysisDefinitions.load_definitions()

# Get Lynis config
config = AnalysisDefinitions.get_config('lynis-audit')
print(config)

# Get cost
cost = AnalysisDefinitions.get_cost('lynis-audit')
print(f"Cost: {cost} WegCoins")
```

### Check Tenant Settings

```python
from app.models import Tenants

tenant = Tenants.query.get('tenant-uuid')
print(f"Has Lynis enabled: {tenant.analysis_toggles.get('lynis-audit', False)}")
print(f"Available WegCoins: {tenant.available_wegcoins}")
print(f"Analyses enabled: {tenant.recurring_analyses_enabled}")
```

### Monitor Processing Status

```sql
-- Check pending analyses
SELECT deviceuuid, metalogos_type, processing_status, created_at
FROM devicemetadata
WHERE metalogos_type = 'lynis-audit'
AND processing_status = 'pending'
ORDER BY created_at ASC;

-- Check processing errors
SELECT deviceuuid, metalogos_type, error_message, created_at
FROM devicemetadata
WHERE metalogos_type = 'lynis-audit'
AND processing_status = 'failed'
ORDER BY created_at DESC;
```

---

## Common Integration Points

### When Device Data is Received

The agent sends data to `/ai/device/metadata` which already handles `lynis-audit` type:

```python
# app/routes/ai/ai_device_metadata.py
new_metadata = DeviceMetadata(
    deviceuuid=device.deviceuuid,
    metalogos_type=data['metalogos_type'],  # 'lynis-audit'
    metalogos=data['metalogos'],            # Audit data JSON
    # ai_analysis and score set by analyzer
)
```

### When AI Analysis Runs

The Celery task automatically triggers the LynisAuditAnalyzer:

```python
# Analyzer is automatically discovered and instantiated
analyzer = LynisAuditAnalyzer(device_id, metadata_id)

# Analyzer generates prompt
prompt = analyzer.create_prompt(current_data, context)

# AI response is parsed
result = analyzer.parse_response(ai_response)

# Results are stored back to DeviceMetadata
```

### When Health Score Updates

Cascading update automatically includes Lynis score:

```sql
-- Device health score averages ALL metadata scores
UPDATE devices d
SET health_score = ds.avg_score
FROM (
    SELECT deviceuuid, ROUND(AVG(score)) as avg_score
    FROM devicemetadata
    WHERE processing_status = 'processed'
    AND score IS NOT NULL
    GROUP BY deviceuuid
) ds
WHERE d.deviceuuid = ds.deviceuuid
```

---

## Testing Workflows

### Test Feature Access

```bash
# 1. Check if device can run Lynis
curl -H "Authorization: Bearer <token>" \
  http://localhost:5000/api/lynis/check-access/device-uuid

# 2. Check if tenant has access
curl -H "Authorization: Bearer <token>" \
  http://localhost:5000/api/lynis/tenant-access

# 3. View audit report (after running)
curl -H "Authorization: Bearer <token>" \
  http://localhost:5000/ui/devices/device-uuid/eventlog/lynis-audit
```

### Simulate Audit Data

```python
from app.models import DeviceMetadata, Devices
from app import db

device = Devices.query.get('device-uuid')

# Create sample metadata
metadata = DeviceMetadata(
    deviceuuid=device.deviceuuid,
    metalogos_type='lynis-audit',
    metalogos=json.dumps({
        'hardening_index': 65,
        'tests_performed': 247,
        'warnings': ['Warning 1', 'Warning 2'],
        'suggestions': ['Fix 1', 'Fix 2']
    })
)
db.session.add(metadata)
db.session.commit()

# Trigger analyzer manually in Celery task
```

---

## Important Notes

1. **Database Schema**: No changes required - uses existing `DeviceMetadata` table
2. **Health Score**: Automatically averaged with other metadata scores
3. **OS Compatibility**: Linux and macOS only (Windows devices skip)
4. **WegCoins**: 10 per analysis (configurable in definition.py)
5. **Schedule**: Weekly by default (604800 seconds, configurable)
6. **License**: Lynis is GPL v3 - downloaded by customer devices, not Wegweiser

---

## Next Steps for Development

1. **Deploy to Test Device**
   - Create snippet in admin UI
   - Wait for agent check-in
   - Verify data in database

2. **Monitor Analysis Processing**
   - Check processing_status in DeviceMetadata
   - Review Celery logs for analyzer execution
   - Verify AI analysis generation

3. **Test UI Display**
   - Navigate to device details
   - Verify audit report displays
   - Check score formatting and badges

4. **Validate Health Scoring**
   - Confirm device health_score updates
   - Check cascading to groups/orgs/tenant
   - Verify score trends

---

**For detailed information, see:**
- Feature Implementation: `LYNIS_INTEGRATION_GUIDE.md`
- Implementation Summary: `LYNIS_IMPLEMENTATION_SUMMARY.md`
- Agent Deployment: `LYNIS_AGENT_SCRIPT.md`
