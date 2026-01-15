# Lynis Security Audit Integration Plan

## Current Status: Parser Created, Not Yet Integrated

**What Exists:**
- ✅ Lynis audit execution via snippet system (`snippets/00000000.../fullAudit.json`)
- ✅ Python parser (`app/utilities/lynis_parser.py`)
- ✅ Raw JSON output saved to `tmp/lynis_results.json`
- ❌ No database storage
- ❌ No UI rendering
- ❌ No health score integration
- ❌ No historical tracking

---

## Lynis Health Score Data Structure

Lynis provides a **single overall health score** rather than per-test scores:

```json
{
  "hardening_index": 67,           // 0-100 scale - PRIMARY HEALTH SCORE
  "tests_performed": 259,
  "warnings": [],                  // Critical issues (count: 0)
  "suggestions": [                 // 66 improvement recommendations
    "AUTH-9230|Configure password hashing rounds...",
    "KRNL-5788|Determine why /vmlinuz is missing...",
    ...
  ]
}
```

**Key Categories in Suggestions:**
- **AUTH** (Authentication) - 12 suggestions
- **KRNL** (Kernel) - 6 suggestions
- **FILE** (File Permissions) - 8 suggestions
- **NETW** (Networking) - 8 suggestions
- **ACCT** (Accounting/Audit) - 6 suggestions
- **HRDN** (Hardening) - 4 suggestions
- **MACF** (Mandatory Access Control) - 2 suggestions
- **FINT** (File Integrity) - 2 suggestions
- **LOGG** (Logging) - 2 suggestions
- Plus: BOOT, BANN, PKGS, USB, NAME, TOOL

---

## Integration into Wegweiser's Health Scoring Architecture

### Hierarchical Position

```
Tenant (MSP)
  └─ Organization (Client)
      └─ Device
          ├─ Task Analysis 1: Hardware Health Score
          ├─ Task Analysis 2: Auth Health Score
          ├─ Task Analysis 3: Network Health Score
          └─ Task Analysis 4: LYNIS SECURITY AUDIT SCORE (NEW)
```

**Lynis Integration Point:**
- **Level**: Device-level task analysis
- **Score Source**: `hardening_index` (0-100 scale) maps directly to Wegweiser's 1-100 health score
- **Aggregation**: Contributes to overall device health score alongside other task analyses

---

## Implementation Plan

### Phase 1: Database Schema (High Priority)

#### New Table: `lynis_audit_results`

```python
class LynisAuditResult(db.Model):
    __tablename__ = 'lynis_audit_results'

    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    device_id = db.Column(UUID(as_uuid=True), db.ForeignKey('devices.id'), nullable=False)
    tenant_id = db.Column(UUID(as_uuid=True), db.ForeignKey('tenants.id'), nullable=False)

    # Core Metrics
    hardening_index = db.Column(db.Integer, nullable=False)  # 0-100
    tests_performed = db.Column(db.Integer)
    warnings_count = db.Column(db.Integer, default=0)
    suggestions_count = db.Column(db.Integer, default=0)

    # System Info
    hostname = db.Column(db.String(255))
    os = db.Column(db.String(100))
    os_version = db.Column(db.String(100))
    lynis_version = db.Column(db.String(50))

    # Timestamp
    scan_timestamp = db.Column(db.DateTime, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Detailed Results (JSON)
    warnings = db.Column(JSON)  # List of warning dicts
    suggestions_by_category = db.Column(JSON)  # Categorized suggestions
    full_results = db.Column(JSON)  # Complete parsed data

    # Relationships
    device = db.relationship('Device', backref='lynis_audits')
    tenant = db.relationship('Tenant')
```

#### Migration Command:
```bash
flask db migrate -m "Add Lynis audit results table"
flask db upgrade
```

---

### Phase 2: Server-Side Ingestion (High Priority)

#### New Route: `/api/devices/<device_id>/lynis/ingest`

**Purpose**: Accept Lynis JSON from agent, parse, store, and create health score

```python
# app/routes/devices/lynis.py

from flask import Blueprint, request, jsonify
from app.utilities.lynis_parser import LynisResultParser
from app.models import Device, LynisAuditResult
from app.tasks.lynis_analysis import analyze_lynis_results
import tempfile

lynis_bp = Blueprint('lynis', __name__)

@lynis_bp.route('/devices/<device_id>/lynis/ingest', methods=['POST'])
@login_required
@permission_required('device.view')
def ingest_lynis_results(device_id: str):
    """
    Accept Lynis JSON results from agent, parse, and store.

    Expected payload: { "results": "{ ... lynis json ... }" }
    """
    device = Device.query.get_or_404(device_id)

    # Ensure tenant isolation
    if device.tenant_id != current_user.tenant_id:
        abort(403)

    # Get JSON from request
    lynis_json = request.json.get('results')
    if not lynis_json:
        return jsonify({'error': 'Missing results'}), 400

    # Parse with temporary file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump(lynis_json, f)
        temp_path = f.name

    try:
        parser = LynisResultParser(temp_path)
        summary = parser.get_summary()
        suggestions = parser.get_suggestions_by_category()
        warnings = parser.get_warnings()

        # Store in database
        audit_result = LynisAuditResult(
            device_id=device.id,
            tenant_id=device.tenant_id,
            hardening_index=summary['hardening_index'],
            tests_performed=summary['tests_performed'],
            warnings_count=summary['warnings_count'],
            suggestions_count=summary['suggestions_count'],
            hostname=summary['hostname'],
            os=summary['os'],
            os_version=summary['os_version'],
            lynis_version=summary['lynis_version'],
            scan_timestamp=summary['timestamp'],
            warnings=warnings,
            suggestions_by_category=suggestions,
            full_results=parser.raw_data
        )

        db.session.add(audit_result)
        db.session.commit()

        # Trigger async AI analysis task
        analyze_lynis_results.delay(audit_result.id)

        return jsonify({
            'status': 'success',
            'audit_id': str(audit_result.id),
            'hardening_index': audit_result.hardening_index
        }), 201

    finally:
        os.unlink(temp_path)
```

---

### Phase 3: Health Score Integration (Critical)

#### New Celery Task: `app/tasks/lynis_analysis.py`

```python
from app import celery
from app.models import LynisAuditResult, Device, HealthScoreHistory
from app.utilities.ai_analyzer import analyze_security_posture

@celery.task(name='tasks.analyze_lynis_results')
def analyze_lynis_results(audit_id: str):
    """
    AI-powered analysis of Lynis results with health score contribution.

    Creates:
    1. HealthScoreHistory entry (contributes to device health)
    2. AI-generated security posture summary
    3. Prioritized remediation recommendations
    """
    audit = LynisAuditResult.query.get(audit_id)
    if not audit:
        return

    device = audit.device

    # Map Lynis hardening_index (0-100) to Wegweiser health score (1-100)
    # Note: Lynis uses 0-100, Wegweiser uses 1-100
    health_score = max(1, audit.hardening_index)

    # Determine severity based on score
    if health_score >= 80:
        severity = 'info'
        severity_level = 1
    elif health_score >= 60:
        severity = 'warning'
        severity_level = 2
    elif health_score >= 40:
        severity = 'error'
        severity_level = 3
    else:
        severity = 'critical'
        severity_level = 4

    # AI-powered analysis using compact payload
    from app.utilities.lynis_parser import LynisResultParser
    parser = LynisResultParser(None)
    parser.raw_data = audit.full_results

    ai_payload = parser.get_ai_summary_payload()

    # Generate AI summary
    ai_summary = analyze_security_posture(
        device_id=device.id,
        lynis_data=ai_payload,
        hardening_score=health_score
    )

    # Create HealthScoreHistory entry
    health_entry = HealthScoreHistory(
        device_id=device.id,
        tenant_id=device.tenant_id,
        task_type='security_audit',
        task_name='Lynis Security Audit',
        health_score=health_score,
        severity=severity,
        severity_level=severity_level,
        summary=ai_summary['summary'],
        details={
            'audit_id': str(audit.id),
            'warnings_count': audit.warnings_count,
            'suggestions_count': audit.suggestions_count,
            'critical_categories': ai_summary['critical_categories'],
            'top_recommendations': ai_summary['top_recommendations'][:5]
        },
        raw_data=ai_payload  # Token-efficient version only
    )

    db.session.add(health_entry)
    db.session.commit()

    # Trigger device health score recalculation
    from app.tasks.health_scores import update_device_health_score
    update_device_health_score.delay(device.id)

    return {
        'health_score': health_score,
        'severity': severity,
        'audit_id': str(audit.id)
    }
```

---

### Phase 4: UI Rendering (User Experience)

#### Device Detail Page Updates

**Add Security Tab**: `/devices/<device_id>`

```html
<!-- app/templates/devices/detail.html -->

<div class="tabs">
  <button class="tab" data-tab="overview">Overview</button>
  <button class="tab" data-tab="health">Health Scores</button>
  <button class="tab" data-tab="security">Security Audit</button>  <!-- NEW -->
  <button class="tab" data-tab="chat">AI Chat</button>
</div>

<div id="security-tab" class="tab-content">
  <div class="security-audit-header">
    <h2>Lynis Security Audit</h2>
    <div class="hardening-score">
      <div class="score-circle" data-score="{{ latest_audit.hardening_index }}">
        <span class="score-value">{{ latest_audit.hardening_index }}</span>
        <span class="score-label">/100</span>
      </div>
      <div class="score-details">
        <p>Last Scan: {{ latest_audit.scan_timestamp | format_datetime }}</p>
        <p>{{ latest_audit.suggestions_count }} recommendations</p>
        <p>{{ latest_audit.warnings_count }} warnings</p>
      </div>
    </div>
  </div>

  <!-- Quick Summary -->
  <div class="audit-summary">
    <h3>Security Posture Summary</h3>
    <div class="ai-summary">
      {{ health_score_entry.summary | markdown }}
    </div>
  </div>

  <!-- Suggestions by Category -->
  <div class="suggestions-by-category">
    <h3>Findings by Category</h3>
    {% for category, suggestions in latest_audit.suggestions_by_category.items() %}
    <div class="category-card">
      <div class="category-header" onclick="toggleCategory('{{ category }}')">
        <span class="category-name">{{ category_names[category] }}</span>
        <span class="badge">{{ suggestions | length }}</span>
      </div>
      <div id="category-{{ category }}" class="category-content collapsed">
        <ul class="suggestions-list">
          {% for suggestion in suggestions %}
          <li>
            <span class="test-id">{{ suggestion.test_id }}</span>
            <span class="message">{{ suggestion.message }}</span>
            {% if suggestion.solution and suggestion.solution != '-' %}
            <div class="solution">
              <strong>Solution:</strong> {{ suggestion.solution }}
            </div>
            {% endif %}
          </li>
          {% endfor %}
        </ul>
      </div>
    </div>
    {% endfor %}
  </div>

  <!-- View Full Report Button -->
  <button class="btn-secondary" onclick="showFullReport('{{ latest_audit.id }}')">
    View Full Technical Report
  </button>
</div>
```

#### Modal: Full Technical Report

**Endpoint**: `/api/devices/<device_id>/lynis/<audit_id>/report`

```javascript
// app/static/js/lynis_viewer.js

function showFullReport(auditId) {
  fetch(`/api/devices/${deviceId}/lynis/${auditId}/report`)
    .then(response => response.json())
    .then(data => {
      const modal = createModal('Lynis Security Audit - Full Report');

      // Render formatted report
      const reportHtml = `
        <div class="lynis-full-report">
          <pre>${data.human_readable_report}</pre>
        </div>
      `;

      modal.setContent(reportHtml);
      modal.show();
    });
}
```

---

### Phase 5: Historical Tracking & Trends

#### Audit History View

**Route**: `/devices/<device_id>/security/history`

Show hardening index trend over time:

```python
@lynis_bp.route('/devices/<device_id>/security/history', methods=['GET'])
@login_required
def security_history(device_id: str):
    """Show historical trend of Lynis audits."""
    device = Device.query.get_or_404(device_id)

    audits = LynisAuditResult.query.filter_by(
        device_id=device.id,
        tenant_id=current_user.tenant_id
    ).order_by(LynisAuditResult.scan_timestamp.desc()).limit(10).all()

    # Prepare chart data
    chart_data = {
        'labels': [a.scan_timestamp.strftime('%Y-%m-%d') for a in audits],
        'scores': [a.hardening_index for a in audits],
        'suggestions': [a.suggestions_count for a in audits],
        'warnings': [a.warnings_count for a in audits]
    }

    return render_template('devices/security_history.html',
                         device=device,
                         audits=audits,
                         chart_data=chart_data)
```

---

## Agent Integration

### Modify Agent Upload Logic

**Current**: Agent uploads to snippet system
**New**: Agent uploads directly to ingest endpoint

```python
# In agent script (agent/lynis_collector.py)

def upload_lynis_results(device_id: str, results: dict, api_url: str, api_key: str):
    """Upload Lynis results to Wegweiser API."""

    endpoint = f"{api_url}/api/devices/{device_id}/lynis/ingest"

    response = requests.post(
        endpoint,
        json={'results': results},
        headers={
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json'
        },
        timeout=30
    )

    if response.status_code == 201:
        data = response.json()
        print(f"✓ Lynis audit uploaded - Hardening Index: {data['hardening_index']}")
        return data['audit_id']
    else:
        print(f"✗ Upload failed: {response.status_code}")
        return None
```

---

## Open Questions & Decisions Needed

### 1. **Audit Frequency**
- How often should Lynis audits run?
- **Recommendation**: Weekly scheduled task (low overhead)

### 2. **Health Score Weight**
- How much should Lynis contribute to overall device health?
- **Recommendation**: Equal weight with other task analyses (hardware, auth, network)

### 3. **Remediation Workflow**
- Should we create actionable tasks from suggestions?
- **Recommendation**: Yes - integrate with task/ticket system

### 4. **AI Analysis Depth**
- Should AI analyze every suggestion or just critical categories?
- **Recommendation**: Focus AI on priority categories (AUTH, KRNL, ACCT, MACF, FIRE)

### 5. **Historical Data Retention**
- How many audit results to keep per device?
- **Recommendation**: Keep all audits, but only load last 10 for UI

---

## Success Metrics

**When fully implemented:**

✅ **Device Health Score** includes security posture (Lynis hardening index)
✅ **AI Chat** can reference security audit findings
✅ **Dashboard** shows security trends across devices/orgs
✅ **MSP** can see client security posture at a glance
✅ **Historical Tracking** shows improvement over time
✅ **Actionable Recommendations** surfaced to users

---

## Implementation Priority

**Phase 1** (High): Database schema
**Phase 2** (High): Ingest endpoint + parsing
**Phase 3** (Critical): Health score integration
**Phase 4** (Medium): UI rendering (tab + modal)
**Phase 5** (Low): Historical trends

**Estimated Effort**: 2-3 days for Phases 1-3, additional 1-2 days for full UI
