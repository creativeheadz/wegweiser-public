# Cryptographic Key Rotation

Wegweiser implements a comprehensive rolling key rotation system that enables server-side key updates without requiring agent downtime.

## Overview

The key rotation mechanism allows the server to rotate its cryptographic keys seamlessly while maintaining backward compatibility with agents running older versions. This ensures:

- **Zero downtime** - Agents continue operating during key rotation
- **Gradual migration** - Agents don't need to be updated simultaneously
- **Security** - Old keys are retired safely after transition period
- **Audit trail** - All key rotations are timestamped and logged

## Architecture

### Components

**Server-Side**:
- RSA-4096 key pair management in Azure Key Vault
- Public keys stored in `/opt/wegweiser/includes/` directory
- Automatic snippet re-signing with current private key
- NATS-based key rotation event broadcasting

**Agent-Side**:
- Multi-key crypto cache (current + old keys)
- Persistent key storage in `~/.wegweiser/keys/` directory
- Automatic key fetching on signature verification failure
- Heartbeat-based key rotation detection

### Key Files

**Server**:
- `app/routes/diags.py` - Key rotation endpoint (`POST /diags/keys/rotate`)
- `app/routes/nats/device_api.py` - Heartbeat key hash comparison
- `includes/serverPubKey.pem` - Current public key
- `includes/old/serverPubKey.pem` - Previous public key (for transition)
- `includes/serverPrivKey.pem` - Private key (Azure Key Vault)

**Agents** (Windows, Linux, macOS):
- `core/agent.py` - Multi-key verification and heartbeat handling
- `core/crypto.py` - Cryptographic operations and key caching
- `core/nats_service.py` - KEY_ROTATION event listener
- `core/secure_snippet_signer.py` - Snippet signing utility (testing/admin)

## Key Rotation Flow

### Initiating Rotation

1. **Server Admin** calls `POST /diags/keys/rotate`
2. **Server** loads current and old public keys
3. **Server** re-signs all snippets with current private key
4. **Server** broadcasts KEY_ROTATION event via NATS to all tenants
5. **Server** includes current and old keys in rotation event

### Agent Detection (Persistent Agents - NATS)

1. Agent receives KEY_ROTATION event via NATS listener
2. Agent extracts current and old keys from event payload
3. Agent updates crypto manager cache in real-time
4. Agent begins verifying new snippets with new key

### Agent Detection (Scheduled Agents - API Polling)

1. Agent sends heartbeat to server
2. Server includes current key hash in heartbeat response
3. Agent compares hash with cached key hash
4. If different, agent detects rotation and fetches new keys
5. Agent fetches keys via `/api/nats/device/{device_uuid}/keys` endpoint
6. Agent caches keys locally and continues operation

## Signature Verification

The multi-key verification process provides automatic fallback:

```
1. Try verifying with current cached key
   ├─ Success → Continue execution
   └─ Failure → Try old key
2. Try verifying with old cached key
   ├─ Success → Continue execution (transition period)
   └─ Failure → Fetch new keys
3. Fetch new keys from server
   ├─ Success → Update cache and retry verification
   │  ├─ Success → Continue execution
   │  └─ Failure → Report SIGFAIL
   └─ Failure → Report SIGFAIL
```

This ensures snippets signed with old keys continue working during the transition period.

## Server Endpoint

### POST /diags/keys/rotate

Triggers automatic key rotation and snippet re-signing.

**Request**:
```bash
curl -X POST https://app.wegweiser.tech/diags/keys/rotate \
  -H "Content-Type: application/json"
```

**Response**:
```json
{
  "status": "success",
  "message": "Key rotation completed successfully",
  "snippets_resigned": 38,
  "snippets_resign_failed": 0,
  "tenants_targeted": 6,
  "published": 6,
  "failed": 0,
  "rotation_id": "808d66f4-f48c-4a26-a73b-395e8ce857c9",
  "notes": "Persistent agents will receive keys via NATS. Scheduled agents will refresh via API polling."
}
```

**Response Fields**:
- `status` - Operation status (success/error)
- `snippets_resigned` - Number of successfully re-signed snippets
- `snippets_resign_failed` - Number of failed re-signings
- `tenants_targeted` - Number of tenants that received key rotation events
- `published` - Number of successful NATS publications
- `failed` - Number of failed NATS publications
- `rotation_id` - Unique identifier for this rotation event
- `notes` - Additional information about the rotation

## Key Storage

### Server (Azure Key Vault)

Private keys are never stored on disk. They're managed through Azure Key Vault:
- RSA-4096 private key for signing operations
- Accessible only by authorized services
- Audit logging for all access attempts
- Regular key rotation policy

### Agent Caching

Agents cache public keys locally for performance:

**Directory**: `~/.wegweiser/keys/`

**Files**:
- `current_key.pem` - Current public key for verification
- `old_key.pem` - Previous public key (transition period)

**Permissions**:
```bash
drwx------ 2 wegweiser wegweiser 4096 Oct 24 12:00 /home/wegweiser/.wegweiser/keys/
-rw------- 1 wegweiser wegweiser  800 Oct 24 12:00 current_key.pem
-rw------- 1 wegweiser wegweiser  800 Oct 24 12:00 old_key.pem
```

## Multi-Key Cache Management

### Crypto Manager

The CryptoManager maintains an in-memory cache of up to two keys:

```python
class CryptoManager:
    def __init__(self):
        self.key_cache = {
            'current': {'key_obj': PublicKey, 'pem': str},
            'old': {'key_obj': PublicKey, 'pem': str}
        }

    def update_server_key(self, key_pem: str, key_type: str = 'current'):
        # Update cache and persist to disk

    def get_all_cached_keys(self) -> List[Tuple[str, PublicKey]]:
        # Return keys in preference order (current first)

    def verify_base64_payload_signature(self, response, try_all_keys=True):
        # Returns (verified: bool, which_key: str)
```

### Key Lifecycle

1. **Current Key** - Active for all new signatures and verification
2. **Old Key** - Retained during transition period for backward compatibility
3. **Retired Key** - Removed after transition period expires

**Transition Period**: Typically 7-14 days (configurable per deployment)

## Snippet Re-signing

### Process

When rotation is triggered, the server:

1. Loads all 38 snippets from repository
2. For each snippet:
   - Extracts base64-encoded payload
   - Decodes payload bytes
   - Generates new signature using current private key
   - RSA-4096 with SHA256 hashing (PKCS1v15 padding)
   - Updates `payloadsig` field in snippet JSON
   - Adds `resigned_at` Unix timestamp
   - Persists updated snippet to disk

### Snippet Structure

```json
{
  "settings": {
    "snippetUuid": "01a2d9eb-4ac1-4da1-817d-81f80230f57e",
    "snippetname": "updateLoggingConfig",
    "snippettype": ".py"
  },
  "payload": {
    "payloadsig": "E2LINZx0LRauxrEcvlv84l8gXVzfFhSlUIFwfmSPTMI...",
    "payloadb64": "IiIiClNuaXBwZXQ6IFVwZGF0ZSBBZ2..."
  },
  "resigned_at": 1761308232
}
```

The `resigned_at` field provides an audit trail of when snippets were last signed.

## NATS Event Broadcasting

### KEY_ROTATION Event

Broadcasted to each tenant on subject: `tenant.{tenant_uuid}.keys.rotation`

**Event Payload**:
```json
{
  "event": "KEY_ROTATION",
  "keys": {
    "current": "-----BEGIN PUBLIC KEY-----\nMIIBIjANBgkqhkiG...",
    "old": "-----BEGIN PUBLIC KEY-----\nMIIBIjANBgkqhkiG..."
  },
  "timestamp": 1761308232,
  "rotation_id": "808d66f4-f48c-4a26-a73b-395e8ce857c9"
}
```

### Listener Implementation

Agents subscribe to their tenant's key rotation subject:

```python
async def setup_subscriptions(self):
    key_rotation_subject = f"tenant.{self.tenant_uuid}.keys.rotation"
    await self.nc.subscribe(key_rotation_subject, cb=self._handle_key_rotation)

async def _handle_key_rotation(self, msg):
    data = json.loads(msg.data.decode())
    if data.get('event') == 'KEY_ROTATION':
        # Update crypto manager cache
        current_key = data.get('keys', {}).get('current')
        old_key = data.get('keys', {}).get('old')
        self.crypto.update_server_key(current_key, key_type='current')
        self.crypto.update_server_key(old_key, key_type='old')
```

## Heartbeat Integration

### Key Hash Detection

Server includes key hash in heartbeat response:

```python
current_key_hash = hashlib.sha256(
    server_core.server_public_key.encode()
).hexdigest()

response = {
    "success": True,
    "current_key_hash": current_key_hash,
    "timestamp": current_time
}
```

### Agent Response Handling

Agent compares hashes to detect rotation:

```python
def _handle_heartbeat_response(self, response_data):
    server_key_hash = response_data.get('current_key_hash')
    if server_key_hash != self.last_key_hash:
        # Key rotation detected
        new_key_pem = self.api.get_server_public_key()
        self.crypto.update_server_key(new_key_pem, key_type='current')
        self.last_key_hash = self._compute_key_hash(new_key_pem)
```

## Testing & Validation

### Manual Testing

Test key rotation endpoint:

```bash
# Trigger key rotation
curl -X POST https://localhost/diags/keys/rotate \
  -H "Content-Type: application/json" \
  -k

# Expected response:
{
  "status": "success",
  "snippets_resigned": 38,
  "snippets_resign_failed": 0,
  ...
}

# Verify snippets were resigned
grep -l "resigned_at" snippets/00000000-0000-0000-0000-000000000000/*.json | wc -l
# Should output: 38
```

### Agent Verification

Verify agents handle key rotation:

1. Check agent logs for key update messages
2. Verify cached keys in `~/.wegweiser/keys/`
3. Confirm snippets execute after rotation
4. Check for SIGFAIL errors (should be none)

### Backward Compatibility

Confirm old snippets still work:

1. Keep old private key for testing
2. Sign snippet with old key
3. Rotate to new key
4. Verify agent can still verify old snippet
5. Verify agent can handle new snippets

## Security Considerations

### Private Key Management

- Never stored on disk in production
- Always accessed through Azure Key Vault
- All access logged and audited
- Rotated on configurable schedule

### Public Key Distribution

- Signed by trusted CA in production
- HTTPS-only distribution
- Pinning recommended for production environments

### Transition Period

- Maintain old key in cache during transition
- Allows phased agent updates
- Recommended: 7-14 days
- Can be extended if needed

### Audit Trail

- All rotations logged with timestamps
- `resigned_at` field in snippets
- NATS event with `rotation_id`
- Server heartbeat logs key hashes

## Troubleshooting

### Snippet Verification Failures

**Symptom**: Agents report SIGFAIL errors after rotation

**Causes**:
1. Snippet not re-signed properly
2. Agent cache corrupted
3. Wrong key in rotation event

**Resolution**:
```bash
# Re-trigger rotation
curl -X POST https://localhost/diags/keys/rotate

# Verify snippets have resigned_at timestamp
grep "resigned_at" snippets/00000000-0000-0000-0000-000000000000/SNIPPET_ID.json

# Clear agent cache and restart
rm -rf ~/.wegweiser/keys/*
systemctl restart wegweiser-agent.service
```

### Missing Key Updates

**Symptom**: Agents don't receive key updates via NATS

**Causes**:
1. NATS connection down
2. Subscription not active
3. Wrong tenant UUID

**Resolution**:
```bash
# Check NATS connection
journalctl -u wegweiser-persistent-agent.service -f

# Verify subscription
# Look for: "Subscribed to tenant.{uuid}.keys.rotation"

# Manual key fetch
curl -X GET https://app.wegweiser.tech/api/nats/device/DEVICE_UUID/keys
```

### Heartbeat Key Hash Mismatch

**Symptom**: Agents detect rotation but fail to fetch new keys

**Causes**:
1. API endpoint down
2. Incorrect device UUID
3. Network connectivity issue

**Resolution**:
```bash
# Check agent logs
journalctl -u wegweiser-agent.service | grep "key rotation"

# Manually trigger key fetch via agent
# (Agent will auto-fetch on next heartbeat)

# Verify API endpoint
curl -X GET https://app.wegweiser.tech/api/nats/device/DEVICE_UUID/keys
```

## Best Practices

### Deployment

1. **Test in staging** before production rotation
2. **Announce rotation** to operators
3. **Monitor closely** for first 24 hours
4. **Keep old key** available for extended period
5. **Document rotation** in change log

### Operations

1. **Schedule rotations** during maintenance windows
2. **Rotate keys** every 6-12 months (or per policy)
3. **Monitor agent logs** for key-related errors
4. **Validate** that all snippets execute after rotation
5. **Archive old keys** for audit compliance

### Security

1. **Protect private keys** in Azure Key Vault
2. **Limit key rotation access** to authorized personnel
3. **Enable audit logging** for all key operations
4. **Use strong certificates** for public keys
5. **Monitor key usage** for anomalies

## Related Documentation

- [Security Overview](./security-overview.md)
- [NATS Integration](./nats-integration.md)
- [NATS Architecture](./nats-architecture.md)
- [NATS Data Flow](./nats-dataflow.md)
- [Agent Architecture](./architecture-overview.md#agent-architecture)

---

**Version**: 1.0
**Last Updated**: October 24, 2025
**Status**: Production Ready
