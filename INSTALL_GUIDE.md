# Wegweiser Installation Guide

**Complete step-by-step guide for installing Wegweiser with enhanced setup experience**

---

## Overview

This guide will help you install Wegweiser using the enhanced installation system, which includes:

- **Pre-flight checking** - Validates all prerequisites before installation
- **Interactive configuration** - Wizard-driven .env setup
- **Progress tracking** - Resume interrupted installations
- **Error recovery** - Automatic rollback on failures
- **Post-install verification** - Functional tests to ensure everything works

**Estimated Installation Time:** 15-30 minutes (depending on system and internet speed)

---

## Prerequisites

Before you begin, ensure you have:

### Required
- **Operating System:** **Ubuntu 20.04 LTS or newer** (recommended)
  - Also supported: Debian 11+, Linux Mint 20+
  - Development only: macOS 11+
  - Not recommended: CentOS, RHEL, WSL (for production)
- **User Privileges:** Root or sudo access
- **PostgreSQL:** 12 or higher (or willing to install)
- **Redis:** 6 or higher (or willing to install)
- **Python:** 3.9 or higher
- **Memory:** Minimum 4GB RAM (8GB+ recommended)
- **Disk Space:** Minimum 20GB available
- **Internet Connection:** For downloading packages

> **Recommended Platform:** Ubuntu 22.04 LTS Server for production deployments

### Optional
- **AI Provider API Key:** OpenAI, Azure OpenAI, Anthropic, or Ollama
- **Email Server:** For notifications and password resets
- **NATS Server:** For agent communication

---

## Quick Start (Recommended)

For the best experience, follow these steps in order:

### 1. Clone the Repository

```bash
git clone https://github.com/creativeheadz/wegweiser-public
cd wegweiser-public
```

### 2. Run Pre-Flight Checks

This validates your system before installation:

```bash
sudo bash check-prereqs.sh
```

**What it checks:**
- Operating system compatibility
- System resources (memory, disk, CPU)
- Required commands and tools
- PostgreSQL and Redis availability
- Network connectivity
- Port availability
- Python dependencies

**If checks fail:** Review the output and install missing prerequisites. Re-run until all checks pass.

### 3. Configure Environment

Run the interactive configuration wizard:

```bash
sudo bash configure-env.sh
```

**The wizard will ask you to:**
- Select deployment mode (Development/Production/Custom)
- Configure database settings
- Set up Redis connection
- Choose secret storage backend
- Select AI provider and enter API keys
- Configure optional services (email, OAuth, payments)
- Set admin user credentials

**Result:** Creates a secure `.env` file with all your settings.

### 4. Run Installation

Execute the enhanced installer:

```bash
sudo bash install-enhanced.sh
```

**What it does:**
1. ✓ Re-runs pre-flight checks
2. ✓ Confirms deployment mode
3. ✓ Validates environment configuration
4. ✓ Creates installation backup
5. ✓ Installs system dependencies
6. ✓ Sets up Python virtual environment
7. ✓ Installs Python packages
8. ✓ Configures PostgreSQL database
9. ✓ Runs database migrations
10. ✓ Sets up Redis
11. ✓ Creates systemd services
12. ✓ Sets file permissions
13. ✓ Performs final verification

**Progress tracking:** Shows real-time progress. If interrupted, you can resume with:

```bash
sudo bash install-enhanced.sh --resume
```

### 5. Verify Installation

Run comprehensive verification tests:

```bash
bash verify-setup-enhanced.sh
```

**What it tests:**
- File structure and permissions
- Configuration validity
- Python environment
- Database connectivity
- Redis connectivity
- Flask application import
- Systemd services
- Network ports

**Success criteria:** 90%+ tests passing with no critical errors.

### 6. Start Services

```bash
# Start all services
sudo systemctl start wegweiser
sudo systemctl start wegweiser-celery
sudo systemctl start wegweiser-celery-beat

# Enable auto-start on boot
sudo systemctl enable wegweiser
sudo systemctl enable wegweiser-celery
sudo systemctl enable wegweiser-celery-beat

# Check status
sudo systemctl status wegweiser
```

### 7. Access Application

Open your browser and navigate to:

```
http://localhost:5000
```

Or if configured with a domain:

```
https://yourdomain.com
```

**Default credentials** (if admin user was created):
- Email: As configured in setup wizard
- Password: As configured in setup wizard

---

## Installation Scenarios

### Scenario 1: Development Environment

**Goal:** Quick setup for testing and development

```bash
# 1. Clone repo
git clone https://github.com/creativeheadz/wegweiser-public
cd wegweiser-public

# 2. Install PostgreSQL and Redis (if not already installed)
sudo apt-get update
sudo apt-get install postgresql redis-server

# 3. Check prerequisites
sudo bash check-prereqs.sh

# 4. Configure (select Development mode)
sudo bash configure-env.sh
# Choose option 1: Development
# Select SQLite for simplest setup

# 5. Install
sudo bash install-enhanced.sh

# 6. Verify
bash verify-setup-enhanced.sh

# 7. Start services
sudo systemctl start wegweiser wegweiser-celery

# Done! Access at http://localhost:5000
```

### Scenario 2: Production Self-Hosted

**Goal:** Secure production deployment with OpenBao

```bash
# 1. Clone repo
git clone https://github.com/creativeheadz/wegweiser-public
cd wegweiser-public

# 2. Ensure services are installed and running
sudo systemctl status postgresql redis-server

# 3. Check prerequisites
sudo bash check-prereqs.sh

# 4. Configure (select Production Self-Hosted)
sudo bash configure-env.sh
# Choose option 2: Production (Self-Hosted)
# Configure OpenBao settings
# Set strong passwords

# 5. Install
sudo bash install-enhanced.sh

# 6. Verify
bash verify-setup-enhanced.sh

# 7. Set up reverse proxy (Nginx/Apache)
# 8. Configure SSL certificates
# 9. Start services
sudo systemctl start wegweiser wegweiser-celery wegweiser-celery-beat

# 10. Enable firewall
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
```

### Scenario 3: Production on Azure

**Goal:** Cloud deployment with Azure services

```bash
# 1. Clone repo on Azure VM
git clone https://github.com/creativeheadz/wegweiser-public
cd wegweiser-public

# 2. Configure (select Production Azure)
sudo bash configure-env.sh
# Choose option 3: Production (Azure)
# Enter Azure Key Vault details
# Configure Azure PostgreSQL connection

# 3. Install
sudo bash install-enhanced.sh

# 4. Configure Azure Managed Identity
# 5. Verify
bash verify-setup-enhanced.sh
```

---

## Post-Installation Tasks

### Secure Your Installation

```bash
# 1. Secure .env file (already done by installer, but verify)
chmod 600 .env
chown www-data:www-data .env

# 2. Set up firewall
sudo ufw enable
sudo ufw allow 5000/tcp  # or your custom port
sudo ufw allow 22/tcp    # SSH

# 3. Configure SSL/TLS (if using HTTPS)
# Install certbot for Let's Encrypt:
sudo apt-get install certbot python3-certbot-nginx
sudo certbot --nginx -d yourdomain.com

# 4. Enable automatic security updates
sudo apt-get install unattended-upgrades
sudo dpkg-reconfigure --priority=low unattended-upgrades
```

### Configure Backups

```bash
# Create backup script
cat > /opt/wegweiser/backup.sh << 'EOF'
#!/bin/bash
BACKUP_DIR="/opt/backups/wegweiser"
DATE=$(date +%Y%m%d_%H%M%S)

mkdir -p "$BACKUP_DIR"

# Backup database
sudo -u postgres pg_dump wegweiser > "$BACKUP_DIR/db_$DATE.sql"

# Backup .env
cp /opt/wegweiser/.env "$BACKUP_DIR/env_$DATE"

# Compress
tar -czf "$BACKUP_DIR/wegweiser_$DATE.tar.gz" "$BACKUP_DIR/db_$DATE.sql" "$BACKUP_DIR/env_$DATE"

# Cleanup old backups (keep last 7 days)
find "$BACKUP_DIR" -name "wegweiser_*.tar.gz" -mtime +7 -delete
EOF

chmod +x /opt/wegweiser/backup.sh

# Add to crontab (daily at 2 AM)
(crontab -l 2>/dev/null; echo "0 2 * * * /opt/wegweiser/backup.sh") | crontab -
```

### Monitor Services

```bash
# View logs
sudo journalctl -u wegweiser -f
sudo journalctl -u wegweiser-celery -f

# Check service status
sudo systemctl status wegweiser wegweiser-celery

# Monitor system resources
htop

# Check database connections
sudo -u postgres psql -c "SELECT count(*) FROM pg_stat_activity;"

# Check Redis memory
redis-cli info memory
```

---

## Troubleshooting

If you encounter issues, follow this diagnostic sequence:

### 1. Run Pre-Flight Checks Again

```bash
sudo bash check-prereqs.sh
```

### 2. Check Installation State

```bash
cat .install-state.json | jq
```

### 3. Run Verification

```bash
bash verify-setup-enhanced.sh
```

### 4. Check Service Logs

```bash
sudo journalctl -u wegweiser -n 100 --no-pager
```

### 5. Consult Troubleshooting Guide

```bash
less TROUBLESHOOTING.md
```

### Common Issues

| Problem | Quick Fix |
|---------|-----------|
| PostgreSQL won't start | `sudo systemctl restart postgresql` |
| Redis connection failed | `sudo systemctl restart redis-server` |
| Permission denied errors | `sudo chown -R www-data:www-data /opt/wegweiser` |
| Can't import Flask app | Check Python packages: `venv/bin/pip list` |
| 502 Bad Gateway | Check if Flask is running: `systemctl status wegweiser` |

**For detailed solutions, see [TROUBLESHOOTING.md](TROUBLESHOOTING.md)**

---

## Upgrading

When new versions are released:

```bash
# 1. Backup current installation
/opt/wegweiser/backup.sh

# 2. Pull latest changes
cd /opt/wegweiser
git pull origin main

# 3. Update dependencies
source venv/bin/activate
pip install -r requirements.txt --upgrade

# 4. Run migrations
export FLASK_APP=wsgi.py
flask db upgrade

# 5. Restart services
sudo systemctl restart wegweiser wegweiser-celery wegweiser-celery-beat

# 6. Verify
bash verify-setup-enhanced.sh
```

---

## Uninstallation

To completely remove Wegweiser:

```bash
# 1. Stop services
sudo systemctl stop wegweiser wegweiser-celery wegweiser-celery-beat
sudo systemctl disable wegweiser wegweiser-celery wegweiser-celery-beat

# 2. Remove systemd services
sudo rm /etc/systemd/system/wegweiser*.service
sudo systemctl daemon-reload

# 3. Remove database (optional)
sudo -u postgres psql -c "DROP DATABASE wegweiser;"
sudo -u postgres psql -c "DROP USER wegweiser;"

# 4. Remove application files
sudo rm -rf /opt/wegweiser

# 5. Remove backups (optional)
sudo rm -rf /opt/backups/wegweiser
```

---

## Getting Help

### Documentation

- [README.md](README.md) - Project overview
- [TROUBLESHOOTING.md](TROUBLESHOOTING.md) - Detailed troubleshooting
- [documentation/](documentation/) - Comprehensive documentation

### Support

- **GitHub Issues:** https://github.com/creativeheadz/wegweiser-public/issues
- **Documentation:** [documentation/INDEX.md](documentation/INDEX.md)

### Diagnostic Report

When reporting issues, include this information:

```bash
# Generate diagnostic report
{
  echo "=== System Info ==="
  uname -a
  echo ""
  echo "=== Pre-flight Results ==="
  sudo bash check-prereqs.sh
  echo ""
  echo "=== Installation State ==="
  cat .install-state.json | jq
  echo ""
  echo "=== Service Logs ==="
  sudo journalctl -u wegweiser -n 50 --no-pager
} > diagnostic-report.txt
```

---

## Advanced Topics

### Custom Installation Directory

```bash
# Edit configure-env.sh and change APP_DIR
# Or set it manually in .env:
APP_DIR=/custom/path/wegweiser

# Then run installation
sudo bash install-enhanced.sh
```

### Multi-Tenancy Setup

See [documentation/architecture-overview.md](documentation/architecture-overview.md) for multi-tenant configuration.

### High Availability Setup

For production high-availability:
- Use external PostgreSQL cluster
- Use Redis Sentinel or Cluster
- Deploy multiple Flask instances behind load balancer
- Use shared storage for static files

### Docker Deployment

For Docker-based deployment, see the Docker documentation (coming soon).

---

## Security Best Practices

1. **Keep secrets secure**
   - Never commit `.env` to version control
   - Use strong, random passwords
   - Rotate secrets regularly

2. **Update regularly**
   - Enable automatic security updates
   - Monitor security advisories
   - Keep dependencies up to date

3. **Limit access**
   - Use firewall rules
   - Configure fail2ban
   - Enable rate limiting

4. **Monitor logs**
   - Review logs regularly
   - Set up alerts for errors
   - Monitor resource usage

5. **Backup everything**
   - Database backups daily
   - Configuration backups
   - Test restore procedures

---

## License

See [LICENSE](LICENSE) file for details.

---

**Enjoy using Wegweiser!** 🚀

For questions or issues, please refer to the troubleshooting guide or open an issue on GitHub.
