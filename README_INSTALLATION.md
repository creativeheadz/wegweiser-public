# Wegweiser Enhanced Installation System

**Professional-grade installation experience with progress tracking, error recovery, and comprehensive validation**

---

## What's New?

The Wegweiser installation process has been completely redesigned for a better user experience:

### ✨ Key Features

- **🔍 Pre-Flight Validation** - Check all prerequisites before installation begins
- **🎯 Interactive Configuration** - Wizard-driven .env setup with validation
- **📊 Progress Tracking** - Real-time progress with state management
- **🔄 Resume Capability** - Continue interrupted installations
- **🛡️ Error Recovery** - Automatic rollback on failures
- **✅ Functional Verification** - Actual connectivity tests, not just file checks
- **📚 Comprehensive Docs** - Detailed troubleshooting and guides

---

## Installation Scripts Overview

### Core Scripts

| Script | Purpose | When to Use |
|--------|---------|-------------|
| `check-prereqs.sh` | Validates system prerequisites | **Run first** - before any installation |
| `configure-env.sh` | Interactive .env configuration wizard | After pre-flight checks pass |
| `install-enhanced.sh` | Main installation with progress tracking | After configuration is complete |
| `verify-setup-enhanced.sh` | Comprehensive post-install verification | After installation completes |

### Supporting Files

| File | Purpose |
|------|---------|
| `.install-state.sh` | State tracking library (sourced by installer) |
| `.install-state.json` | Installation progress state (auto-generated) |
| `.install-backup/` | Backup directory (auto-created) |
| `INSTALL_GUIDE.md` | Complete installation guide |
| `TROUBLESHOOTING.md` | Detailed troubleshooting guide |

---

## Quick Start

```bash
# 1. Clone the repository
git clone https://github.com/creativeheadz/wegweiser-public
cd wegweiser-public

# 2. Check prerequisites
sudo bash check-prereqs.sh

# 3. Configure environment
sudo bash configure-env.sh

# 4. Install
sudo bash install-enhanced.sh

# 5. Verify
bash verify-setup-enhanced.sh

# 6. Start services
sudo systemctl start wegweiser wegweiser-celery

# 7. Access application
# http://localhost:5000
```

**Total time:** 15-30 minutes

---

## Script Details

### 1. check-prereqs.sh

**Purpose:** Validates your system before installation

**What it checks:**
- ✓ Operating system and architecture
- ✓ User permissions (root check)
- ✓ System resources (RAM, disk, CPU)
- ✓ Required commands (git, python3, curl, etc.)
- ✓ PostgreSQL installation and status
- ✓ Redis installation and status
- ✓ NATS server (optional)
- ✓ Network connectivity
- ✓ Port availability
- ✓ Python dependencies prerequisites
- ✓ Project file structure
- ✓ Security configuration

**Usage:**
```bash
sudo bash check-prereqs.sh
```

**Output:**
- Detailed check results with colored indicators
- System readiness score (percentage)
- Critical issues that must be fixed
- Warnings and recommendations
- Exit code 0 if ready, non-zero otherwise

**Example output:**
```
╔════════════════════════════════════════════════════════════╗
║        Wegweiser Pre-Flight System Checker                ║
╚════════════════════════════════════════════════════════════╝

System Information
═══════════════════════════════════════════════════════════
[✓] Operating System: Ubuntu 22.04 (Linux)
[✓] Architecture: x86_64 (64-bit)

System Resources
═══════════════════════════════════════════════════════════
[✓] Total Memory: 8192MB (Excellent)
[✓] Available Memory: 4096MB
[✓] Available Disk Space: 51200MB (Excellent)
[✓] CPU Cores: 4 (Excellent)

...

Pre-Flight Check Summary
═══════════════════════════════════════════════════════════
Total Checks Run: 47
Passed: 45
Failed: 0
Warnings: 2

System Readiness: 95%

✓ System is ready for installation!
```

---

### 2. configure-env.sh

**Purpose:** Interactive wizard to generate .env configuration

**Features:**
- Step-by-step guided configuration
- Smart defaults based on deployment mode
- Auto-generation of secure secrets
- Connection testing for database and Redis
- Email validation
- Password security requirements
- Automatic file permissions (600)

**Configuration Steps:**
1. **Deployment Mode** - Development, Production (Self-Hosted/Azure), or Custom
2. **Application Settings** - Directory, user, port
3. **Database** - PostgreSQL or SQLite (dev mode), with connection testing
4. **Redis** - Host, port, password (optional), with connection testing
5. **Secret Storage** - Local, Azure Key Vault, or OpenBao
6. **AI Provider** - OpenAI, Azure OpenAI, Anthropic, or Ollama
7. **Optional Services** - Email, Azure AD OAuth, Stripe
8. **Admin User** - Email and password with validation
9. **Additional Settings** - Domain, HTTPS, logging

**Usage:**
```bash
sudo bash configure-env.sh
```

**Result:**
- Creates `.env` file with all configurations
- Backs up existing `.env` if present
- Sets file permissions to 600
- Displays configuration summary

---

### 3. install-enhanced.sh

**Purpose:** Main installation script with progress tracking and error recovery

**Features:**
- ✅ Progress tracking with state management
- ✅ Resume capability for interrupted installations
- ✅ Automatic backups before changes
- ✅ Step-by-step visual progress
- ✅ Error handling with rollback
- ✅ Service creation and configuration
- ✅ Database setup and migrations
- ✅ Permission management

**Installation Steps:**
1. Pre-flight checks
2. Deployment mode selection
3. Environment configuration validation
4. Backup creation
5. System dependencies installation
6. Python virtual environment setup
7. Python packages installation
8. PostgreSQL database configuration
9. Database migrations
10. Redis configuration
11. Systemd services creation
12. File permissions
13. Final verification

**Usage:**
```bash
# Normal installation
sudo bash install-enhanced.sh

# Resume interrupted installation
sudo bash install-enhanced.sh --resume
```

**Progress Display:**
```
Step 6: Python Dependencies
═══════════════════════════════════════════════════════════
[i] This may take 5-10 minutes...
[✓] Python dependencies installed successfully

Progress: [==========================------] 75%
```

**State Management:**
All progress is saved to `.install-state.json`:
```json
{
  "version": "1.0",
  "started_at": "2024-01-15T10:30:00Z",
  "deployment_mode": "production-self-hosted",
  "steps": {
    "preflight": {
      "status": "completed",
      "started_at": "2024-01-15T10:30:05Z",
      "completed_at": "2024-01-15T10:30:15Z"
    },
    "python_venv": {
      "status": "in_progress",
      "started_at": "2024-01-15T10:35:00Z"
    }
  },
  "status": "in_progress"
}
```

---

### 4. verify-setup-enhanced.sh

**Purpose:** Comprehensive post-installation verification with functional tests

**What it tests:**
- ✓ File structure and presence
- ✓ Configuration file validity
- ✓ Environment variable completeness
- ✓ Python version compatibility
- ✓ Python package installation
- ✓ **Database connectivity** (actual connection test)
- ✓ **Redis connectivity** (actual ping test)
- ✓ **Flask application import** (tests if app can start)
- ✓ Flask CLI functionality
- ✓ Database migrations status
- ✓ Systemd service files
- ✓ Service status (enabled/running)
- ✓ Network ports
- ✓ File permissions and ownership

**Usage:**
```bash
bash verify-setup-enhanced.sh
```

**Output:**
```
╔════════════════════════════════════════════════════════════╗
║        Wegweiser Enhanced Verification Suite              ║
║        Functional Testing & Health Checks                 ║
╚════════════════════════════════════════════════════════════╝

Database Connectivity Tests
═══════════════════════════════════════════════════════════
▶ PostgreSQL Connection
[✓] PostgreSQL connection: successful
[✓] Database tables: 45 tables found

Redis Connectivity Tests
═══════════════════════════════════════════════════════════
▶ Redis Connection
[✓] Redis connection: successful
[✓] Redis memory usage: 2.5M

Flask Application Tests
═══════════════════════════════════════════════════════════
▶ Application Import Test
[✓] Flask application: can be imported

Verification Summary
═══════════════════════════════════════════════════════════
Total Tests: 52
Passed: 50
Failed: 0
Warnings: 2
Success Rate: 96%

Overall Status: Excellent

✓ System verification complete!
```

---

## State Management

The installation system tracks progress in `.install-state.json`, enabling:

### Resume Capability

If installation is interrupted:
```bash
sudo bash install-enhanced.sh --resume
```

The installer will:
1. Load previous state
2. Show completed steps
3. Ask if you want to continue
4. Resume from last incomplete step

### Rollback on Failure

On error:
1. State is saved with failure details
2. Error information logged
3. User notified with recovery options
4. Can resume after fixing issue

### State Commands

```bash
# View current state
cat .install-state.json | jq

# Check installation status
jq '.status' .install-state.json

# See failed steps
jq '.steps[] | select(.status=="failed")' .install-state.json

# View progress percentage
jq -r '
  (.steps | to_entries | map(select(.value.status == "completed")) | length) as $completed |
  (.steps | length) as $total |
  ($completed * 100 / $total | floor)
' .install-state.json
```

---

## Backup System

### Automatic Backups

The installer automatically creates backups before making changes:

```bash
.install-backup/
├── pre-install-20240115_103000/
│   ├── .env
│   └── metadata.json
├── pre-install-20240115_110000/
│   ├── .env
│   └── metadata.json
```

### Backup Management

```bash
# List backups
ls -la .install-backup/

# Restore from backup
cp .install-backup/BACKUP_NAME/.env .env

# Clean old backups (automatic - keeps last 5)
# Manual cleanup if needed:
rm -rf .install-backup/OLD_BACKUP_NAME
```

---

## Comparison: Old vs New Installation

| Feature | Old install.sh | New install-enhanced.sh |
|---------|---------------|-------------------------|
| Pre-flight checks | ❌ No | ✅ Comprehensive |
| Interactive config | ❌ Manual .env edit | ✅ Wizard-driven |
| Progress tracking | ❌ No | ✅ Real-time |
| Resume capability | ❌ No | ✅ Yes |
| Error recovery | ❌ Manual | ✅ Automatic |
| Functional tests | ❌ File checks only | ✅ Connectivity tests |
| State management | ❌ No | ✅ JSON state file |
| Backups | ❌ Manual | ✅ Automatic |
| Troubleshooting | ⚠️ Basic | ✅ Comprehensive guide |
| User experience | ⚠️ Terminal errors | ✅ Colored, formatted output |

---

## Troubleshooting

### Installation Failed

```bash
# 1. Check installation state
cat .install-state.json | jq '.status, .current_step'

# 2. View error details
cat .install-state.json | jq '.steps[] | select(.status=="failed")'

# 3. Check logs
sudo journalctl -xe | tail -50

# 4. Try to resume
sudo bash install-enhanced.sh --resume
```

### Pre-Flight Checks Fail

```bash
# See what failed
sudo bash check-prereqs.sh | grep "✗"

# Install missing prerequisites
# Example: PostgreSQL
sudo apt-get install postgresql postgresql-contrib

# Re-run checks
sudo bash check-prereqs.sh
```

### Configuration Issues

```bash
# Re-run configuration wizard
sudo bash configure-env.sh

# Or manually edit .env
nano .env

# Verify configuration
bash verify-setup-enhanced.sh
```

**For detailed solutions, see [TROUBLESHOOTING.md](TROUBLESHOOTING.md)**

---

## Advanced Usage

### Skip Pre-Flight Checks (Not Recommended)

```bash
# Edit install-enhanced.sh and comment out pre-flight step
# Or manually mark as complete:
# jq '.steps.preflight.status = "completed"' .install-state.json > tmp.json
# mv tmp.json .install-state.json
```

### Custom Installation Directory

```bash
# Set in .env:
APP_DIR=/custom/path

# Then run installer
sudo bash install-enhanced.sh
```

### Development Mode Quick Install

```bash
# Minimal setup for development
sudo bash configure-env.sh  # Choose "Development" + SQLite
sudo bash install-enhanced.sh
# Services optional for development
```

---

## Files Created During Installation

```
wegweiser-public/
├── .env                          # Your configuration (600 perms)
├── .install-state.json          # Installation progress
├── .install-backup/             # Backup directory
│   └── pre-install-*/
├── venv/                        # Python virtual environment
├── migrations/                  # Database migrations
├── wegweiser.db                 # SQLite DB (if using SQLite)
└── /etc/systemd/system/
    ├── wegweiser.service
    ├── wegweiser-celery.service
    └── wegweiser-celery-beat.service
```

---

## Contributing

If you find issues or have suggestions for the installation system:

1. Check [TROUBLESHOOTING.md](TROUBLESHOOTING.md)
2. Open an issue on GitHub
3. Include diagnostic output:
   ```bash
   sudo bash check-prereqs.sh > prereqs-output.txt 2>&1
   cat .install-state.json > install-state.txt
   bash verify-setup-enhanced.sh > verify-output.txt 2>&1
   ```

---

## License

Same as main project - see [LICENSE](LICENSE)

---

**Happy Installing!** 🚀

For complete installation instructions, see [INSTALL_GUIDE.md](INSTALL_GUIDE.md)
