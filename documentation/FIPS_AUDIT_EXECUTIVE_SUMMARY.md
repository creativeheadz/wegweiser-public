# FIPS 140-2/140-3 Compliance Audit - Executive Summary

**Date**: 2025-11-07  
**Project**: Wegweiser - AI-Powered MSP Intelligence Platform  
**Audit Scope**: Comprehensive cryptographic compliance review  
**Status**: ✅ OPTION A & B COMPLETE - Awaiting approval for OPTION C (Code Modifications)

---

## 🎯 Executive Summary

Wegweiser can achieve **FIPS 140-2/140-3 compatibility** by deploying on FIPS-enabled infrastructure and making targeted code modifications. The audit identified **4 critical** and **2 moderate** issues that must be addressed before claiming FIPS compatibility.

### ✅ What You Can Claim

**Recommended Language**:
> "When deployed on FIPS-enabled infrastructure (Ubuntu Pro FIPS, RHEL with FIPS mode, or Windows Server with FIPS policy) and configured to use Azure FIPS-validated services (Key Vault Premium, Front Door, Application Gateway), Wegweiser uses only FIPS 140-2/140-3 validated cryptographic modules for all security operations including TLS, password hashing (PBKDF2-HMAC-SHA256), and digital signatures (RSA-2048+ with SHA-256)."

**Avoid Saying**:
- "FIPS certified product" (only modules are certified, not applications)
- "FIPS compliant application" (implies your code was validated)

---

## 📊 Audit Findings Summary

### Critical Issues (Must Fix) ❌

| # | Issue | Impact | Locations | Effort | Priority |
|---|-------|--------|-----------|--------|----------|
| 1 | **Bcrypt password hashing** | NOT FIPS-approved | 7 files | HIGH | P0 |
| 2 | **1024-bit RSA keys** | Below FIPS minimum | 2 files | MEDIUM | P0 |
| 3 | **Deprecated datetime** | Python 3.12+ compatibility | 15+ files | MEDIUM | P1 |
| 4 | **Session signing (SHA-1)** | itsdangerous default | 1 file | LOW | P0 |

### Moderate Issues (Should Fix) ⚠️

| # | Issue | Impact | Locations | Effort | Priority |
|---|-------|--------|-----------|--------|----------|
| 5 | **TOTP HMAC-SHA1** | Should use SHA-256 | 1 file | LOW | P1 |

### Compliant Implementations ✅

- ✅ RSA signatures use PKCS1v15 with SHA-256
- ✅ Agent crypto (Windows/Linux/macOS) uses 4096-bit RSA
- ✅ File hashing uses SHA-256
- ✅ HMAC-SHA256 used for URL obfuscation
- ✅ No Ed25519/X25519/ChaCha20 usage in application code
- ✅ No custom/homebrew encryption

---

## 💰 Azure Investment Strategy ($45K Credits)

### Recommended Azure Services (FIPS-Validated)

| Service | Purpose | Monthly Cost (Est.) | FIPS Validation |
|---------|---------|---------------------|-----------------|
| **Ubuntu Pro FIPS VM** (D4s_v3) | Application server | ~$200 | CMVP #4282 |
| **Azure Front Door Premium** | TLS termination, WAF | ~$400 | FIPS 140-2 |
| **Azure Key Vault Premium** | Secret management, HSM | ~$150 | CMVP #3653 (Level 3) |
| **Azure Database for PostgreSQL** | Database | ~$300 | FIPS 140-2 |
| **Azure Cache for Redis Premium** | Session/cache | ~$250 | FIPS 140-2 |
| **Azure Monitor + App Insights** | Logging, monitoring | ~$100 | FIPS 140-2 |
| **Total** | | **~$1,400/month** | |

**Your $45K credits = ~32 months of FIPS-compliant infrastructure** ✅

### Alternative: Lower-Cost Option

| Service | Purpose | Monthly Cost (Est.) |
|---------|---------|---------------------|
| **Ubuntu Pro FIPS VM** (D2s_v3) | Application server | ~$100 |
| **Azure Application Gateway v2** | TLS termination | ~$200 |
| **Azure Key Vault Standard** | Secret management | ~$5 |
| **Self-hosted PostgreSQL** (on FIPS VM) | Database | Included |
| **Self-hosted Redis** (on FIPS VM) | Session/cache | Included |
| **Total** | | **~$305/month** |

**Your $45K credits = ~147 months (12+ years)** ✅

---

## 🔧 Required Code Changes

### 1. Replace Bcrypt with PBKDF2-HMAC-SHA256

**Files to Modify** (7 locations):
- `app/models/__init__.py` - Remove global bcrypt instance
- `app/__init__.py` - Remove bcrypt initialization
- `app/routes/login/login.py` - Replace verification
- `app/routes/registration/register.py` - Replace hashing
- `app/routes/ui.py` - Replace admin user creation
- `app/routes/tenant/profile.py` - Replace password changes
- `app/routes/tenant/tenant.py` - Replace tenant user management

**New Implementation**:
```python
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes
import os

def hash_password_fips(password: str, iterations: int = 600000) -> str:
    salt = os.urandom(16)
    kdf = PBKDF2HMAC(algorithm=hashes.SHA256(), length=32, salt=salt, iterations=iterations)
    key = kdf.derive(password.encode())
    return f"{iterations}${salt.hex()}${key.hex()}"
```

**Migration Strategy**: Hybrid verification (support both bcrypt and PBKDF2 during transition)

### 2. Update RSA Key Generation (1024-bit → 2048-bit)

**Files to Modify** (2 locations):
- `agent/agent.py` (Line 41: `key_size=1024` → `key_size=2048`)
- `downloads/agent.py` (Line 42: `key_size=1024` → `key_size=2048`)

**Migration Strategy**: Push snippet update to rotate keys on existing agents

### 3. Replace Deprecated Datetime Functions

**Files to Modify** (15+ locations):
```python
# OLD (deprecated)
datetime.utcnow()
datetime.utcfromtimestamp(timestamp)

# NEW (FIPS-compliant, timezone-aware)
from datetime import datetime, UTC
datetime.now(UTC)
datetime.fromtimestamp(timestamp, tz=UTC)
```

### 4. Configure Session Signing for SHA-256

**File to Modify**: `app/__init__.py`
```python
from itsdangerous import TimestampSigner
from hashlib import sha256

class FIPSSHA256Signer(TimestampSigner):
    default_digest_method = staticmethod(sha256)
```

### 5. Configure TOTP for SHA-256

**File to Modify**: `app/models/two_factor.py`
```python
import hashlib
totp = TOTP(key=self.totp_secret, issuer="Wegweiser", digits=6, digest=hashlib.sha256)
```

---

## 📋 Deployment Roadmap

### Phase 1: Infrastructure Setup (Week 1)
- [ ] Deploy Ubuntu Pro FIPS 22.04 VM on Azure
- [ ] Configure Azure Front Door Premium with TLS 1.2+
- [ ] Create Azure Key Vault Premium
- [ ] Deploy Azure Database for PostgreSQL with TLS
- [ ] Deploy Azure Cache for Redis Premium with TLS
- [ ] Configure NATS server with BoringCrypto build

### Phase 2: Code Modifications (Week 2)
- [ ] Replace bcrypt with PBKDF2-HMAC-SHA256 (7 files)
- [ ] Update RSA key generation to 2048-bit (2 files)
- [ ] Replace deprecated datetime functions (15+ files)
- [ ] Configure session signing for SHA-256
- [ ] Configure TOTP for SHA-256
- [ ] Update requirements.txt (remove Flask_Bcrypt, add cryptography>=41.0.0)

### Phase 3: Testing (Week 3)
- [ ] Unit tests for password hashing/verification
- [ ] Integration tests for authentication flow
- [ ] TLS configuration testing (cipher suites, versions)
- [ ] Agent registration testing (2048-bit keys)
- [ ] Performance testing (PBKDF2 with 600,000 iterations)
- [ ] Security scanning (no non-FIPS algorithms)

### Phase 4: Migration (Week 4)
- [ ] Deploy hybrid password verification (bcrypt + PBKDF2)
- [ ] Monitor user login and automatic hash migration
- [ ] Push agent key rotation snippet
- [ ] Monitor agent key updates
- [ ] Verify all agents using 2048-bit keys

### Phase 5: Validation (Week 5)
- [ ] FIPS mode verification on all systems
- [ ] TLS scan with testssl.sh (only FIPS ciphers)
- [ ] Algorithm audit (no bcrypt, no 1024-bit keys)
- [ ] Documentation review
- [ ] Compliance statement finalization

---

## 📚 Deliverables

### Completed ✅
1. **FIPS_AUDIT_FINDINGS_OPTION_A.md** - Detailed code audit with 605 lines
2. **FIPS_DEPLOYMENT_PROFILE.md** - Infrastructure deployment guide (Part 1)
3. **FIPS_DEPLOYMENT_PROFILE_PART2.md** - Azure services and migration strategy (Part 2)
4. **FIPS_AUDIT_EXECUTIVE_SUMMARY.md** - This document

### Pending Approval 🔄
5. **OPTION C: Code Modifications** - 46 subtasks across 9 areas
   - Create FIPS-compliant crypto utilities
   - Replace bcrypt in all locations
   - Update RSA key generation
   - Replace deprecated datetime
   - Configure session/CSRF signing
   - Update TOTP configuration
   - Update dependencies
   - Create/update tests
   - Update documentation

---

## 🚦 Decision Points

### Option 1: Full FIPS Deployment (Recommended)
- **Cost**: ~$1,400/month (~$16,800/year)
- **Timeline**: 5 weeks
- **Claim**: "Deployed on FIPS-validated infrastructure with FIPS-approved algorithms"
- **Compliance**: Full FIPS 140-2/140-3 compatibility
- **Azure Credits**: Covers ~32 months

### Option 2: Budget FIPS Deployment
- **Cost**: ~$305/month (~$3,660/year)
- **Timeline**: 5 weeks
- **Claim**: Same as Option 1
- **Compliance**: Full FIPS 140-2/140-3 compatibility
- **Azure Credits**: Covers 12+ years

### Option 3: Partial FIPS (Code Only)
- **Cost**: $0 (use existing infrastructure)
- **Timeline**: 2 weeks
- **Claim**: "Uses FIPS-approved algorithms (PBKDF2, RSA-2048+, SHA-256)"
- **Compliance**: Algorithms compliant, but infrastructure not validated
- **Azure Credits**: Not used

---

## ✅ Next Steps

**Awaiting your decision**:

1. **Approve OPTION C (Code Modifications)**?
   - If YES: I will proceed with creating FIPS-compliant crypto utilities and modifying all 7+ files
   - If NO: Provide feedback on which changes to prioritize

2. **Choose Azure deployment option**?
   - Option 1: Full FIPS (~$1,400/month)
   - Option 2: Budget FIPS (~$305/month)
   - Option 3: Code-only (no Azure changes)

3. **Timeline preference**?
   - Aggressive: 3 weeks (all phases parallel)
   - Standard: 5 weeks (sequential phases)
   - Conservative: 8 weeks (extensive testing)

**Please confirm to proceed with OPTION C code modifications.**

---

**End of Executive Summary**
