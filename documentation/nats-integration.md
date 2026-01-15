# NATS Integration for Wegweiser Agent Communication

## Overview

This document describes the NATS integration that replaces Node-RED for agent communication while ensuring absolute tenant separation and maintaining compatibility with existing functionality.

## Architecture

### Key Components

1. **NATS Server** (`nats.wegweiser.tech:4222`)
   - Handles all agent communication
   - Provides tenant isolation through subject-based permissions
   - Supports JetStream for message persistence

2. **NATS Connection Manager** (`app/utilities/nats_manager.py`)
   - Manages tenant-specific NATS connections
   - Handles authentication and reconnection
   - Validates subject permissions

3. **NATS Persistent Agent** (`nats_persistent_agent.py`)
   - Replaces WebSocket-based persistent agent
   - Connects to NATS using tenant credentials
   - Maintains same functionality as original agent

4. **Flask NATS Routes** (`app/routes/nats/`)
   - New API endpoints for NATS communication
   - Parallel to existing Node-RED routes
   - Handles device registration and command dispatch

5. **Message Handlers** (`app/handlers/nats/`)
   - Process incoming NATS messages
   - Validate tenant context
   - Update database with agent data

## Tenant Isolation

### Subject Hierarchy

All NATS subjects follow this pattern:
```
tenant.{tenant_uuid}.device.{device_uuid}.{message_type}
```

Examples:
- `tenant.123e4567-e89b-12d3-a456-426614174000.device.987fcdeb-51a2-43d1-9f12-123456789abc.heartbeat`
- `tenant.123e4567-e89b-12d3-a456-426614174000.device.987fcdeb-51a2-43d1-9f12-123456789abc.command`

### Authentication

Each tenant receives unique NATS credentials:
- Username: `tenant_{tenant_uuid}`
- Password: 32-character random string
- Permissions: Limited to `tenant.{tenant_uuid}.>` subjects only

### JetStream Streams

Each tenant gets a dedicated JetStream stream:
- Name: `TENANT_{tenant_uuid}_DEVICES`
- Subjects: `tenant.{tenant_uuid}.device.>`
- Retention: 24 hours, max 10,000 messages

## API Endpoints

### Device Management

- `GET /api/nats/device/{device_uuid}/tenant` - Get tenant info for device
- `GET /api/nats/device/{device_uuid}/credentials` - Get NATS credentials
- `POST /api/nats/device/{device_uuid}/heartbeat` - Process heartbeat
- `POST /api/nats/device/{device_uuid}/command` - Send command to device
- `GET /api/nats/device/{device_uuid}/status` - Get device status

### Agent Management

- `POST /api/nats/agent/register` - Register new NATS agent
- `POST /api/nats/agent/{device_uuid}/upgrade` - Upgrade existing agent
- `GET /api/nats/agent/{device_uuid}/config` - Get agent configuration
- `POST /api/nats/agent/{device_uuid}/restart` - Restart agent

### Monitoring

- `GET /api/nats/health` - NATS infrastructure health check
- `GET /api/nats/metrics` - Detailed NATS metrics
- `GET /api/nats/tenant/{tenant_uuid}/metrics` - Tenant-specific metrics
- `GET /api/nats/connections` - Active NATS connections
- `GET /api/nats/service/status` - Message service status
- `POST /api/nats/service/start` - Start message processing service

## Deployment

### Prerequisites

1. NATS server running at `nats.wegweiser.tech:4222`
2. Flask application with virtual environment
3. Database with existing tenant/device structure

### Installation Steps

1. **Run deployment script:**
   ```bash
   ./scripts/deploy_nats_integration.sh
   ```

2. **Start NATS message service:**
   ```bash
   curl -X POST http://localhost:5000/api/nats/service/start
   ```

3. **Verify deployment:**
   ```bash
   curl http://localhost:5000/api/nats/health
   ```

### Manual Installation

1. **Install dependencies:**
   ```bash
   pip install nats-py aiohttp python-dotenv
   ```

2. **Update environment variables:**
   ```bash
   echo "NATS_SERVER_URL=nats://nats.wegweiser.tech:4222" >> .env
   echo "NATS_ENABLED=true" >> .env
   ```

3. **Restart Flask application:**
   ```bash
   sudo systemctl restart wegweiser
   ```

## Agent Migration

### New Agent Installation

1. **Deploy NATS agent:**
   ```bash
   # Copy nats_persistent_agent.py to target machine
   # Install dependencies: pip install nats-py aiohttp python-dotenv psutil
   # Run: python nats_persistent_agent.py
   ```

2. **Register agent:**
   ```bash
   curl -X POST http://app.wegweiser.tech/api/nats/agent/register \
     -H "Content-Type: application/json" \
     -d '{"groupuuid": "your-group-uuid", "devicename": "hostname"}'
   ```

### Existing Agent Upgrade

1. **Get upgrade credentials:**
   ```bash
   curl http://app.wegweiser.tech/api/nats/agent/{device_uuid}/upgrade
   ```

2. **Update agent configuration:**
   - Replace WebSocket connection with NATS connection
   - Use provided NATS credentials
   - Update subject patterns

## Testing

### Run Tests

```bash
# Install test dependencies
pip install pytest pytest-asyncio

# Run NATS integration tests
python -m pytest tests/test_nats_integration.py -v
```

### Manual Testing

1. **Test NATS connectivity:**
   ```python
   import asyncio
   import nats
   
   async def test():
       nc = await nats.connect("nats://nats.wegweiser.tech:4222")
       print("Connected to NATS")
       await nc.close()
   
   asyncio.run(test())
   ```

2. **Test tenant isolation:**
   ```bash
   # Should work - correct tenant
   curl http://localhost:5000/api/nats/device/{valid_device_uuid}/tenant
   
   # Should fail - invalid device
   curl http://localhost:5000/api/nats/device/{invalid_device_uuid}/tenant
   ```

## Monitoring

### Health Checks

- **NATS Health:** `GET /api/nats/health`
- **Service Status:** `GET /api/nats/service/status`
- **Connection Status:** `GET /api/nats/connections`

### Metrics

- **Overall Metrics:** `GET /api/nats/metrics`
- **Tenant Metrics:** `GET /api/nats/tenant/{tenant_uuid}/metrics`
- **Debug Info:** `GET /api/nats/debug/subjects`

### Logs

- **Flask Logs:** `/opt/wegweiser/wlog/wegweiser.log`
- **Agent Logs:** `../Logs/nats_persistent_agent.log`
- **NATS Server Logs:** Check NATS server configuration

## Troubleshooting

### Common Issues

1. **NATS Connection Failed**
   - Check NATS server is running: `nc -z nats.wegweiser.tech 4222`
   - Verify credentials are correct
   - Check firewall settings

2. **Tenant Isolation Errors**
   - Verify device belongs to correct tenant
   - Check subject permissions
   - Review NATS server logs

3. **Message Processing Errors**
   - Check message service status: `GET /api/nats/service/status`
   - Review Flask application logs
   - Verify database connectivity

### Debug Commands

```bash
# Check NATS server status
nats server check

# List NATS subjects
nats sub "tenant.*.device.*.>"

# Monitor NATS traffic
nats sub ">" --count=10

# Test subject permissions
nats pub "tenant.{tenant_uuid}.device.{device_uuid}.test" "test message"
```

## Migration Strategy

### Phase 1: Parallel Deployment (Current)
- NATS infrastructure deployed alongside Node-RED
- New `/api/nats/` endpoints available
- Existing agents continue using Node-RED

### Phase 2: Gradual Migration
- Select test tenants for NATS migration
- Deploy NATS agents to test devices
- Monitor performance and reliability

### Phase 3: Full Migration
- Migrate all tenants to NATS
- Deprecate Node-RED endpoints
- Remove WebSocket dependencies

## Security Considerations

- **Tenant Isolation:** Cryptographically enforced via NATS permissions
- **Authentication:** JWT-based with tenant claims
- **Transport Security:** TLS for all NATS connections
- **Audit Logging:** All tenant access attempts logged
- **Credential Rotation:** Supported for enhanced security

## Performance

- **Scalability:** NATS clustering for high availability
- **Persistence:** JetStream for reliable message delivery
- **Monitoring:** Real-time metrics and health checks
- **Optimization:** Connection pooling and efficient routing

## Support

For issues or questions:
1. Check logs in `/opt/wegweiser/wlog/`
2. Review health endpoints
3. Consult this documentation
4. Contact development team
