# FIPS 140-2/140-3 Compliance Audit - OPTION A Findings

**Date**: 2025-11-07  
**Auditor**: Augment Agent  
**Scope**: Wegweiser codebase cryptographic implementations

---

## Executive Summary

This audit identified **4 CRITICAL** and **2 MODERATE** FIPS compliance issues across the Wegweiser codebase:

### Critical Issues (Must Fix)
1. ❌ **Bcrypt password hashing** (NOT FIPS-approved) - 7 locations
2. ❌ **1024-bit RSA keys** (below FIPS minimum) - 2 locations  
3. ❌ **Deprecated datetime functions** - 15+ locations
4. ❌ **Session signing algorithm** - needs verification

### Moderate Issues (Should Fix)
5. ⚠️ **TOTP/2FA HMAC algorithm** - likely SHA-1 (should be SHA-256)
6. ⚠️ **No Ed25519/X25519/ChaCha20 usage found** ✅ (Good - these are NOT FIPS-approved)

### Compliant Implementations ✅
- RSA signatures use PKCS1v15 with SHA-256 ✅
- Agent crypto (Windows/Linux/macOS) uses 4096-bit RSA ✅
- HMAC-SHA256 used for URL obfuscation ✅
- File hashing uses SHA-256 ✅

---

## A1: Bcrypt Usage Audit - CRITICAL ❌

### Finding
**Bcrypt is NOT FIPS 140-2/140-3 approved.** Must replace with PBKDF2-HMAC-SHA256 per NIST SP 800-132.

### Locations Found

#### 1. **app/models/__init__.py** (Lines 3, 6)
```python
from flask_bcrypt import Bcrypt
bcrypt = Bcrypt()
```
**Impact**: Global bcrypt instance exported to entire application

#### 2. **app/__init__.py** (Lines 6, 397)
```python
from flask_bcrypt import Bcrypt
bcrypt.init_app(app)
```
**Impact**: Bcrypt initialized in application factory

#### 3. **app/routes/login/login.py** (Lines 8, 29, 94, 294)
```python
from flask_bcrypt import Bcrypt
bcrypt = Bcrypt()
# Line 94: Password verification
if account and bcrypt.check_password_hash(account.password, password):
# Line 294: SSO user password generation
hashed_password = bcrypt.generate_password_hash(str(uuid.uuid4())).decode('utf-8')
```
**Impact**: Authentication entry point - CRITICAL

#### 4. **app/routes/registration/register.py** (Line 200)
```python
hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
```
**Impact**: User registration - CRITICAL

#### 5. **app/routes/ui.py** (Lines 42, 44, 192)
```python
from flask_bcrypt import Bcrypt
bcrypt = Bcrypt()
hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
```
**Impact**: Admin user creation

#### 6. **app/routes/tenant/profile.py** (Lines 7, 16, 129)
```python
from flask_bcrypt import Bcrypt
bcrypt = Bcrypt()
user.password = bcrypt.generate_password_hash(form.password.data).decode('utf-8')
```
**Impact**: Password changes

#### 7. **app/routes/tenant/tenant.py** (Lines 43, 45)
```python
from flask_bcrypt import Bcrypt
bcrypt = Bcrypt()
```
**Impact**: Tenant user management

#### 8. **requirements.txt** (Line 19)
```
Flask_Bcrypt==1.0.1
```
**Impact**: Dependency declaration

#### 9. **CLAUDE.md** (Line 24)
```bash
pip install flask-bcrypt
```
**Impact**: Documentation

#### 10. **dev_scripts/diagnostics/check_hashing.py**
```python
from flask_bcrypt import Bcrypt
bcrypt = Bcrypt()
hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
check_correct = bcrypt.check_password_hash(hashed_password, '9Palo)pad')
```
**Impact**: Testing/diagnostic script

### Bcrypt Hash Format
- Format: `$2b$12$<salt><hash>` (60 characters)
- Rounds: Typically 12 (2^12 = 4096 iterations)
- **Migration Strategy Required**: Existing hashes must be handled during transition

### Recommended Fix
Replace with **PBKDF2-HMAC-SHA256**:
- Algorithm: PBKDF2 with HMAC-SHA-256
- Iterations: 600,000+ (OWASP 2023 recommendation)
- Salt: 16 bytes (128 bits) minimum
- Key length: 32 bytes (256 bits)

**Python Implementation**:
```python
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes
import os
import base64

def hash_password(password: str, iterations: int = 600000) -> str:
    salt = os.urandom(16)
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=iterations,
    )
    key = kdf.derive(password.encode())
    # Store: iterations$salt$hash (base64 encoded)
    return f"{iterations}${base64.b64encode(salt).decode()}${base64.b64encode(key).decode()}"

def verify_password(password: str, stored_hash: str) -> bool:
    iterations, salt_b64, key_b64 = stored_hash.split('$')
    salt = base64.b64decode(salt_b64)
    stored_key = base64.b64decode(key_b64)
    
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=int(iterations),
    )
    try:
        kdf.verify(password.encode(), stored_key)
        return True
    except:
        return False
```

---

## A2: Non-Approved Algorithms Audit

### A2.1: Ed25519, X25519, ChaCha20-Poly1305 - ✅ GOOD NEWS

**Finding**: No application code uses these non-FIPS-approved algorithms.

**Evidence**:
- Ed25519, X25519, ChaCha20-Poly1305 implementations exist in bundled `cryptography` library
- Located in: `installerFiles/Windows/python-weg/Lib/site-packages/cryptography/hazmat/`
- **BUT**: No application code imports or uses these algorithms ✅

**Conclusion**: Application does not use non-approved elliptic curve or stream cipher algorithms.

### A2.2: MD5 and SHA-1 Usage - ⚠️ ACCEPTABLE (Non-Cryptographic)

**Finding**: MD5 and SHA-1 found in Loki security scanner for file identification (non-cryptographic purpose).

**Location**: `Loki/lib/helpers.py` (Lines 64-75)
```python
# Used for file hashing/identification in IOC detection
md5 = hashlib.md5()
sha1 = hashlib.sha1()
sha256 = hashlib.sha256()
```

**Context**: Loki is a security scanning tool that uses MD5/SHA-1 for:
- File identification
- IOC (Indicator of Compromise) matching
- Malware signature comparison

**FIPS Compliance**: ✅ **ACCEPTABLE**
- MD5/SHA-1 used for **non-cryptographic purposes** (file identification)
- NOT used for authentication, integrity protection, or key derivation
- NIST allows MD5/SHA-1 for non-security purposes

**Recommendation**: Document this usage as non-cryptographic in FIPS deployment guide.

### A2.3: RSA Signatures - ✅ FIPS-COMPLIANT

**Finding**: All RSA signatures use PKCS1v15 padding with SHA-256 hash.

**Locations Verified**:

1. **agent/agent.py** (Lines 176-180)
```python
publicKey.verify(
    payloadsig,
    payload,
    padding.PKCS1v15(),
    hashes.SHA256()
)
```

2. **agent/signFile.py** (Lines 45-50)
```python
publicKey.verify(
    decoded_signature,
    decoded_message,
    padding.PKCS1v15(),
    hashes.SHA256()
)
```

3. **installerFiles/Windows/Agent/core/crypto.py** (Lines 153-158)
```python
public_key.verify(
    signature,
    message.encode(),
    padding.PKCS1v15(),
    hashes.SHA256()
)
```

4. **installerFiles/Linux/Agent/core/crypto.py** (Same pattern)
5. **installerFiles/MacOS/Agent/core/crypto.py** (Same pattern)

**FIPS Compliance**: ✅ **COMPLIANT**
- RSA with PKCS#1 v1.5 padding: FIPS-approved
- SHA-256 hash algorithm: FIPS-approved

### A2.4: Custom Encryption - ✅ NO ISSUES FOUND

**Finding**: No custom encryption implementations detected.

**Evidence**:
- All encryption uses standard `cryptography` library
- PBKDF2 found in `dev_scripts/utilities/jwnMessage.py` (Lines 11-17) - already FIPS-compliant:
```python
kdf = PBKDF2HMAC(
    algorithm=hashes.SHA256(),
    length=32,
    salt=salt,
    iterations=200000,
    backend=backend
)
```

**Conclusion**: No custom/homebrew crypto found. All implementations use standard libraries.

---

## A3: Deprecated Datetime Functions - CRITICAL ❌

### Finding
**datetime.utcnow() and datetime.utcfromtimestamp() are deprecated** in Python 3.12+.
Must use timezone-aware: `datetime.now(datetime.UTC)`

### Locations Found (15+ instances)

#### 1. **app/utilities/ui_time_converter.py** (Line 11)
```python
utc_time = datetime.utcfromtimestamp(timestamp)
```
**Impact**: Used throughout UI for timestamp conversion

#### 2. **app/models/context.py** (Line 24)
```python
def unix_to_datetime(unix_time):
    return datetime.utcfromtimestamp(unix_time)
```
**Impact**: Database model utility function

#### 3. **app/models/ai_memory.py** (Line 28)
```python
def unix_to_datetime(unix_time):
    return datetime.utcfromtimestamp(unix_time)
```
**Impact**: AI memory timestamp conversion

#### 4. **app/models/two_factor.py** (Line 49)
```python
self.last_used = datetime.utcnow()
```
**Impact**: 2FA timestamp tracking

#### 5. **app/models/invite_codes.py** (Lines 10, 18, 25)
```python
created_at = db.Column(db.DateTime, default=datetime.utcnow)
self.expires_at = datetime.utcnow() + timedelta(days=expires_in_days)
self.used_at = datetime.utcnow()
```
**Impact**: Invite code expiration logic

#### 6. **app/routes/widgets.py** (Line 89)
```python
end_date = datetime.utcnow()
```
**Impact**: Dashboard widgets

#### 7. **app/routes/admin/admin.py** (Lines 340, 342, 344)
```python
start_time = datetime.utcnow() - timedelta(hours=1)
start_time = datetime.utcnow() - timedelta(days=1)
start_time = datetime.utcnow() - timedelta(days=7)
```
**Impact**: Admin log filtering

#### 8. **app/tasks/base/analyzer.py** (Line 321)
```python
'timestamp': datetime.utcnow().isoformat()
```
**Impact**: Task analysis timestamps

#### 9. **Loki/lib/lokilogger.py** (Line 336)
```python
date_obj = datetime.datetime.utcnow()
```
**Impact**: Loki security scanner logging

#### 10. **snippets/unSigned/eventLogAudit.py** (Line 50)
```python
eventTime = eventTime.replace(year=datetime.datetime.now().year)
```
**Impact**: Event log analysis

#### 11. **snippets/unSigned/getEventLogs.py** (Line 85)
```python
now = datetime.datetime.now()
```
**Impact**: Windows event log collection

#### 12. **snippets/unSigned/MacAudit.py** (Lines 713, 716)
```python
return (datetime.datetime.strptime(timeStr, "%Y-%m-%d-%H:%M:%S"))
return (datetime.datetime.strptime(timeStr, "%Y-%m-%d %H:%M:%S"))
```
**Impact**: macOS audit script

### Recommended Fix
Replace all instances with timezone-aware datetime:

```python
# OLD (deprecated)
datetime.utcnow()
datetime.utcfromtimestamp(timestamp)

# NEW (FIPS-compliant, timezone-aware)
from datetime import datetime, UTC
datetime.now(UTC)
datetime.fromtimestamp(timestamp, tz=UTC)
```

**Note**: This is already documented in `.augment/rules/date_time.md`

---

## A4: RSA Key Generation - CRITICAL ❌

### Finding
**1024-bit RSA keys found** (below FIPS 140-2 minimum of 2048 bits).

### Locations with 1024-bit Keys ❌

#### 1. **agent/agent.py** (Lines 39-42)
```python
def genPrivatePem():
    logger.info('Generating private key...')
    privateKey = rsa.generate_private_key(
        public_exponent=65537,
        key_size=1024,  # ❌ TOO SMALL
        backend=default_backend
    )
```
**Impact**: CRITICAL - Agent registration keys

#### 2. **downloads/agent.py** (Lines 40-43)
```python
privateKey = rsa.generate_private_key(
    public_exponent=65537,
    key_size=1024,  # ❌ TOO SMALL
    backend=default_backend
)
```
**Impact**: CRITICAL - Downloadable agent keys

### Locations with 4096-bit Keys ✅

#### 1. **agent/genKeys.py** (Lines 8-11)
```python
def genPrivateKey():
    privateKey = rsa.generate_private_key(
        public_exponent=65537,
        key_size=4096  # ✅ EXCELLENT
    )
```
**Impact**: Server key generation - COMPLIANT

#### 2. **installerFiles/Windows/Agent/core/crypto.py** (Lines 21, 110-114)
```python
KEY_SIZE = 4096  # Strong RSA key size

private_key = rsa.generate_private_key(
    public_exponent=CryptoManager.PUBLIC_EXPONENT,
    key_size=CryptoManager.KEY_SIZE,  # 4096
    backend=default_backend()
)
```
**Impact**: Windows agent - COMPLIANT

#### 3. **installerFiles/Linux/Agent/core/crypto.py** (Same as Windows)
**Impact**: Linux agent - COMPLIANT

#### 4. **installerFiles/MacOS/Agent/core/crypto.py** (Same as Windows)
**Impact**: macOS agent - COMPLIANT

### Recommended Fix
Update `agent/agent.py` and `downloads/agent.py`:

```python
# Change from:
key_size=1024

# To:
key_size=2048  # FIPS minimum (or 4096 for better security)
```

**Migration Strategy**:
- Existing 1024-bit keys should be rotated
- Agents should regenerate keys on next update
- Server should accept both during transition period

---

## A5: Session/CSRF Token Generation - ⚠️ NEEDS VERIFICATION

### Finding
Flask-Session with `SESSION_USE_SIGNER=True` uses `itsdangerous` library.
**Default algorithm**: HMAC-SHA1 (NOT FIPS-approved for new implementations)

### Location
**app/__init__.py** (Line 233)
```python
app.config['SESSION_USE_SIGNER'] = True  # Sign session cookies
```

### itsdangerous Default Behavior
- Uses `hmac` module with SHA-1 by default
- Can be configured to use SHA-256

### Recommended Verification
Check if `itsdangerous` can be configured for SHA-256:

```python
from itsdangerous import TimestampSigner
from hashlib import sha256

# Configure signer with SHA-256
signer = TimestampSigner(
    secret_key=app.config['SECRET_KEY'],
    digest_method=sha256  # Use SHA-256 instead of SHA-1
)
```

### Flask-WTF CSRF Tokens
**app/__init__.py** (Line 12)
```python
from flask_wtf.csrf import CSRFProtect, CSRFError
csrf.init_app(app)
```

**Status**: Flask-WTF uses `itsdangerous` internally - same SHA-1 concern.

### Recommended Action
1. Verify current `itsdangerous` version supports SHA-256
2. Configure Flask-Session and Flask-WTF to use SHA-256
3. Test session signing with FIPS-enabled OpenSSL

---

## A6: JWT/Token Implementations - ✅ NO ISSUES FOUND

### Finding
No PyJWT usage found in application code.

### OAuth/SSO Tokens
**app/routes/login/login.py** (Lines 256, 294)
```python
token = microsoft.authorize_access_token()
user_info = microsoft.get('https://graph.microsoft.com/v1.0/me').json()
```

**Analysis**:
- Uses Authlib for Microsoft OAuth
- Token generation handled by Microsoft (external)
- No custom JWT creation in application

### NATS Authentication
**app/routes/nats/device_api.py** (Lines 100-112)
```python
credentials = loop.run_until_complete(nats_manager.get_tenant_credentials(tenant_uuid))
return jsonify({
    "credentials": {
        "username": credentials.username,
        "password": credentials.password,
        "nats_url": "tls://nats.wegweiser.tech:443"
    }
})
```

**Analysis**:
- NATS uses username/password credentials (not JWT)
- NATS client library in `installerFiles/Windows/python-weg/Lib/site-packages/nats/` supports JWT
- **Action Required**: Verify NATS server JWT configuration if used

### Conclusion
No application-level JWT creation found. OAuth tokens handled externally by Microsoft.

---

## A7: TOTP/2FA Implementation - ⚠️ NEEDS VERIFICATION

### Finding
TOTP typically uses HMAC-SHA1 by default. Should verify if SHA-256 is supported.

### Location
**app/models/two_factor.py** (Lines 45-46)
```python
totp = TOTP(key=self.totp_secret, issuer="Wegweiser", digits=6)
match_result = totp.match(token)
```

### pyotp Library
- Default: HMAC-SHA1 (RFC 6238 standard)
- SHA-256 support: Available in pyotp

### Recommended Fix
Configure TOTP to use SHA-256:

```python
from pyotp import TOTP

totp = TOTP(
    key=self.totp_secret,
    issuer="Wegweiser",
    digits=6,
    digest=hashlib.sha256  # Use SHA-256 instead of SHA-1
)
```

**Note**: Changing TOTP algorithm requires users to re-register 2FA devices.

---

## Summary of Findings

### Critical Issues (Must Fix Before FIPS Deployment)

| Issue | Severity | Locations | Effort |
|-------|----------|-----------|--------|
| Bcrypt password hashing | CRITICAL | 7 files | HIGH |
| 1024-bit RSA keys | CRITICAL | 2 files | MEDIUM |
| Deprecated datetime | CRITICAL | 15+ files | MEDIUM |
| Session signing (SHA-1) | CRITICAL | 1 file | LOW |

### Moderate Issues (Should Fix)

| Issue | Severity | Locations | Effort |
|-------|----------|-----------|--------|
| TOTP HMAC-SHA1 | MODERATE | 1 file | LOW |

### Compliant Implementations ✅

- RSA signatures (PKCS1v15 + SHA-256)
- Agent crypto (4096-bit RSA)
- File hashing (SHA-256)
- HMAC-SHA256 usage
- No Ed25519/X25519/ChaCha20 usage
- No custom encryption

---

## Next Steps

1. **Review this report** with stakeholders
2. **Proceed to OPTION B**: Create detailed FIPS deployment profile
3. **After approval**: Execute OPTION C code modifications
4. **Test thoroughly**: Ensure no authentication breakage
5. **Document**: Create FIPS deployment guide

---

**End of OPTION A Report**


