# Wegweiser Quick Start Guide

**Get Wegweiser up and running in 15 minutes**

---

## Prerequisites Checklist

Before you begin, ensure you have:

- [ ] **Ubuntu 20.04 LTS or newer** (recommended) or compatible Linux distribution
- [ ] Root/sudo access
- [ ] 4GB+ RAM
- [ ] 20GB+ free disk space
- [ ] Internet connection

> **Note:** Wegweiser is primarily tested on Ubuntu 20.04+ LTS. Other distributions may work but are not officially supported.

---

## Installation in 6 Steps

### Step 1: Clone Repository (1 min)

```bash
git clone https://github.com/creativeheadz/wegweiser-public
cd wegweiser-public
```

### Step 2: Check Prerequisites (2 min)

```bash
sudo bash check-prereqs.sh
```

**What to look for:** Green ✓ marks and "System is ready for installation!"

**If checks fail:** Install missing items (PostgreSQL, Redis, Python 3.9+)

### Step 3: Configure Environment (3 min)

```bash
sudo bash configure-env.sh
```

**What to choose:**
- **Deployment mode:** Development (for testing) or Production
- **Database:** SQLite (easiest) or PostgreSQL
- **AI Provider:** Enter your API key or skip

**Result:** Creates `.env` file with your settings

### Step 4: Install (8 min)

```bash
sudo bash install-enhanced.sh
```

**What happens:**
- Installs system packages
- Sets up Python environment
- Configures database
- Creates services

**Progress shown:** Real-time progress bar

### Step 5: Verify (1 min)

```bash
bash verify-setup-enhanced.sh
```

**What to look for:** 90%+ success rate

### Step 6: Start Services (30 sec)

```bash
sudo systemctl start wegweiser wegweiser-celery
sudo systemctl enable wegweiser wegweiser-celery
```

---

## Access Your Installation

Open browser: **http://localhost:5000**

Or if configured: **https://yourdomain.com**

---

## If Something Goes Wrong

### Installation Failed?

```bash
# Resume from where it left off
sudo bash install-enhanced.sh --resume
```

### Need Help?

```bash
# Check what failed
cat .install-state.json | jq

# See troubleshooting guide
less TROUBLESHOOTING.md

# Or view installation guide
less INSTALL_GUIDE.md
```

---

## Common Issues

| Problem | Solution |
|---------|----------|
| PostgreSQL not found | `sudo apt-get install postgresql` |
| Redis not found | `sudo apt-get install redis-server` |
| Permission denied | Run with `sudo` |
| Can't connect to DB | `sudo systemctl start postgresql` |
| Can't connect to Redis | `sudo systemctl start redis-server` |
| Port 5000 in use | Change `FLASK_PORT` in `.env` |

---

## Next Steps After Installation

1. **Configure your organization**
   - Add devices, groups, organizations

2. **Set up agents**
   - Deploy agents to endpoints for monitoring

3. **Configure AI features**
   - Test chat functionality
   - Review health scores

4. **Set up backups**
   - Database backups
   - Configuration backups

5. **Enable HTTPS** (production)
   - Configure SSL certificates
   - Update domain settings

---

## Useful Commands

```bash
# Check service status
sudo systemctl status wegweiser

# View logs
sudo journalctl -u wegweiser -f

# Restart services
sudo systemctl restart wegweiser wegweiser-celery

# Stop services
sudo systemctl stop wegweiser wegweiser-celery

# Re-run verification
bash verify-setup-enhanced.sh

# Check installation state
cat .install-state.json | jq
```

---

## Documentation

- **Full Installation Guide:** [INSTALL_GUIDE.md](INSTALL_GUIDE.md)
- **Troubleshooting:** [TROUBLESHOOTING.md](TROUBLESHOOTING.md)
- **Installation System Details:** [README_INSTALLATION.md](README_INSTALLATION.md)
- **Project Overview:** [README.md](README.md)

---

## Support

**GitHub Issues:** https://github.com/creativeheadz/wegweiser-public/issues

**When reporting issues, include:**
```bash
# Generate diagnostic report
sudo bash check-prereqs.sh > diagnostics.txt 2>&1
cat .install-state.json >> diagnostics.txt
bash verify-setup-enhanced.sh >> diagnostics.txt 2>&1
```

---

**Installation taking longer than expected?**

That's normal for:
- First-time PostgreSQL setup
- Python package downloads
- Database migrations

Be patient - progress bar shows you what's happening!

---

**Ready to get started?** Jump to Step 1! 🚀
