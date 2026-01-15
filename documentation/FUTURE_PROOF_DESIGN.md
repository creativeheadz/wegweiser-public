# Future-Proof Agent Update System Design

## Why This System Is Future-Proof

The agent update mechanism is designed as a **generic, extensible platform** that can handle ANY code changes to the agent, not just the current heartbeat functionality.

---

## Architecture Principles

### 1. **Model-Driven Design**
- **Single Source of Truth**: `app/models/servercore.py` defines what fields exist
- **Auto-Generated Migrations**: `flask db migrate` automatically detects model changes
- **No Manual SQL**: All schema changes go through the ORM

**Implication**: When you add new agent features, you just update the model and migrations are generated automatically.

### 2. **Version-Based Distribution**
- **Semantic Versioning**: `persistent_agent_version` (e.g., "3.0.1", "3.1.0", "4.0.0")
- **Platform-Specific Hashes**: Each platform has its own hash for security
- **Atomic Updates**: All files updated together or not at all

**Implication**: You can push any version to any platform independently.

### 3. **Snippet-Based Execution**
- **Server-Side Logic**: Update logic lives in `snippets/unSigned/updateNatsAgent.py`
- **Agent-Side Execution**: Agents run the snippet on schedule
- **No Agent Recompilation**: Changes to update logic don't require agent rebuild

**Implication**: You can change how updates work without touching agent code.

### 4. **File-Based Distribution**
- **Modular Structure**: Agent files in `/installerFiles/<platform>/Agent/`
- **Atomic Replacement**: Files replaced as a unit
- **Backup Preservation**: Previous version always available

**Implication**: You can update any combination of agent files.

---

## Scaling to New Features

### Scenario 1: Add New Agent Module

**Current**: Agent has `nats_agent.py`, `core/nats_service.py`, etc.

**Future**: Add `core/osquery_integration.py`

**Steps**:
1. Create `installerFiles/Windows/Agent/core/osquery_integration.py`
2. Create `installerFiles/Linux/Agent/core/osquery_integration.py`
3. Create `installerFiles/MacOS/Agent/core/osquery_integration.py`
4. Calculate hashes
5. Update ServerCore version and hashes
6. Done! Agents auto-update

### Scenario 2: Add New Agent Configuration

**Current**: Agent reads from `config.json`

**Future**: Add support for `advanced_config.json`

**Steps**:
1. Update agent code to read new config
2. Add new config files to `/installerFiles/<platform>/Agent/`
3. Calculate hashes
4. Update ServerCore
5. Done! Agents auto-update

### Scenario 3: Add New Metrics Collection

**Current**: Agent collects basic metrics

**Future**: Add advanced metrics (CPU, memory, disk, network)

**Steps**:
1. Update `core/agent.py` with new metrics logic
2. Update all three platform versions
3. Calculate hashes
4. Update ServerCore
5. Done! Agents auto-update

### Scenario 4: Add New Communication Protocol

**Current**: Agent uses NATS for messaging

**Future**: Add support for gRPC or WebSocket

**Steps**:
1. Add new protocol handler to agent code
2. Update all platform versions
3. Calculate hashes
4. Update ServerCore
5. Done! Agents auto-update

---

## Extensibility Points

### 1. **Database Schema**
Add new fields to `ServerCore` for tracking:
- Agent capabilities
- Feature flags
- Configuration versions
- Deployment status

**Example**:
```python
class ServerCore(db.Model):
    # ... existing fields ...
    persistent_agent_features = db.Column(JSONB, nullable=True)  # {"osquery": true, "grpc": false}
    persistent_agent_config_version = db.Column(db.String(50), nullable=True)
```

### 2. **Update Snippet**
Extend `updateNatsAgent.py` to:
- Download configuration files
- Run pre/post-update hooks
- Validate agent functionality
- Report detailed status

### 3. **Endpoint Responses**
Extend `/diags/persistentagentversion` to return:
- Available features
- Configuration requirements
- Rollback information
- Update history

### 4. **Agent Capabilities**
Track per-device:
- Installed version
- Supported features
- Configuration status
- Last update time

---

## Deployment Patterns

### Pattern 1: Canary Deployment
```python
# Update 5% of devices first
devices = Device.query.filter_by(tenant_uuid=tenant_uuid).limit(count // 20)
for device in devices:
    schedule_update_snippet(device)

# Monitor for 24 hours
# If successful, update next 25%
# If failed, rollback all
```

### Pattern 2: Staged Rollout
```python
# Day 1: 5% of devices
# Day 2: 25% of devices
# Day 3: 50% of devices
# Day 4: 100% of devices
```

### Pattern 3: Feature Flags
```python
# Update agent code with feature flag
if config.get('enable_osquery'):
    # Use osquery integration
else:
    # Use legacy method
```

### Pattern 4: A/B Testing
```python
# Run two versions simultaneously
# Compare performance
# Gradually migrate to better version
```

---

## Security Considerations

### 1. **Hash Verification**
- SHA256 hashes prevent tampering
- Platform-specific hashes prevent cross-platform issues
- Hashes stored in database (single source of truth)

### 2. **Atomic Updates**
- All files updated together
- No partial updates
- Rollback always available

### 3. **Backup Preservation**
- Previous version always available
- Automatic rollback on failure
- Manual rollback possible

### 4. **Signature Verification**
- Snippets are signed by server
- Agent verifies signature before execution
- Prevents unauthorized code execution

---

## Monitoring & Observability

### Metrics to Track
- Update success rate per device
- Update duration per device
- Rollback frequency
- Version distribution across fleet
- Feature adoption rate

### Alerts to Set
- Update failure rate > 5%
- Device stuck on old version > 48 hours
- Rollback triggered
- Hash mismatch detected

### Dashboard to Build
- Real-time update progress
- Device version distribution
- Update history per device
- Rollback history
- Feature adoption timeline

---

## Limitations & Future Work

### Current Limitations
- Updates run on 24-hour schedule (can be made on-demand)
- No UI for scheduling updates
- No canary deployment UI
- No automatic rollback on failure

### Phase 2 Enhancements
- On-demand update triggering
- Canary deployment UI
- Automatic rollback on heartbeat failure
- Update status dashboard
- Device-level version tracking

### Phase 3 Enhancements
- Feature flag management
- A/B testing framework
- Performance impact tracking
- Automatic rollback triggers
- Update scheduling UI

---

## Conclusion

This system is **truly future-proof** because:

✅ **Model-driven**: Changes to schema are auto-migrated  
✅ **Version-based**: Any version can be deployed independently  
✅ **Snippet-based**: Update logic can change without agent rebuild  
✅ **File-based**: Any combination of files can be updated  
✅ **Extensible**: New fields and features can be added easily  
✅ **Secure**: Hash verification prevents tampering  
✅ **Reliable**: Atomic updates and rollback capability  

**You can now push ANY code changes to agents in the field with confidence.**

