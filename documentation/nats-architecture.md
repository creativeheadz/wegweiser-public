# NATS Architecture Design for Wegweiser Agent Communication

## Overview

This document outlines the design for replacing Node-RED with NATS for agent communication while ensuring absolute tenant separation and maintaining compatibility with existing functionality.

## Current Architecture Analysis

### Existing Components
- **Flask Application**: Handles web UI, data analysis, user management
- **Node-RED (vidar.wegweiser.tech)**: WebSocket orchestration for agent connections
- **Persistent Agent**: Connects via WebSocket to Node-RED for heartbeat and commands
- **Device Registration**: Via Flask `/devices/register` endpoint with group UUID

### Current Authentication Flow
1. Agent registers with Flask using group UUID
2. Receives device UUID and stores in agent.config
3. Connects to Node-RED WebSocket at `wss://vidar.wegweiser.tech/ws/checkin`
4. Sends heartbeat messages with device UUID
5. Receives commands and sends responses

## NATS Architecture Design

### Subject Hierarchy

```
tenant.{tenant_uuid}.device.{device_uuid}.{message_type}
```

#### Subject Patterns
- **Heartbeat**: `tenant.{tenant_uuid}.device.{device_uuid}.heartbeat`
- **Status Updates**: `tenant.{tenant_uuid}.device.{device_uuid}.status`
- **Commands**: `tenant.{tenant_uuid}.device.{device_uuid}.command`
- **Command Responses**: `tenant.{tenant_uuid}.device.{device_uuid}.response`
- **System Info**: `tenant.{tenant_uuid}.device.{device_uuid}.sysinfo`
- **Monitoring Data**: `tenant.{tenant_uuid}.device.{device_uuid}.monitoring`

#### Administrative Subjects
- **Device Registration**: `admin.device.register`
- **Tenant Management**: `admin.tenant.{tenant_uuid}.{action}`
- **Health Checks**: `admin.health.{component}`

### Tenant Isolation Strategy

#### 1. Subject-Level Isolation
- All device communication scoped to tenant UUID
- No cross-tenant subject access possible
- Wildcard subscriptions limited to tenant scope

#### 2. Authentication & Authorization
- Each tenant gets unique NATS credentials
- JWT-based authentication with tenant claims
- Subject permissions enforced at NATS server level

#### 3. JetStream Configuration
- Separate streams per tenant for persistence
- Stream naming: `TENANT_{tenant_uuid}_DEVICES`
- Consumer groups scoped to tenant

### NATS Server Configuration

#### Authentication
```json
{
  "authorization": {
    "users": [
      {
        "user": "tenant_{tenant_uuid}",
        "password": "{generated_password}",
        "permissions": {
          "publish": ["tenant.{tenant_uuid}.>"],
          "subscribe": ["tenant.{tenant_uuid}.>"]
        }
      }
    ]
  }
}
```

#### JetStream Streams
```json
{
  "name": "TENANT_{tenant_uuid}_DEVICES",
  "subjects": ["tenant.{tenant_uuid}.device.>"],
  "retention": "limits",
  "max_age": 86400000000000,
  "max_msgs": 10000,
  "storage": "file"
}
```

## Component Design

### 1. NATS Connection Manager (`app/utilities/nats_manager.py`)
- Tenant-aware connection pooling
- Automatic reconnection with backoff
- Subject validation and sanitization
- Connection health monitoring

### 2. NATS Agent (`nats_persistent_agent.py`)
- Replaces WebSocket-based persistent agent
- Maintains same registration flow
- Uses NATS subjects for all communication
- Backward compatible configuration

### 3. Flask NATS Routes (`app/routes/nats/`)
- New route blueprint for NATS integration
- Parallel to existing routes (no disruption)
- Device registration with NATS credentials
- Command dispatch via NATS

### 4. Message Handlers (`app/handlers/nats/`)
- Tenant-scoped message processing
- Heartbeat processing and database updates
- Command execution and response handling
- System information aggregation

## Security Considerations

### 1. Tenant Isolation
- Cryptographic separation via NATS permissions
- No shared subjects between tenants
- Audit logging for cross-tenant access attempts

### 2. Authentication
- Device UUID + tenant UUID validation
- JWT tokens with tenant claims
- Credential rotation support

### 3. Data Protection
- Message encryption for sensitive data
- TLS for all NATS connections
- Audit trail for all communications

## Migration Strategy

### Phase 1: Parallel Implementation
- Implement NATS infrastructure alongside Node-RED
- Create new routes with `/nats/` prefix
- Test with subset of devices

### Phase 2: Gradual Migration
- Update agent installer to support both modes
- Migrate tenants one by one
- Monitor performance and reliability

### Phase 3: Full Transition
- Deprecate Node-RED routes
- Remove WebSocket dependencies
- Optimize NATS configuration

## Performance Considerations

### Scalability
- NATS clustering for high availability
- JetStream for message persistence
- Horizontal scaling of Flask workers

### Monitoring
- NATS server metrics
- Message throughput per tenant
- Connection health per device
- Response time monitoring

## Implementation Plan

1. **NATS Infrastructure Setup**
   - Configure NATS server with tenant isolation
   - Set up JetStream for persistence
   - Implement monitoring and alerting

2. **Core Components**
   - NATS connection manager
   - Message handlers with tenant validation
   - New Flask routes for NATS communication

3. **Agent Development**
   - New NATS-based persistent agent
   - Maintain compatibility with existing config
   - Implement all current functionality

4. **Testing & Validation**
   - Tenant isolation verification
   - Performance testing
   - Security audit

5. **Deployment & Migration**
   - Parallel deployment
   - Gradual tenant migration
   - Monitoring and optimization

## Next Steps

1. Set up NATS server configuration
2. Implement NATS connection utilities
3. Create new persistent agent
4. Develop Flask integration routes
5. Comprehensive testing framework
