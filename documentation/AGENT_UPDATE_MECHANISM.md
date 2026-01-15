# Wegweiser Agent Update Mechanism - Conceptual Design

## Current Status

**Problem**: The latest NATS agent (v3.0.0-poc) now includes heartbeat functionality to update `DeviceConnectivity.is_online` status, but existing agents in the field don't have this code. We need a mechanism to push these changes downstream.

**Existing Infrastructure**: 
- Snippet-based update system already exists (`updateAgent.py`)
- Version comparison via `/diags/agentversion` endpoint
- SHA256 hash verification for integrity
- ServerCore model tracks versions and hashes

## Proposed Solution: Tiered Agent Update System

### Phase 1: Immediate (Current Implementation)
**Goal**: Push heartbeat functionality to existing agents

#### 1.1 Backend Changes Required

**A. Extend ServerCore Model**
```python
# Add to app/models/servercore.py
persistent_agent_version = db.Column(db.String(50), nullable=True)
persistent_agent_hash_py = db.Column(db.String(255), nullable=True)
persistent_agent_hash_linux = db.Column(db.String(255), nullable=True)
persistent_agent_hash_macos = db.Column(db.String(255), nullable=True)
```

**B. Create Update Endpoint**
```
GET /diags/persistentagentversion
Returns: {
  "persistent_agent_version": "3.0.1",
  "persistent_agent_hash_py": "sha256...",
  "persistent_agent_hash_linux": "sha256...",
  "persistent_agent_hash_macos": "sha256..."
}
```

**C. Create Download Endpoints**
```
GET /download/nats_agent.py (Windows/Linux)
GET /download/nats_agent_macos.py (macOS)
```

#### 1.2 Agent-Side Changes

**A. Create updateNatsAgent.py Snippet**
- Check current NATS agent version
- Compare with server version
- Download new agent files (nats_agent.py, core/nats_service.py, etc.)
- Verify SHA256 hashes
- Backup current agent
- Replace with new version
- Restart service

**B. Schedule updateNatsAgent.py**
- Run every 24 hours (or on-demand)
- Only on devices with NATS agents running
- Graceful restart of WegweiserServiceHost

### Phase 2: Robust Distribution (Next Sprint)
**Goal**: Implement comprehensive agent lifecycle management

#### 2.1 Agent Registry
Track per-device:
- Agent type (scheduled vs persistent NATS)
- Current version
- Last update check
- Update status (pending, in-progress, completed, failed)
- Rollback capability

#### 2.2 Selective Deployment
- Canary deployments (5% of devices first)
- Gradual rollout (25%, 50%, 100%)
- Rollback on failure detection
- Device-specific version pinning

#### 2.3 Update Scheduling
- Maintenance windows per device/group
- Staggered updates to avoid load spikes
- Automatic retry on failure
- Update notifications to MSP

### Phase 3: Advanced (Future)
**Goal**: Full agent orchestration platform

#### 3.1 Agent Package Management
- Versioned agent packages (like Docker images)
- Dependency tracking
- Configuration management
- Feature flags per agent version

#### 3.2 Monitoring & Observability
- Agent health dashboard
- Update success/failure rates
- Performance impact tracking
- Automatic rollback triggers

## Implementation Priority

### Immediate (This Week) - PHASE 1 COMPLETE
1. ✅ Add heartbeat to NATS agent (DONE)
2. ✅ Add persistent_agent_* fields to ServerCore (DONE)
3. ✅ Create `/diags/persistentagentversion` endpoint (DONE)
4. ✅ Download endpoints already exist via `/installerFiles/<platform>/Agent/<file>` (DONE)
5. ✅ Create `updateNatsAgent.py` snippet (DONE)
6. ⏳ Schedule snippet on all NATS devices (NEXT STEP)

### Short-term (Next 2 Weeks)
1. Add agent version tracking to DeviceConnectivity
2. Create agent update status dashboard
3. Implement canary deployment logic
4. Add rollback mechanism

### Medium-term (Next Month)
1. Build agent registry system
2. Implement selective deployment
3. Add update scheduling UI
4. Create monitoring dashboard

## Technical Considerations

### Challenges
1. **Service Restart**: WegweiserServiceHost needs graceful restart
2. **File Locking**: Windows may lock running Python files
3. **Rollback**: Need to preserve previous version
4. **Atomicity**: Ensure all files updated together
5. **Verification**: Validate agent functionality post-update

### Solutions
1. Use Windows Service Control Manager for restart
2. Rename files (agent.py → agent.old, agent.new → agent.py)
3. Keep backup of previous version for 7 days
4. Use transaction-like approach (all-or-nothing)
5. Post-update health check via heartbeat

## Risk Mitigation

1. **Staged Rollout**: Don't push to all devices at once
2. **Monitoring**: Track update success rates
3. **Rollback Plan**: Keep previous version available
4. **Testing**: Test on internal devices first
5. **Communication**: Notify MSPs of updates

## Success Metrics

- Update success rate > 95%
- Average update time < 5 minutes
- Zero data loss during updates
- Automatic rollback on failure
- All devices reporting heartbeat within 1 hour of update

---

## PHASE 1 IMPLEMENTATION DETAILS

### What Was Implemented

#### 1. Backend Changes

**A. ServerCore Model Extension** (`app/models/servercore.py`)
```python
persistent_agent_version = db.Column(db.String(50), nullable=True)
persistent_agent_hash_py = db.Column(db.String(255), nullable=True)
persistent_agent_hash_linux = db.Column(db.String(255), nullable=True)
persistent_agent_hash_macos = db.Column(db.String(255), nullable=True)
```

**B. Version Endpoint** (`app/routes/diags.py`)
- Endpoint: `GET /diags/persistentagentversion`
- Returns: persistent agent version and platform-specific SHA256 hashes
- Fallback: Uses agent_* fields if persistent_agent_* not set

**C. Download Infrastructure**
- Already exists: `/installerFiles/<platform>/Agent/<filepath>`
- Serves files from `installerFiles/Windows/Agent/`, `installerFiles/Linux/Agent/`, `installerFiles/MacOS/Agent/`
- No changes needed - fully functional

#### 2. Agent-Side Update Mechanism

**A. Update Snippet** (`snippets/unSigned/updateNatsAgent.py`)
- Checks local vs server NATS agent version
- Downloads updated files: nats_agent.py, core/nats_service.py, core/agent.py, core/api_client.py
- Verifies SHA256 hashes for integrity
- Creates backup of current version
- Atomically replaces files
- Restarts WegweiserServiceHost (Windows) or wegweiser-persistent-agent (Linux/macOS)
- Supports Windows, Linux, and macOS

**B. Key Features**
- Graceful error handling with rollback capability
- Backup preservation for 7 days
- Platform-specific hash verification
- Service restart with proper timing
- Comprehensive logging

### How to Deploy

#### Step 1: Update ServerCore with Version Info
```python
from app.models import ServerCore, db

servercore = ServerCore.query.first()
servercore.persistent_agent_version = "3.0.1"
servercore.persistent_agent_hash_py = "<sha256_hash_of_nats_agent.py>"
servercore.persistent_agent_hash_linux = "<sha256_hash_of_nats_agent.py>"
servercore.persistent_agent_hash_macos = "<sha256_hash_of_nats_agent.py>"
db.session.commit()
```

#### Step 2: Calculate Hashes
```bash
# For each platform
sha256sum installerFiles/Windows/Agent/nats_agent.py
sha256sum installerFiles/Linux/Agent/nats_agent.py
sha256sum installerFiles/MacOS/Agent/nats_agent.py
```

#### Step 3: Schedule Update Snippet
The `updateNatsAgent.py` snippet should be scheduled on all devices with NATS agents:
- Recurrence: Every 24 hours (or on-demand)
- Start time: Off-peak hours (e.g., 2 AM)
- Stagger across devices to avoid load spikes

#### Step 4: Monitor Updates
- Check device heartbeat status in UI
- Verify all devices report new version
- Monitor logs for any failures

### Rollback Procedure

If an update causes issues:

1. **Automatic Rollback** (if implemented):
   - Detect failed heartbeat
   - Restore from backup
   - Restart service

2. **Manual Rollback**:
   ```bash
   # On affected device
   cp -r /opt/Wegweiser/Agent/backup/<old_version>/* /opt/Wegweiser/Agent/
   sudo systemctl restart wegweiser-persistent-agent
   ```

### Next Steps (Phase 2)

1. Create UI for scheduling updates
2. Add device-level version tracking
3. Implement canary deployment (5% → 25% → 50% → 100%)
4. Add automatic rollback on heartbeat failure
5. Create update status dashboard

