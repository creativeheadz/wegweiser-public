# FIPS 140-2/140-3 Deployment Profile - Part 2

**Continuation of FIPS_DEPLOYMENT_PROFILE.md**

---

## B7: Azure Services - FIPS Profile

### B7.1: Azure Key Vault Premium / Managed HSM

**Service**: Azure Key Vault Premium or Azure Managed HSM

**FIPS Validation**:
- FIPS 140-2 Level 3 validated HSMs
- CMVP Certificate #3653
- All cryptographic operations performed in HSM

**Use Cases for Wegweiser**:
1. **TLS Certificate Storage**: Store server/client certificates
2. **Secret Management**: Database passwords, API keys, NATS credentials
3. **Key Generation**: Generate RSA keys for agents (2048-bit or 4096-bit)
4. **Signing Operations**: Sign agent updates, configuration files

**Configuration**:
```bash
# Create Azure Key Vault Premium
az keyvault create \
  --resource-group wegweiser-rg \
  --name wegweiser-kv-fips \
  --location eastus \
  --sku premium \
  --enable-rbac-authorization true

# Or create Managed HSM (higher security, higher cost)
az keyvault create \
  --resource-group wegweiser-rg \
  --name wegweiser-hsm-fips \
  --location eastus \
  --hsm-name wegweiser-hsm \
  --administrators <admin-object-id>

# Store secrets
az keyvault secret set \
  --vault-name wegweiser-kv-fips \
  --name db-password \
  --value '<strong-password>'

# Generate RSA key (4096-bit)
az keyvault key create \
  --vault-name wegweiser-kv-fips \
  --name agent-signing-key \
  --kty RSA \
  --size 4096 \
  --ops sign verify
```

**Python Integration**:
```python
from azure.identity import DefaultAzureCredential
from azure.keyvault.secrets import SecretClient
from azure.keyvault.keys import KeyClient
from azure.keyvault.keys.crypto import CryptographyClient, SignatureAlgorithm

# Authenticate
credential = DefaultAzureCredential()

# Secrets client
secret_client = SecretClient(
    vault_url="https://wegweiser-kv-fips.vault.azure.net/",
    credential=credential
)

# Retrieve secret
db_password = secret_client.get_secret("db-password").value

# Keys client
key_client = KeyClient(
    vault_url="https://wegweiser-kv-fips.vault.azure.net/",
    credential=credential
)

# Get signing key
signing_key = key_client.get_key("agent-signing-key")

# Crypto client for signing
crypto_client = CryptographyClient(signing_key, credential=credential)

# Sign data (RSA-PSS with SHA-256)
signature = crypto_client.sign(
    SignatureAlgorithm.ps256,  # RSA-PSS with SHA-256 (FIPS-approved)
    message_digest
)
```

### B7.2: Azure Front Door / Application Gateway

**Service**: Azure Front Door Premium or Azure Application Gateway v2

**FIPS Validation**:
- FIPS 140-2 validated
- TLS termination in FIPS-compliant environment
- Managed by Microsoft

**Use Case**: TLS termination for Wegweiser web application

**Configuration - Azure Front Door Premium**:
```bash
# Create Front Door Premium
az afd profile create \
  --resource-group wegweiser-rg \
  --profile-name wegweiser-fd-fips \
  --sku Premium_AzureFrontDoor

# Create endpoint
az afd endpoint create \
  --resource-group wegweiser-rg \
  --profile-name wegweiser-fd-fips \
  --endpoint-name wegweiser-app \
  --enabled-state Enabled

# Configure custom domain
az afd custom-domain create \
  --resource-group wegweiser-rg \
  --profile-name wegweiser-fd-fips \
  --custom-domain-name app-wegweiser-tech \
  --host-name app.wegweiser.tech \
  --minimum-tls-version TLS12

# Configure origin (backend)
az afd origin-group create \
  --resource-group wegweiser-rg \
  --profile-name wegweiser-fd-fips \
  --origin-group-name wegweiser-backend

az afd origin create \
  --resource-group wegweiser-rg \
  --profile-name wegweiser-fd-fips \
  --origin-group-name wegweiser-backend \
  --origin-name wegweiser-app-vm \
  --host-name wegweiser-app-fips.eastus.cloudapp.azure.com \
  --origin-host-header wegweiser-app-fips.eastus.cloudapp.azure.com \
  --priority 1 \
  --weight 1000 \
  --enabled-state Enabled \
  --http-port 80 \
  --https-port 443
```

**TLS Policy** (FIPS-compliant cipher suites):
```json
{
  "minimumTlsVersion": "1.2",
  "cipherSuites": [
    "TLS_ECDHE_RSA_WITH_AES_256_GCM_SHA384",
    "TLS_ECDHE_RSA_WITH_AES_128_GCM_SHA256",
    "TLS_RSA_WITH_AES_256_GCM_SHA384",
    "TLS_RSA_WITH_AES_128_GCM_SHA256"
  ]
}
```

**Benefits**:
- Offload TLS termination to Azure (FIPS-validated)
- WAF (Web Application Firewall) protection
- DDoS protection
- Global load balancing
- Caching and CDN

### B7.3: Azure Monitor / Application Insights

**Service**: Azure Monitor with Application Insights

**FIPS Compliance**:
- Data transmission over TLS 1.2+
- Data at rest encrypted with FIPS-validated modules
- Managed by Microsoft

**Configuration**:
```bash
# Create Application Insights
az monitor app-insights component create \
  --resource-group wegweiser-rg \
  --app wegweiser-insights-fips \
  --location eastus \
  --kind web \
  --application-type web

# Get instrumentation key
az monitor app-insights component show \
  --resource-group wegweiser-rg \
  --app wegweiser-insights-fips \
  --query instrumentationKey -o tsv
```

**Python Integration**:
```python
from opencensus.ext.azure.log_exporter import AzureLogHandler
import logging

# Configure Azure Monitor logging
logger = logging.getLogger(__name__)
logger.addHandler(AzureLogHandler(
    connection_string=f'InstrumentationKey={instrumentation_key}'
))

# Log events
logger.info('FIPS-compliant deployment started')
```

---

## B8: Deployment Checklist

### B8.1: Pre-Deployment Verification

#### Operating System
- [ ] Ubuntu Pro FIPS 22.04 LTS deployed from Azure Marketplace
- [ ] FIPS mode enabled and verified: `fips-mode-setup --check`
- [ ] OpenSSL FIPS provider active: `openssl list -providers`
- [ ] Kernel crypto in FIPS mode: `cat /proc/sys/crypto/fips_enabled` (should be `1`)

#### Python Environment
- [ ] Python 3.10+ installed with FIPS-enabled OpenSSL
- [ ] Virtual environment created: `/opt/wegweiser/venv`
- [ ] `cryptography>=41.0.0` installed
- [ ] OpenSSL version verified: `python3 -c "import ssl; print(ssl.OPENSSL_VERSION)"`
- [ ] FIPS provider detected: `python3 -c "from cryptography.hazmat.backends.openssl import backend; print(backend.openssl_version_text())"`

#### Code Changes (from OPTION A findings)
- [ ] Bcrypt replaced with PBKDF2-HMAC-SHA256 in all 7 locations
- [ ] RSA key generation updated to 2048-bit minimum (agent/agent.py, downloads/agent.py)
- [ ] Deprecated datetime functions replaced (15+ locations)
- [ ] Session signing configured for SHA-256 (itsdangerous)
- [ ] TOTP configured for SHA-256 (pyotp)

#### Dependencies
- [ ] `requirements.txt` updated (Flask_Bcrypt removed, cryptography>=41.0.0 added)
- [ ] All dependencies installed in FIPS-enabled environment
- [ ] No non-FIPS-approved crypto libraries present

### B8.2: Infrastructure Deployment

#### Database
- [ ] PostgreSQL 14+ deployed with TLS enabled
- [ ] SSL certificates configured
- [ ] FIPS-approved cipher suites configured
- [ ] TLS 1.2 minimum enforced
- [ ] Connection string uses `sslmode=verify-full`

#### Redis
- [ ] Redis 6.2+ deployed with TLS support
- [ ] TLS certificates configured
- [ ] FIPS-approved cipher suites configured
- [ ] TLS 1.2 minimum enforced
- [ ] Client authentication enabled

#### NATS
- [ ] NATS server 2.10+ built with BoringCrypto
- [ ] TLS certificates configured
- [ ] FIPS-approved cipher suites configured
- [ ] TLS 1.2 minimum enforced
- [ ] Authentication webhook configured (replaces bcrypt)

#### Azure Services
- [ ] Azure Key Vault Premium created
- [ ] Secrets migrated to Key Vault
- [ ] Azure Front Door Premium configured
- [ ] Custom domain with TLS 1.2+ configured
- [ ] Application Insights enabled

### B8.3: Application Deployment

#### Flask Application
- [ ] Code deployed to `/opt/wegweiser/`
- [ ] Virtual environment activated
- [ ] Environment variables configured (OPENSSL_CONF, OPENSSL_MODULES)
- [ ] Database migrations applied: `flask db upgrade`
- [ ] Static files collected
- [ ] Gunicorn configured with FIPS-compliant TLS

#### Celery Workers
- [ ] Celery worker service configured
- [ ] Redis broker with TLS configured
- [ ] FIPS environment variables set
- [ ] Worker started and verified

#### Agents
- [ ] Windows agent updated with 2048-bit RSA keys
- [ ] Linux agent deployed on FIPS-enabled systems
- [ ] macOS agent documented as non-FIPS (or FIPS-enabled OpenSSL configured)
- [ ] Agent update mechanism tested
- [ ] NATS TLS configuration verified

### B8.4: Testing and Validation

#### Cryptographic Operations
- [ ] Password hashing tested (PBKDF2-HMAC-SHA256)
- [ ] Password verification tested (existing bcrypt hashes migrated)
- [ ] RSA key generation tested (2048-bit minimum)
- [ ] RSA signature verification tested
- [ ] TLS connections tested (all services)
- [ ] Session signing tested (SHA-256)
- [ ] CSRF tokens tested (SHA-256)
- [ ] TOTP tested (SHA-256)

#### Integration Testing
- [ ] User registration tested
- [ ] User login tested
- [ ] Password reset tested
- [ ] 2FA enrollment tested
- [ ] Agent registration tested
- [ ] Agent communication tested (NATS)
- [ ] Background tasks tested (Celery)
- [ ] Database operations tested
- [ ] Redis caching tested

#### Security Validation
- [ ] TLS cipher suites verified (only FIPS-approved)
- [ ] TLS version verified (1.2 minimum)
- [ ] Certificate validation tested
- [ ] No deprecated algorithms in use
- [ ] No bcrypt usage remaining
- [ ] No 1024-bit RSA keys remaining
- [ ] No datetime.utcnow() calls remaining

#### Performance Testing
- [ ] Login performance acceptable (PBKDF2 iterations: 600,000)
- [ ] Agent registration performance acceptable
- [ ] Background task performance acceptable
- [ ] Database query performance acceptable

---

## B9: Migration Strategy

### B9.1: Password Hash Migration (Bcrypt → PBKDF2)

**Challenge**: Existing user passwords are hashed with bcrypt.

**Solution**: Hybrid verification with gradual migration.

**Implementation**:
```python
def verify_password_hybrid(password: str, stored_hash: str) -> tuple[bool, bool]:
    """
    Verify password with hybrid bcrypt/PBKDF2 support.
    
    Returns:
        (is_valid, needs_rehash)
    """
    # Check hash format
    if stored_hash.startswith('$2b$') or stored_hash.startswith('$2a$'):
        # Legacy bcrypt hash
        try:
            is_valid = bcrypt.check_password_hash(stored_hash, password)
            return (is_valid, True)  # Valid but needs rehash
        except:
            return (False, False)
    else:
        # New PBKDF2 hash
        is_valid = verify_password_fips(password, stored_hash)
        return (is_valid, False)  # Already FIPS-compliant

def login_with_migration(username: str, password: str):
    """Login with automatic password hash migration"""
    user = User.query.filter_by(username=username).first()
    if not user:
        return False
    
    is_valid, needs_rehash = verify_password_hybrid(password, user.password)
    
    if is_valid and needs_rehash:
        # Rehash with PBKDF2
        user.password = hash_password_fips(password)
        db.session.commit()
        logger.info(f"Migrated password hash for user {username}")
    
    return is_valid
```

**Timeline**:
- **Day 0**: Deploy hybrid verification
- **Day 1-90**: Users automatically migrated on login
- **Day 90**: Force password reset for remaining bcrypt users
- **Day 91**: Remove bcrypt support entirely

### B9.2: RSA Key Rotation (1024-bit → 2048-bit)

**Challenge**: Existing agents use 1024-bit RSA keys.

**Solution**: Gradual key rotation via snippet update.

**Implementation**:
1. **Server accepts both key sizes** (transition period)
2. **Push snippet update** to regenerate keys with 2048-bit
3. **Agents regenerate keys** on next update
4. **Server validates new keys** and marks agents as "FIPS-compliant"
5. **After 30 days**: Reject 1024-bit keys

**Snippet Update** (`snippets/signed/rotate_rsa_keys.py`):
```python
import os
from core.crypto import CryptoManager

def rotate_keys():
    """Rotate agent RSA keys to 2048-bit minimum"""
    crypto = CryptoManager()
    
    # Check current key size
    current_key_size = crypto.get_key_size()
    
    if current_key_size < 2048:
        print(f"Rotating keys from {current_key_size}-bit to 2048-bit...")
        
        # Backup old keys
        crypto.backup_keys()
        
        # Generate new 2048-bit keys
        crypto.generate_keypair(key_size=2048)
        
        # Re-register with server
        crypto.register_with_server()
        
        print("Key rotation complete")
    else:
        print(f"Keys already FIPS-compliant ({current_key_size}-bit)")
```

---

## B10: Validation and Certification

### B10.1: Internal Validation Procedures

#### Cryptographic Algorithm Audit
```bash
# Scan codebase for non-approved algorithms
grep -r "bcrypt" app/ --exclude-dir=venv
grep -r "md5" app/ --exclude-dir=venv | grep -v "# non-cryptographic"
grep -r "sha1" app/ --exclude-dir=venv | grep -v "# non-cryptographic"
grep -r "Ed25519" app/ --exclude-dir=venv
grep -r "ChaCha20" app/ --exclude-dir=venv

# Expected: No results (or only documented non-cryptographic uses)
```

#### TLS Configuration Audit
```bash
# Test TLS configuration with nmap
nmap --script ssl-enum-ciphers -p 443 app.wegweiser.tech

# Expected: Only FIPS-approved cipher suites

# Test with testssl.sh
./testssl.sh --protocols --ciphers app.wegweiser.tech

# Expected: TLS 1.2+, FIPS-approved ciphers only
```

#### FIPS Mode Verification
```bash
# Verify FIPS mode on all systems
ansible all -m shell -a "fips-mode-setup --check"

# Expected: "FIPS mode is enabled." on all hosts
```

### B10.2: Documentation for Compliance

**Required Documentation**:

1. **Cryptographic Module Inventory**
   - List all FIPS-validated modules with CMVP certificate numbers
   - Document versions and validation dates

2. **Algorithm Usage Matrix**
   - Document which algorithms are used for which purposes
   - Confirm all are FIPS-approved

3. **Configuration Baseline**
   - Document OS configuration (FIPS mode enabled)
   - Document application configuration (cipher suites, TLS versions)
   - Document service configuration (PostgreSQL, Redis, NATS)

4. **Deployment Procedures**
   - Step-by-step deployment guide
   - Verification procedures
   - Rollback procedures

5. **Testing Evidence**
   - Test results showing FIPS-compliant operation
   - TLS scan results
   - Algorithm audit results

---

**End of OPTION B - FIPS Deployment Profile**
