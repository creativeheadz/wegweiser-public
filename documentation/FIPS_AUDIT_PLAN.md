# FIPS 140-2/140-3 Compliance Audit Plan for Wegweiser

## Overview
Comprehensive evaluation of Wegweiser codebase for FIPS 140-2/140-3 compliance readiness. This plan covers both quick scans (Option A) and deeper deployment profiles (Option B), followed by code modifications (Option C).

## OPTION A: Quick Scan & Proposed Edits (8 Major Areas)

### A1: Bcrypt Usage Audit
- Identify all flask_bcrypt imports and usage
- Document password hashing locations (registration, login, profile, admin)
- Document password verification locations
- Understand bcrypt hash format for migration strategy

### A2: Non-Approved Algorithms Audit
- Search for Ed25519, X25519, ChaCha20-Poly1305 usage
- Identify MD5, SHA-1 usage (crypto vs non-crypto)
- Verify all RSA signatures use PKCS1v15 with SHA-256
- Check for custom encryption implementations

### A3: Deprecated Datetime Functions
- Find all datetime.utcnow() calls
- Find all datetime.utcfromtimestamp() calls
- Plan migration to datetime.now(datetime.UTC)

### A4: RSA Key Generation
- Identify all RSA key generation code
- Document current key sizes (1024-bit vs 2048-bit)
- Propose migration to 2048-bit minimum

### A5: Session/CSRF Token Generation
- Verify Flask-Session signing algorithm (SHA-256 vs SHA-1)
- Check Flask-WTF CSRF token generation
- Verify itsdangerous configuration

### A6: JWT/Token Implementations
- Search for PyJWT usage and algorithm configuration
- Search for Authlib OAuth token generation
- Verify only FIPS-approved algorithms (RS256, PS256, ES256)

### A7: TOTP/2FA Implementations
- Check pyotp library configuration
- Verify HMAC algorithm support (SHA-256 vs SHA-1)

### A8: Generate Option A Report
- Comprehensive report with precise code locations
- Proposed edits for each finding
- Configuration instructions

## OPTION B: Deeper FIPS Deployment Profile (10 Major Areas)

### B1: Application Layer (Flask/Python)
- Document all cryptographic dependencies
- Verify cryptography library FIPS OpenSSL linking
- Identify Python version requirements
- Create FIPS-compatible requirements.txt

### B2: Agent Layer (Windows/Linux/macOS)
- Audit Windows, Linux, macOS agent crypto
- Verify 2048-bit RSA key generation
- Document agent FIPS deployment

### B3: NATS Integration
- Verify NATS TLS configuration
- Check NATS authentication (JWT, NKey, credentials)
- Verify NATS client FIPS support
- Document NATS server FIPS configuration

### B4: Database Layer (PostgreSQL)
- Verify PostgreSQL TLS configuration
- Check password hashing in database
- Document PostgreSQL FIPS mode setup

### B5: Cache/Session Layer (Redis)
- Verify Redis TLS configuration
- Check Redis authentication
- Document Redis FIPS mode setup

### B6: Task Queue (Celery)
- Verify Celery broker TLS (Redis)
- Check Celery task signing algorithm
- Document Celery FIPS configuration

### B7: Web Server (Gunicorn)
- Review gunicorn.conf.py TLS settings
- Verify FIPS-approved cipher suites
- Check certificate and key management

### B8: Azure Integration
- Document Azure Key Vault FIPS 140-2 Level 3 validation
- Verify Azure Front Door TLS configuration
- Verify Azure Application Gateway TLS configuration
- Document managed identity authentication

### B9: Operating System Layer
- Document Ubuntu Pro FIPS setup and validation
- Document RHEL FIPS mode setup and validation
- Document Windows Server FIPS policy setup
- Verify OpenSSL FIPS provider version and CMVP certificate

### B10: Create FIPS Deployment Profile Document
- Server deployment profile (OS, OpenSSL, Python, packages)
- Agent deployment profile (Windows/Linux/macOS)
- NATS deployment profile
- Database deployment profile
- Cache/Session deployment profile
- Web server deployment profile
- Azure services deployment profile
- Validation checklist with CMVP certificate references

## OPTION C: Code Modifications (After Approval)

### C1: Replace bcrypt with PBKDF2-HMAC-SHA256 (9 subtasks)
### C2: Fix deprecated datetime functions (10 subtasks)
### C3: Fix RSA key generation to 2048-bit (5 subtasks)
### C4: Verify session signing uses SHA-256 (3 subtasks)
### C5: Verify JWT algorithms (3 subtasks)
### C6: Verify TOTP/2FA configuration (2 subtasks)
### C7: Update dependencies (4 subtasks)
### C8: Create/update tests (6 subtasks)
### C9: Documentation updates (4 subtasks)

## Total Scope
- **139 subtasks** organized in hierarchical structure
- **3 major phases**: Quick Scan (A), Deployment Profile (B), Code Modifications (C)
- **Coverage**: Application, agents, NATS, database, cache, web server, Azure, OS layer

## Status
Awaiting user approval to proceed with execution.

