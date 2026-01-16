# Wegweiser Installation Checklist

**Print this checklist and check off items as you complete them**

---

## Pre-Installation

### System Requirements
- [ ] Linux (Ubuntu 20.04+/CentOS 8+) or macOS
- [ ] Root or sudo access available
- [ ] 4GB+ RAM available
- [ ] 20GB+ disk space free
- [ ] Internet connection active

### Software Requirements
- [ ] Git installed
- [ ] Python 3.9 or higher installed
- [ ] PostgreSQL 12+ installed (or ready to install)
- [ ] Redis 6+ installed (or ready to install)

### Preparation
- [ ] API keys ready (OpenAI/Azure/Anthropic) - optional
- [ ] Database password chosen
- [ ] Admin email and password chosen
- [ ] Domain name ready (if using) - optional
- [ ] SSL certificates ready (if using HTTPS) - optional

---

## Installation Process

### Step 1: Clone Repository
- [ ] Cloned repository: `git clone https://github.com/creativeheadz/wegweiser-public`
- [ ] Changed to directory: `cd wegweiser-public`

### Step 2: Pre-Flight Checks
- [ ] Ran: `sudo bash check-prereqs.sh`
- [ ] All critical checks passed (green ✓)
- [ ] System readiness: ___% (should be 80%+)
- [ ] Fixed any critical errors
- [ ] Reviewed warnings (if any)

### Step 3: Configuration
- [ ] Ran: `sudo bash configure-env.sh`
- [ ] Selected deployment mode: ____________
- [ ] Configured database settings
- [ ] Database connection test: PASSED / FAILED
- [ ] Configured Redis settings
- [ ] Redis connection test: PASSED / FAILED
- [ ] Selected AI provider: ____________
- [ ] Configured email (if needed)
- [ ] Set admin credentials
- [ ] .env file created successfully

### Step 4: Installation
- [ ] Ran: `sudo bash install-enhanced.sh`
- [ ] Pre-flight checks passed
- [ ] System dependencies installed
- [ ] Python venv created
- [ ] Python packages installed
- [ ] Database created/configured
- [ ] Database migrations completed
- [ ] Redis configured
- [ ] Systemd services created
- [ ] Permissions set
- [ ] Installation completed successfully
- [ ] Installation time: ___ minutes

### Step 5: Verification
- [ ] Ran: `bash verify-setup-enhanced.sh`
- [ ] File structure checks: PASSED
- [ ] Configuration checks: PASSED
- [ ] Python environment: PASSED
- [ ] Database connectivity: PASSED
- [ ] Redis connectivity: PASSED
- [ ] Flask application: PASSED
- [ ] Systemd services: PASSED
- [ ] Overall success rate: ___%  (should be 90%+)

### Step 6: Start Services
- [ ] Started wegweiser: `sudo systemctl start wegweiser`
- [ ] Started celery: `sudo systemctl start wegweiser-celery`
- [ ] Started celery-beat: `sudo systemctl start wegweiser-celery-beat` (optional)
- [ ] Enabled wegweiser: `sudo systemctl enable wegweiser`
- [ ] Enabled celery: `sudo systemctl enable wegweiser-celery`
- [ ] Verified services running: `sudo systemctl status wegweiser`

---

## Post-Installation

### Initial Access
- [ ] Opened browser to: http://localhost:5000
- [ ] Successfully accessed login page
- [ ] Logged in with admin credentials
- [ ] Dashboard loaded successfully

### Configuration
- [ ] Reviewed application settings
- [ ] Updated profile information
- [ ] Tested AI chat functionality
- [ ] Created test organization (optional)
- [ ] Added test device (optional)

### Security
- [ ] .env file permissions: 600 ✓
- [ ] Strong SECRET_KEY set (64 chars)
- [ ] Strong API_KEY set (32 chars)
- [ ] Admin password is strong
- [ ] Firewall configured (if needed)
- [ ] SSL/TLS configured (if needed)

### Backups
- [ ] Backup script created
- [ ] Test backup performed
- [ ] Backup location: _______________
- [ ] Automated backup scheduled (cron)

### Monitoring
- [ ] Service logs checked: `sudo journalctl -u wegweiser -f`
- [ ] No errors in logs
- [ ] Celery workers running
- [ ] Database connections normal
- [ ] Redis memory usage normal

---

## Optional Components

### NATS (for agents)
- [ ] NATS server installed
- [ ] NATS running
- [ ] Agent communication tested

### Reverse Proxy (Nginx/Apache)
- [ ] Nginx/Apache installed
- [ ] Reverse proxy configured
- [ ] HTTPS working (if configured)

### Email
- [ ] SMTP settings configured
- [ ] Test email sent successfully

### Azure Integration
- [ ] Azure Key Vault configured
- [ ] Azure AD OAuth configured
- [ ] Azure PostgreSQL connected

---

## Documentation Review

- [ ] Read QUICK_START.md
- [ ] Read INSTALL_GUIDE.md
- [ ] Bookmarked TROUBLESHOOTING.md
- [ ] Reviewed README_INSTALLATION.md
- [ ] Know where to find documentation/

---

## Troubleshooting (if needed)

### Issues Encountered
- [ ] Issue 1: _______________________
      Solution: _______________________
- [ ] Issue 2: _______________________
      Solution: _______________________
- [ ] Issue 3: _______________________
      Solution: _______________________

### Support Resources Used
- [ ] TROUBLESHOOTING.md
- [ ] Installation state: `.install-state.json`
- [ ] GitHub issues
- [ ] Other: _______________

---

## Sign-Off

**Installation completed by:** _______________________

**Date:** _______________________

**Installation time:** ___ hours ___ minutes

**Overall experience:** Excellent / Good / Fair / Poor

**Notes:**
```
_________________________________________________________________

_________________________________________________________________

_________________________________________________________________

_________________________________________________________________
```

---

## Next Steps

- [ ] Deploy agents to endpoints
- [ ] Configure organizations and groups
- [ ] Set up regular backups
- [ ] Configure monitoring/alerting
- [ ] Plan for scaling (if needed)
- [ ] Review security hardening
- [ ] Document your specific configuration

---

**Congratulations on successfully installing Wegweiser!** 🎉

Keep this checklist for future reference or when installing on additional servers.
