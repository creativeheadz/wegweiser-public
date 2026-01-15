# FIPS 140-2/140-3 Deployment Profile for Wegweiser

**Date**: 2025-11-07  
**Version**: 1.0  
**Target**: Azure Cloud Deployment

---

## Executive Summary

This document provides a comprehensive FIPS 140-2/140-3 deployment profile for Wegweiser across all components:
- Application server (Flask/Python)
- Agents (Windows, Linux, macOS)
- NATS messaging infrastructure
- Database (PostgreSQL)
- Cache/Session (Redis)
- Task queue (Celery)
- Web server (Gunicorn)
- Azure services (Key Vault, Front Door, Application Gateway)

**Key Principle**: Use only FIPS-validated cryptographic modules in approved mode.

---

## B1: Application Layer (Flask/Python) - FIPS Profile

### B1.1: Operating System Selection

#### Option 1: Ubuntu Pro FIPS 22.04 LTS (Recommended for Azure)

**Azure Marketplace Image**:
- Publisher: Canonical
- Offer: `ubuntu-pro-fips-22_04-lts`
- SKU: `pro-fips-22_04-lts-gen2`
- Billing: Per-vCPU hourly (Azure credits apply)

**FIPS Validation**:
- OpenSSL FIPS Provider: CMVP Certificate #4282 (OpenSSL 3.0 FIPS Provider)
- Kernel Crypto: FIPS 140-2 validated
- Maintained by Canonical with security updates

**Deployment**:
```bash
# Azure CLI deployment
az vm create \
  --resource-group wegweiser-rg \
  --name wegweiser-app-fips \
  --image Canonical:ubuntu-pro-fips-22_04-lts:pro-fips-22_04-lts-gen2:latest \
  --size Standard_D4s_v3 \
  --admin-username azureuser \
  --generate-ssh-keys

# Enable FIPS mode (pre-enabled in FIPS image)
sudo fips-mode-setup --check
# Expected: FIPS mode is enabled.
```

**Python Configuration**:
```bash
# Install Python 3.10+ with FIPS-enabled OpenSSL
sudo apt update
sudo apt install python3.10 python3.10-venv python3-pip

# Verify OpenSSL FIPS provider
python3 -c "import ssl; print(ssl.OPENSSL_VERSION)"
# Expected: OpenSSL 3.0.x FIPS

# Create virtual environment
python3 -m venv /opt/wegweiser/venv
source /opt/wegweiser/venv/bin/activate

# Install cryptography with FIPS support
pip install cryptography>=41.0.0
```

**FIPS Configuration File** (`/etc/ssl/fipsmodule.cnf`):
```ini
[fips_sect]
activate = 1
```

**OpenSSL Configuration** (`/etc/ssl/openssl.cnf`):
```ini
openssl_conf = openssl_init

[openssl_init]
providers = provider_sect

[provider_sect]
fips = fips_sect
base = base_sect

[base_sect]
activate = 1
```

#### Option 2: Red Hat Enterprise Linux 9 with FIPS Mode

**Azure Marketplace Image**:
- Publisher: RedHat
- Offer: `RHEL`
- SKU: `9-lvm-gen2`

**Enable FIPS Mode**:
```bash
# Enable FIPS mode
sudo fips-mode-setup --enable
sudo reboot

# Verify
fips-mode-setup --check
# Expected: FIPS mode is enabled.
```

**FIPS Validation**:
- OpenSSL: CMVP Certificate #4282
- NSS: CMVP Certificate #4024
- Kernel Crypto: FIPS 140-2 validated

#### Option 3: Windows Server 2022 with FIPS Policy

**Azure Marketplace Image**:
- Publisher: MicrosoftWindowsServer
- Offer: WindowsServer
- SKU: 2022-datacenter-azure-edition

**Enable FIPS Policy**:
```powershell
# Enable FIPS via Group Policy
Set-ItemProperty -Path "HKLM:\SYSTEM\CurrentControlSet\Control\Lsa\FipsAlgorithmPolicy" `
  -Name "Enabled" -Value 1

# Or via Local Security Policy GUI:
# secpol.msc → Local Policies → Security Options
# → "System cryptography: Use FIPS compliant algorithms for encryption, hashing, and signing" → Enabled

# Reboot required
Restart-Computer
```

**FIPS Validation**:
- CNG (Cryptography Next Generation): FIPS 140-2 validated
- BCrypt.dll: CMVP Certificate #3197
- SCHANNEL (TLS): FIPS-compliant

### B1.2: Python Cryptography Library Configuration

**Required Package**: `cryptography>=41.0.0`

**FIPS-Compliant Usage**:
```python
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.backends import default_backend
import os

# Password hashing (replaces bcrypt)
def hash_password_fips(password: str, iterations: int = 600000) -> str:
    """FIPS-compliant password hashing using PBKDF2-HMAC-SHA256"""
    salt = os.urandom(16)  # 128-bit salt
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),  # FIPS-approved
        length=32,  # 256-bit key
        salt=salt,
        iterations=iterations,  # OWASP 2023: 600,000+
        backend=default_backend()
    )
    key = kdf.derive(password.encode('utf-8'))
    
    # Store format: iterations$salt_hex$key_hex
    return f"{iterations}${salt.hex()}${key.hex()}"

# RSA key generation (minimum 2048-bit)
from cryptography.hazmat.primitives.asymmetric import rsa

def generate_rsa_keypair_fips():
    """FIPS-compliant RSA key generation"""
    private_key = rsa.generate_private_key(
        public_exponent=65537,  # Standard exponent
        key_size=2048,  # FIPS minimum (4096 recommended)
        backend=default_backend()
    )
    return private_key

# TLS configuration
import ssl

def create_fips_ssl_context():
    """FIPS-compliant TLS context"""
    context = ssl.create_default_context()
    
    # FIPS-approved cipher suites only
    context.set_ciphers(':'.join([
        'ECDHE-RSA-AES256-GCM-SHA384',
        'ECDHE-RSA-AES128-GCM-SHA256',
        'AES256-GCM-SHA384',
        'AES128-GCM-SHA256',
    ]))
    
    # TLS 1.2+ only (FIPS requirement)
    context.minimum_version = ssl.TLSVersion.TLSv1_2
    
    return context
```

### B1.3: Flask Application Configuration

**FIPS-Compliant Settings** (`app/__init__.py`):
```python
# Session configuration
app.config['SESSION_TYPE'] = 'redis'
app.config['SESSION_USE_SIGNER'] = True
app.config['SESSION_KEY_PREFIX'] = 'wegweiser:'

# Configure itsdangerous to use SHA-256
from itsdangerous import TimestampSigner
from hashlib import sha256

app.config['SESSION_SERIALIZATION_FORMAT'] = 'json'

# Custom signer with SHA-256
class FIPSSHA256Signer(TimestampSigner):
    default_digest_method = staticmethod(sha256)

# Apply to Flask-Session
# (Requires Flask-Session configuration update)
```

**CSRF Token Configuration**:
```python
# Flask-WTF CSRF with SHA-256
from flask_wtf.csrf import CSRFProtect

csrf = CSRFProtect()
csrf.init_app(app)

# Configure CSRFProtect to use SHA-256
# (May require Flask-WTF update or custom implementation)
```

### B1.4: Gunicorn TLS Configuration

**FIPS-Compliant Gunicorn Config** (`gunicorn.conf.py`):
```python
import ssl

# TLS configuration
keyfile = '/opt/wegweiser/certs/server.key'
certfile = '/opt/wegweiser/certs/server.crt'
ca_certs = '/opt/wegweiser/certs/ca-bundle.crt'

# FIPS-approved cipher suites
ciphers = ':'.join([
    'ECDHE-RSA-AES256-GCM-SHA384',
    'ECDHE-RSA-AES128-GCM-SHA256',
    'ECDHE-ECDSA-AES256-GCM-SHA384',
    'ECDHE-ECDSA-AES128-GCM-SHA256',
    'AES256-GCM-SHA384',
    'AES128-GCM-SHA256',
])

# TLS version
ssl_version = ssl.PROTOCOL_TLS_SERVER  # TLS 1.2+

# Disable SSLv3, TLS 1.0, TLS 1.1
```

---

## B2: Agent Layer (Windows/Linux/macOS) - FIPS Profile

### B2.1: Windows Agent FIPS Configuration

**Operating System**: Windows 10/11 Pro/Enterprise or Windows Server 2019/2022

**Enable FIPS Policy**:
```powershell
# Via Registry
Set-ItemProperty -Path "HKLM:\SYSTEM\CurrentControlSet\Control\Lsa\FipsAlgorithmPolicy" `
  -Name "Enabled" -Value 1

# Via Group Policy (recommended for domain-joined machines)
# Computer Configuration → Windows Settings → Security Settings → Local Policies → Security Options
# → "System cryptography: Use FIPS compliant algorithms" → Enabled

Restart-Computer
```

**Python Embedded Distribution**:
- Location: `installerFiles/Windows/python-weg/`
- Version: Python 3.11+ with OpenSSL 3.0 FIPS module
- **Action Required**: Rebuild with FIPS-enabled OpenSSL

**Agent Crypto Configuration** (`installerFiles/Windows/Agent/core/crypto.py`):
```python
# Already uses 4096-bit RSA ✅
KEY_SIZE = 4096

# Verify FIPS mode
import ssl
print(f"OpenSSL version: {ssl.OPENSSL_VERSION}")
print(f"FIPS mode: {ssl.OPENSSL_VERSION_INFO}")
```

**NATS TLS Configuration** (`installerFiles/Windows/Agent/config/nats_config.json`):
```json
{
  "servers": ["tls://nats.wegweiser.tech:443"],
  "tls": {
    "cert_file": "certs/client.crt",
    "key_file": "certs/client.key",
    "ca_file": "certs/ca.crt",
    "min_version": "1.2",
    "ciphers": [
      "ECDHE-RSA-AES256-GCM-SHA384",
      "ECDHE-RSA-AES128-GCM-SHA256",
      "AES256-GCM-SHA384",
      "AES128-GCM-SHA256"
    ]
  }
}
```

### B2.2: Linux Agent FIPS Configuration

**Supported Distributions**:
- Ubuntu Pro FIPS 20.04/22.04 LTS
- Red Hat Enterprise Linux 8/9 with FIPS mode
- CentOS Stream 9 with FIPS mode

**Enable FIPS Mode** (RHEL/CentOS):
```bash
sudo fips-mode-setup --enable
sudo reboot
fips-mode-setup --check
```

**Enable FIPS Mode** (Ubuntu Pro):
```bash
# Ubuntu Pro FIPS is pre-configured
sudo pro status
# Should show: fips: enabled

# Verify OpenSSL FIPS provider
openssl list -providers
# Should show: fips
```

**Agent Installation**:
```bash
# Install to /opt/wegweiser/agent/
sudo mkdir -p /opt/wegweiser/agent
sudo cp -r installerFiles/Linux/Agent/* /opt/wegweiser/agent/

# Install Python dependencies with FIPS-enabled OpenSSL
python3 -m venv /opt/wegweiser/agent/venv
source /opt/wegweiser/agent/venv/bin/activate
pip install -r requirements.txt

# Verify cryptography uses FIPS provider
python3 -c "from cryptography.hazmat.backends.openssl import backend; print(backend.openssl_version_text())"
```

**Systemd Service** (`/etc/systemd/system/wegweiser-agent.service`):
```ini
[Unit]
Description=Wegweiser NATS Agent
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=wegweiser
Group=wegweiser
WorkingDirectory=/opt/wegweiser/agent
Environment="OPENSSL_CONF=/etc/ssl/openssl.cnf"
Environment="OPENSSL_MODULES=/usr/lib/x86_64-linux-gnu/ossl-modules"
ExecStart=/opt/wegweiser/agent/venv/bin/python3 nats_persistent_agent.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

### B2.3: macOS Agent FIPS Configuration

**Challenge**: macOS does not have native FIPS mode.

**Options**:

#### Option 1: Use FIPS-Validated OpenSSL (Recommended)
```bash
# Install OpenSSL 3.0 with FIPS module via Homebrew
brew install openssl@3

# Configure FIPS provider
export OPENSSL_CONF=/usr/local/etc/openssl@3/openssl.cnf
export OPENSSL_MODULES=/usr/local/Cellar/openssl@3/3.x.x/lib/ossl-modules

# Build Python with FIPS-enabled OpenSSL
brew install python@3.11 --with-openssl@3

# Install agent
sudo mkdir -p /opt/wegweiser/agent
sudo cp -r installerFiles/MacOS/Agent/* /opt/wegweiser/agent/

# Create virtual environment
python3.11 -m venv /opt/wegweiser/agent/venv
source /opt/wegweiser/agent/venv/bin/activate
pip install -r requirements.txt
```

#### Option 2: Document as Non-FIPS Endpoint
- macOS agents operate in non-FIPS mode
- Server validates agent identity via RSA signatures
- TLS encryption still uses strong ciphers
- Document as "managed endpoint" exception

**LaunchDaemon** (`/Library/LaunchDaemons/tech.wegweiser.agent.plist`):
```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>tech.wegweiser.agent</string>
    <key>ProgramArguments</key>
    <array>
        <string>/opt/wegweiser/agent/venv/bin/python3</string>
        <string>/opt/wegweiser/agent/nats_persistent_agent.py</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>StandardOutPath</key>
    <string>/var/log/wegweiser-agent.log</string>
    <key>StandardErrorPath</key>
    <string>/var/log/wegweiser-agent-error.log</string>
    <key>EnvironmentVariables</key>
    <dict>
        <key>OPENSSL_CONF</key>
        <string>/usr/local/etc/openssl@3/openssl.cnf</string>
    </dict>
</dict>
</plist>
```

### B2.4: Agent Update Mechanism - FIPS Considerations

**Current Mechanism**: Snippet-based updates with RSA signature verification

**FIPS Compliance**:
- ✅ RSA signatures use PKCS1v15 + SHA-256 (already compliant)
- ✅ Signature verification in `core/crypto.py` uses 4096-bit keys
- ❌ Legacy agents (`agent/agent.py`, `downloads/agent.py`) use 1024-bit keys

**Action Required**:
1. Update `agent/agent.py` and `downloads/agent.py` to use 2048-bit minimum
2. Regenerate all agent keys with 2048-bit or 4096-bit RSA
3. Push key rotation via snippet update mechanism
4. Server accepts both old and new keys during transition (30-day window)

---

## B3: NATS Infrastructure - FIPS Profile

### B3.1: NATS Server FIPS Configuration

**NATS Server Version**: 2.10+ with TLS 1.2/1.3 support

**Build with BoringCrypto** (FIPS-validated Go crypto):
```bash
# Clone NATS server
git clone https://github.com/nats-io/nats-server.git
cd nats-server

# Build with BoringCrypto (FIPS-validated)
CGO_ENABLED=1 GOEXPERIMENT=boringcrypto go build -tags=boringcrypto -o nats-server

# Verify BoringCrypto
./nats-server --version
# Should indicate BoringCrypto build
```

**NATS Server Configuration** (`nats-server.conf`):
```conf
# Server identity
server_name: wegweiser-nats-01

# Listen on TLS port
port: 4222
https: 443

# TLS configuration
tls {
  cert_file: "/etc/nats/certs/server.crt"
  key_file: "/etc/nats/certs/server.key"
  ca_file: "/etc/nats/certs/ca.crt"

  # FIPS-approved cipher suites
  cipher_suites: [
    "TLS_ECDHE_RSA_WITH_AES_256_GCM_SHA384",
    "TLS_ECDHE_RSA_WITH_AES_128_GCM_SHA256",
    "TLS_RSA_WITH_AES_256_GCM_SHA384",
    "TLS_RSA_WITH_AES_128_GCM_SHA256"
  ]

  # TLS 1.2 minimum
  min_version: "1.2"

  # Verify client certificates
  verify: true
  verify_and_map: true
}

# Authentication
authorization {
  users = [
    {
      user: "tenant_<uuid>"
      password: "$2a$11$..." # bcrypt hash (REPLACE with PBKDF2)
      permissions: {
        publish: ["tenant.<uuid>.>"]
        subscribe: ["tenant.<uuid>.>"]
      }
    }
  ]
}

# Jetstream (persistent messaging)
jetstream {
  store_dir: "/var/lib/nats/jetstream"
  max_memory_store: 1GB
  max_file_store: 10GB
}

# Monitoring
http_port: 8222
```

**FIPS Validation**:
- BoringCrypto: FIPS 140-2 validated (CMVP Certificate #2964)
- TLS implementation: FIPS-compliant
- Cipher suites: FIPS-approved only

### B3.2: NATS Client Configuration (Python)

**Python NATS Client**: `nats-py` library

**FIPS-Compliant Connection**:
```python
import nats
import ssl

async def connect_nats_fips():
    # Create FIPS-compliant SSL context
    ssl_ctx = ssl.create_default_context(
        purpose=ssl.Purpose.SERVER_AUTH,
        cafile="/opt/wegweiser/certs/ca.crt"
    )
    ssl_ctx.load_cert_chain(
        certfile="/opt/wegweiser/certs/client.crt",
        keyfile="/opt/wegweiser/certs/client.key"
    )

    # FIPS-approved cipher suites
    ssl_ctx.set_ciphers(':'.join([
        'ECDHE-RSA-AES256-GCM-SHA384',
        'ECDHE-RSA-AES128-GCM-SHA256',
        'AES256-GCM-SHA384',
        'AES128-GCM-SHA256',
    ]))

    # TLS 1.2 minimum
    ssl_ctx.minimum_version = ssl.TLSVersion.TLSv1_2

    # Connect to NATS
    nc = await nats.connect(
        servers=["tls://nats.wegweiser.tech:443"],
        tls=ssl_ctx,
        user="tenant_<uuid>",
        password="<password>"  # From PBKDF2, not bcrypt
    )

    return nc
```

### B3.3: NATS Authentication - Replace Bcrypt

**Current**: NATS uses bcrypt for password hashing (NOT FIPS-approved)

**Solution**: Use NATS with external authentication (webhook)

**NATS Server Config** (with auth webhook):
```conf
authorization {
  # External authentication via webhook
  auth_callout {
    # Wegweiser auth endpoint
    issuer: "wegweiser-auth"
    auth_users: [ "auth-service" ]

    # Webhook URL
    account: "AUTH"
    url: "https://app.wegweiser.tech/api/nats/auth"

    # TLS for webhook
    tls {
      cert_file: "/etc/nats/certs/webhook-client.crt"
      key_file: "/etc/nats/certs/webhook-client.key"
      ca_file: "/etc/nats/certs/ca.crt"
    }
  }
}
```

**Wegweiser Auth Endpoint** (`app/routes/nats/auth.py`):
```python
from flask import Blueprint, request, jsonify
from app.utilities.crypto_fips import verify_password_fips

nats_auth_bp = Blueprint('nats_auth', __name__)

@nats_auth_bp.route('/api/nats/auth', methods=['POST'])
def nats_authenticate():
    """NATS authentication webhook with FIPS-compliant password verification"""
    data = request.json
    username = data.get('user')
    password = data.get('password')

    # Look up user credentials
    tenant = Tenant.query.filter_by(nats_username=username).first()
    if not tenant:
        return jsonify({"error": "invalid credentials"}), 401

    # Verify password with PBKDF2-HMAC-SHA256
    if not verify_password_fips(password, tenant.nats_password_hash):
        return jsonify({"error": "invalid credentials"}), 401

    # Return permissions
    return jsonify({
        "user": username,
        "permissions": {
            "publish": [f"tenant.{tenant.uuid}.>"],
            "subscribe": [f"tenant.{tenant.uuid}.>"]
        }
    }), 200
```

---

## B4: Database Layer (PostgreSQL) - FIPS Profile

### B4.1: PostgreSQL FIPS Configuration

**PostgreSQL Version**: 14+ with OpenSSL 3.0 FIPS module

**Installation on Ubuntu Pro FIPS**:
```bash
# Install PostgreSQL
sudo apt install postgresql-14 postgresql-contrib-14

# Verify OpenSSL FIPS
sudo -u postgres psql -c "SHOW ssl_library;"
# Expected: OpenSSL 3.0.x

# Enable SSL
sudo -u postgres psql -c "ALTER SYSTEM SET ssl = on;"
sudo -u postgres psql -c "ALTER SYSTEM SET ssl_cert_file = '/etc/postgresql/14/main/server.crt';"
sudo -u postgres psql -c "ALTER SYSTEM SET ssl_key_file = '/etc/postgresql/14/main/server.key';"
sudo -u postgres psql -c "ALTER SYSTEM SET ssl_ca_file = '/etc/postgresql/14/main/ca.crt';"

# FIPS-approved cipher suites
sudo -u postgres psql -c "ALTER SYSTEM SET ssl_ciphers = 'ECDHE-RSA-AES256-GCM-SHA384:ECDHE-RSA-AES128-GCM-SHA256:AES256-GCM-SHA384:AES128-GCM-SHA256';"

# TLS 1.2 minimum
sudo -u postgres psql -c "ALTER SYSTEM SET ssl_min_protocol_version = 'TLSv1.2';"

# Reload configuration
sudo systemctl reload postgresql
```

**PostgreSQL Connection String** (FIPS-compliant):
```python
# app/__init__.py
SQLALCHEMY_DATABASE_URI = (
    f"postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"
    f"?sslmode=verify-full"
    f"&sslcert=/opt/wegweiser/certs/client.crt"
    f"&sslkey=/opt/wegweiser/certs/client.key"
    f"&sslrootcert=/opt/wegweiser/certs/ca.crt"
)
```

### B4.2: Azure Database for PostgreSQL - FIPS

**Azure Service**: Azure Database for PostgreSQL Flexible Server

**FIPS Compliance**:
- TLS 1.2+ enforced
- FIPS 140-2 validated cryptographic modules
- Managed by Microsoft (no OS-level configuration needed)

**Configuration**:
```bash
# Azure CLI - Create FIPS-compliant PostgreSQL
az postgres flexible-server create \
  --resource-group wegweiser-rg \
  --name wegweiser-db-fips \
  --location eastus \
  --admin-user wegweiseradmin \
  --admin-password '<strong-password>' \
  --sku-name Standard_D4s_v3 \
  --tier GeneralPurpose \
  --version 14 \
  --storage-size 128 \
  --ssl-enforcement Enabled \
  --minimal-tls-version TLS1_2

# Configure firewall (allow Azure services)
az postgres flexible-server firewall-rule create \
  --resource-group wegweiser-rg \
  --name wegweiser-db-fips \
  --rule-name AllowAzureServices \
  --start-ip-address 0.0.0.0 \
  --end-ip-address 0.0.0.0
```

**Connection String**:
```python
SQLALCHEMY_DATABASE_URI = (
    f"postgresql://{db_user}@{server_name}:{db_password}"
    f"@{server_name}.postgres.database.azure.com:5432/{db_name}"
    f"?sslmode=require"
)
```

---

## B5: Cache/Session Layer (Redis) - FIPS Profile

### B5.1: Redis FIPS Configuration

**Redis Version**: 6.2+ with TLS support

**Build with OpenSSL FIPS** (Ubuntu Pro FIPS):
```bash
# Install Redis from source with FIPS-enabled OpenSSL
wget https://download.redis.io/releases/redis-7.2.3.tar.gz
tar xzf redis-7.2.3.tar.gz
cd redis-7.2.3

# Build with TLS support
make BUILD_TLS=yes USE_SYSTEMD=yes

# Install
sudo make install

# Create systemd service
sudo cp utils/systemd-redis_server.service /etc/systemd/system/redis.service
sudo systemctl daemon-reload
```

**Redis Configuration** (`/etc/redis/redis.conf`):
```conf
# TLS configuration
port 0
tls-port 6379

tls-cert-file /etc/redis/certs/redis.crt
tls-key-file /etc/redis/certs/redis.key
tls-ca-cert-file /etc/redis/certs/ca.crt

# FIPS-approved cipher suites
tls-ciphers ECDHE-RSA-AES256-GCM-SHA384:ECDHE-RSA-AES128-GCM-SHA256:AES256-GCM-SHA384:AES128-GCM-SHA256

# TLS 1.2 minimum
tls-protocols "TLSv1.2 TLSv1.3"

# Client certificate verification
tls-auth-clients yes

# Persistence
save 900 1
save 300 10
save 60 10000

# AOF
appendonly yes
appendfsync everysec
```

**Python Redis Client** (FIPS-compliant):
```python
import redis
import ssl

# Create FIPS-compliant SSL context
ssl_ctx = ssl.create_default_context(
    cafile="/opt/wegweiser/certs/ca.crt"
)
ssl_ctx.load_cert_chain(
    certfile="/opt/wegweiser/certs/client.crt",
    keyfile="/opt/wegweiser/certs/client.key"
)
ssl_ctx.set_ciphers(':'.join([
    'ECDHE-RSA-AES256-GCM-SHA384',
    'ECDHE-RSA-AES128-GCM-SHA256',
]))
ssl_ctx.minimum_version = ssl.TLSVersion.TLSv1_2

# Connect to Redis
redis_client = redis.Redis(
    host='redis.wegweiser.tech',
    port=6379,
    ssl=True,
    ssl_context=ssl_ctx,
    decode_responses=True
)
```

### B5.2: Azure Cache for Redis - FIPS

**Azure Service**: Azure Cache for Redis Premium tier

**FIPS Compliance**:
- FIPS 140-2 validated
- TLS 1.2+ enforced
- Managed by Microsoft

**Configuration**:
```bash
# Azure CLI - Create FIPS-compliant Redis
az redis create \
  --resource-group wegweiser-rg \
  --name wegweiser-redis-fips \
  --location eastus \
  --sku Premium \
  --vm-size P1 \
  --enable-non-ssl-port false \
  --minimum-tls-version 1.2
```

**Connection String**:
```python
REDIS_URL = (
    f"rediss://:{redis_password}@{redis_host}:6380/0"
    f"?ssl_cert_reqs=required"
)
```

---

## B6: Task Queue (Celery) - FIPS Profile

### B6.1: Celery with Redis Broker - FIPS

**Celery Configuration** (`app/__init__.py`):
```python
from celery import Celery
import ssl

# Create FIPS-compliant SSL context for Redis
broker_ssl_ctx = ssl.create_default_context(
    cafile="/opt/wegweiser/certs/ca.crt"
)
broker_ssl_ctx.load_cert_chain(
    certfile="/opt/wegweiser/certs/client.crt",
    keyfile="/opt/wegweiser/certs/client.key"
)
broker_ssl_ctx.set_ciphers('ECDHE-RSA-AES256-GCM-SHA384:ECDHE-RSA-AES128-GCM-SHA256')
broker_ssl_ctx.minimum_version = ssl.TLSVersion.TLSv1_2

# Celery app
celery = Celery(
    app.name,
    broker=f'rediss://:{redis_password}@{redis_host}:6380/0',
    backend=f'rediss://:{redis_password}@{redis_host}:6380/1',
    broker_use_ssl={
        'ssl_context': broker_ssl_ctx,
    },
    redis_backend_use_ssl={
        'ssl_context': broker_ssl_ctx,
    }
)
```

**Celery Worker Startup**:
```bash
# Start Celery worker with FIPS-enabled environment
export OPENSSL_CONF=/etc/ssl/openssl.cnf
celery -A app.celery worker --loglevel=info --concurrency=4
```

---

## Summary Table: FIPS Validation Certificates

| Component | Module | CMVP Cert | Algorithm Support |
|-----------|--------|-----------|-------------------|
| Ubuntu Pro FIPS | OpenSSL 3.0 FIPS Provider | #4282 | AES, RSA, ECDSA, SHA-2, HMAC, PBKDF2 |
| RHEL 9 | OpenSSL 3.0 | #4282 | AES, RSA, ECDSA, SHA-2, HMAC, PBKDF2 |
| Windows Server 2022 | CNG (BCrypt.dll) | #3197 | AES, RSA, ECDSA, SHA-2, HMAC, PBKDF2 |
| NATS (BoringCrypto) | Go BoringCrypto | #2964 | AES-GCM, RSA, ECDSA, SHA-2, HMAC |
| Azure Key Vault Premium | Azure HSM | #3653 | AES, RSA, ECDSA, SHA-2, HMAC |
| Azure Managed HSM | Azure Managed HSM | #3653 | AES, RSA, ECDSA, SHA-2, HMAC |

---

**End of OPTION B - Part 1**
*Continued in next section: Azure Services, Deployment Checklist, and Validation Procedures*


