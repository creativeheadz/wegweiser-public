# Wegweiser Portability Improvements

This document summarizes the enhancements made to Wegweiser's portability, installation, and configuration management.

## Overview

Wegweiser is now highly portable and deployable across multiple environments with a flexible setup system that supports:

- **Development**: Local .env file-based configuration
- **Self-Hosted**: OpenBao vault for secrets management
- **Azure Cloud**: Azure Key Vault integration
- **Hybrid**: Custom combinations of the above

## What's New

### 1. Flexible Secret Management (`app/utilities/secret_manager.py`)

**Purpose**: Abstract secret storage layer supporting multiple backends with automatic fallback.

**Features**:
- Multiple backend support:
  - **Azure Key Vault**: For Azure deployments
  - **OpenBao**: For self-hosted/on-prem (Vault API compatible)
  - **Local Environment**: Development fallback
- Automatic fallback chain (try each backend in order)
- Health checks for each backend
- LRU caching to reduce repeated secret lookups
- Graceful error handling

**Usage**:
```python
from app.utilities.secret_manager import get_secret

# Get a single secret
api_key = get_secret('AZURE_OPENAI_API_KEY')

# Get with default value
db_url = get_secret('DATABASE_URL', default='postgresql://localhost/wegweiser')

# Require a secret to exist
secret_key = get_secret('SECRET_KEY', required=True)

# Get multiple secrets
secrets = get_secrets(['DATABASE_URL', 'SECRET_KEY', 'API_KEY'])
```

**Benefits**:
- No code changes needed when switching secret backends
- Consistent error handling across all backends
- Reduced Azure SDK calls through caching
- Easy to add new backends (extend `SecretBackend` class)

### 2. Enhanced Installation Wizard (`install.sh`)

**Purpose**: User-friendly entry point for Wegweiser installation.

**Features**:
- Deployment mode selection (Development, Self-Hosted, Azure, Custom)
- Pre-flight system checks
- Resource validation (memory, disk space)
- Installation confirmation with summary
- Calls the existing `app/setup.sh` with appropriate configuration

**Usage**:
```bash
sudo bash install.sh
```

**Flow**:
1. Display banner and verify root privileges
2. Present deployment mode options
3. Run system requirement checks
4. Show configuration summary
5. Confirm before proceeding
6. Execute detailed setup script

### 3. Enhanced Setup Script (`app/setup.sh`)

**Improvements**:

#### AI Provider Setup
- Interactive selection with explanations
- Provider-specific configuration functions
- Links to obtain API keys
- Support for all major providers:
  - Azure OpenAI (recommended for Azure)
  - OpenAI (standalone)
  - Anthropic Claude
  - Ollama (self-hosted)
  - Option to skip and configure later

#### Secret Storage Setup
- Selection between:
  - Local .env (development)
  - Azure Key Vault (Azure production)
  - OpenBao (self-hosted)
  - Environment variables only
- Backend-specific configuration functions
- Connection testing where applicable

#### Azure Credentials
- Optional Azure AD configuration
- Collects Tenant ID, Client ID, Client Secret, Redirect URI
- Explains intended use cases
- Emphasizes security when storing credentials

### 4. Configuration Validation (`app/utilities/config_validator.py`)

**Purpose**: Validate configuration at startup and provide diagnostic information.

**Features**:
- Database connectivity check
- Redis connectivity check
- Secret storage backend verification
- AI provider configuration validation
- Required directory creation
- Detailed report generation

**Usage**:
```bash
# Run validation directly
python -m app.utilities.config_validator

# Use in application startup
from app.utilities.config_validator import validate_config
if validate_config():
    print("Configuration is valid")
```

### 5. Setup Verification Script (`verify-setup.sh`)

**Purpose**: Quick post-installation verification.

**Checks**:
- Configuration files present
- Required dependencies installed
- Python and virtual environment
- PostgreSQL and Redis availability
- Configuration variables set
- Service readiness

**Usage**:
```bash
bash verify-setup.sh
```

### 6. Configuration Templates

#### `.env.example`
Comprehensive template with all available configuration options organized by category:
- Application configuration
- Database settings
- Redis configuration
- Secret storage options
- AI provider settings
- Azure services
- Email configuration
- Stripe integration
- Logging settings
- IP blocker configuration

#### `config/secrets.openbao.example`
Complete guide for setting up OpenBao secrets:
- Explanation of how to use OpenBao
- Example vault commands
- All required secrets with descriptions
- Docker quick-start
- Production recommendations

### 7. Setup Guide (`SETUP_GUIDE.md`)

Comprehensive installation and configuration documentation including:
- Quick start instructions
- Detailed setup for each deployment scenario
- Configuration option reference
- Post-installation steps
- Troubleshooting guide
- Security best practices
- Upgrade instructions
- Resource links

## Updated Application Initialization

### Changes to `app/__init__.py`

**Before**: Hardcoded Azure Key Vault with limited fallback
```python
credential = ManagedIdentityCredential()
_secret_client = SecretClient(vault_url=key_vault_url, credential=credential)
secret_value = _secret_client.get_secret(secret_name).value
```

**After**: Flexible secret manager with multiple backends
```python
from app.utilities.secret_manager import get_secret_manager

_secret_manager = get_secret_manager()
value = _secret_manager.get_secret(secret_name, default=default, required=required)
```

**Benefits**:
- Removed Azure SDK hard dependency
- Works offline with local config
- Automatic fallback chain
- Better error messages
- Easier to test

## Deployment Workflow

### Development
```bash
sudo bash install.sh
# Select: 1) Development
# Configure: Local .env, PostgreSQL, Redis, OpenAI
# Result: Ready to run with `python wsgi.py`
```

### Self-Hosted
```bash
# 1. Install OpenBao
docker run -d -p 8200:8200 openbao:latest

# 2. Run installation
sudo bash install.sh
# Select: 2) Production (Self-Hosted)
# Configure: OpenBao, External Database, External Redis

# 3. Add secrets to OpenBao
vault kv put secret/wegweiser/databaseurl value="..."
# ... add other secrets
```

### Azure
```bash
# Prerequisites: Azure Key Vault, Database, Redis already created
sudo bash install.sh
# Select: 3) Production (Azure)
# Configure: Azure Key Vault, Azure Database, Azure Cache
# Add secrets via Azure Portal or CLI
```

## File Structure

```
wegweiser/
├── install.sh                          # Main installation wizard (NEW)
├── verify-setup.sh                     # Setup verification (NEW)
├── .env.example                        # Configuration template (ENHANCED)
├── SETUP_GUIDE.md                      # Installation guide (NEW)
├── PORTABILITY_IMPROVEMENTS.md         # This file (NEW)
├── app/
│   ├── __init__.py                     # Updated for flexible secrets
│   ├── setup.sh                        # Enhanced with OpenBao & Azure
│   └── utilities/
│       ├── secret_manager.py           # Secret backend abstraction (NEW)
│       └── config_validator.py         # Configuration validator (NEW)
└── config/
    └── secrets.openbao.example         # OpenBao setup guide (NEW)
```

## Key Improvements Summary

| Component | Before | After |
|-----------|--------|-------|
| **Secret Storage** | Azure Key Vault only | Azure KV, OpenBao, Local .env, Env vars |
| **Installation** | Script-based, minimal guidance | Interactive wizard with validation |
| **Configuration** | Manual .env editing | Guided setup with defaults |
| **AI Provider** | Limited setup, no explanations | Full guide, all providers supported |
| **Verification** | None | Built-in validation & verification script |
| **Documentation** | Minimal | Comprehensive setup guide |
| **Error Handling** | Hard failures | Graceful degradation with warnings |

## Security Considerations

### Secrets Protection
1. `.env` files not committed to version control (added to `.gitignore`)
2. `chmod 600 .env` recommended for production
3. Secret rotation supported by all backends
4. No plain-text secrets in logs

### Backend Security
- **Local**: Requires file system security
- **Azure KV**: Enterprise-grade with managed access
- **OpenBao**: Self-hosted with audit logging

### Installation Security
- Root privilege requirement enforced
- Pre-flight checks prevent common misconfigurations
- Validation before service start
- Detailed logging for troubleshooting

## Migration Guide

### From Existing Setup

If you have an existing Wegweiser installation using Azure Key Vault:

1. **No Changes Required**: It will continue to work
2. **Optional Migration**:
   ```bash
   # Backup current .env
   cp .env .env.backup

   # Run new setup to generate fresh config
   sudo bash install.sh
   # Select: 3) Production (Azure)
   # Use your existing Azure credentials
   ```

## Performance Impact

- **Caching**: Secret lookups cached to reduce backend calls
- **Fallback**: Automatic fallback means no extra latency
- **Health Checks**: Optional, can be disabled for high-throughput scenarios

## Testing

### Validate Your Setup
```bash
bash verify-setup.sh
```

### Test Secret Manager
```python
from app.utilities.secret_manager import get_secret_manager

manager = get_secret_manager()
health = manager.health_check()
print(manager.get_available_backends())
```

### Test Database Connection
```bash
source venv/bin/activate
export FLASK_APP=wsgi.py
flask db current
```

## Future Enhancements

Potential additions:
- Docker containers for development/production
- Kubernetes manifests for cloud deployment
- Automated backup/restore procedures
- Secret rotation automation
- Multi-tenant support improvements
- Automated Health monitoring

## Questions & Support

- **Documentation**: See `SETUP_GUIDE.md` for detailed instructions
- **Configuration**: See `.env.example` for all available options
- **Troubleshooting**: See `SETUP_GUIDE.md` troubleshooting section
- **OpenBao Setup**: See `config/secrets.openbao.example` for vault configuration

## Summary

Wegweiser is now significantly more portable and flexible:
✅ Works in development with minimal config
✅ Supports enterprise secret management (Azure KV, OpenBao)
✅ Interactive installation with guidance
✅ Configuration validation and verification
✅ Clear documentation for all deployment scenarios
✅ Graceful fallback for missing components
✅ Security best practices built-in

Installation is now accessible to operators at all skill levels while maintaining flexibility for advanced deployments.
