# Wegweiser Installation Troubleshooting Guide

## Quick Diagnostics

If you encounter issues during installation, run these commands in order:

```bash
# 1. Check system prerequisites
sudo bash check-prereqs.sh

# 2. Check installation state
cat .install-state.json | jq '.status, .steps'

# 3. Verify configuration
bash verify-setup.sh

# 4. Check service logs
sudo journalctl -u wegweiser -n 50
sudo journalctl -u wegweiser-celery -n 50
```

## Common Issues and Solutions

### Pre-Installation Issues

#### Issue: "PostgreSQL not found"
**Symptoms:**
- check-prereqs.sh reports PostgreSQL not installed
- `psql: command not found`

**Solution:**
```bash
# Ubuntu/Debian
sudo apt-get update
sudo apt-get install postgresql postgresql-contrib

# Start PostgreSQL
sudo systemctl start postgresql
sudo systemctl enable postgresql

# Verify
sudo systemctl status postgresql
```

#### Issue: "Redis not found"
**Symptoms:**
- check-prereqs.sh reports Redis not installed
- `redis-cli: command not found`

**Solution:**
```bash
# Ubuntu/Debian
sudo apt-get update
sudo apt-get install redis-server

# Start Redis
sudo systemctl start redis-server
sudo systemctl enable redis-server

# Verify
redis-cli ping
# Should return: PONG
```

#### Issue: "Insufficient disk space"
**Symptoms:**
- Pre-flight check shows low disk space
- Installation fails during package installation

**Solution:**
```bash
# Check disk usage
df -h

# Clean package cache
sudo apt-get clean
sudo apt-get autoclean

# Remove old logs
sudo journalctl --vacuum-time=7d

# Find large files
sudo du -h / | sort -rh | head -20
```

#### Issue: "Python version too old"
**Symptoms:**
- check-prereqs.sh reports Python < 3.9
- Installation fails with Python compatibility errors

**Solution:**
```bash
# Ubuntu 20.04+
sudo apt-get update
sudo apt-get install python3.10 python3.10-venv python3.10-dev

# Update alternatives
sudo update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.10 1

# Verify
python3 --version
```

---

### Configuration Issues

#### Issue: ".env configuration errors"
**Symptoms:**
- Application fails to start
- Error about missing environment variables

**Solution:**
```bash
# Run configuration wizard again
sudo bash configure-env.sh

# Or manually edit
nano .env

# Check for required variables
grep -E "^(DATABASE_URL|SECRET_KEY|API_KEY|REDIS_HOST)" .env

# Ensure proper permissions
chmod 600 .env
```

#### Issue: "Database connection failed"
**Symptoms:**
- Cannot connect to PostgreSQL
- Error: "FATAL: password authentication failed"

**Solution:**
```bash
# Check if PostgreSQL is running
sudo systemctl status postgresql

# Test connection manually
psql -U wegweiser -d wegweiser -h localhost
# Enter password when prompted

# If user doesn't exist, create it
sudo -u postgres psql
CREATE USER wegweiser WITH ENCRYPTED PASSWORD 'your_password';
CREATE DATABASE wegweiser;
GRANT ALL PRIVILEGES ON DATABASE wegweiser TO wegweiser;
\q

# Update .env with correct credentials
nano .env
```

#### Issue: "Redis connection failed"
**Symptoms:**
- Error: "Error connecting to Redis"
- Application cannot start Celery workers

**Solution:**
```bash
# Check if Redis is running
sudo systemctl status redis-server

# Test connection
redis-cli ping

# Check Redis configuration
sudo nano /etc/redis/redis.conf
# Ensure: bind 127.0.0.1 ::1
# Restart Redis
sudo systemctl restart redis-server

# Update .env if needed
nano .env
```

#### Issue: "Secret keys not secure"
**Symptoms:**
- Warning about weak SECRET_KEY
- Default values still in .env

**Solution:**
```bash
# Generate new secure keys
openssl rand -base64 64  # For SECRET_KEY
openssl rand -base64 32  # For API_KEY

# Update .env
nano .env
# Replace SECRET_KEY and API_KEY values

# Ensure file is secure
chmod 600 .env
```

---

### Installation Issues

#### Issue: "Installation failed midway"
**Symptoms:**
- Installation script exits with error
- .install-state.json shows "failed" status

**Solution:**
```bash
# Check installation state
cat .install-state.json | jq

# Review error details
cat .install-state.json | jq '.steps[] | select(.status=="failed")'

# Resume installation
sudo bash install-enhanced.sh --resume

# If resume doesn't work, check specific failed step logs
journalctl -xe
```

#### Issue: "Python dependencies installation failed"
**Symptoms:**
- pip install -r requirements.txt fails
- Error about missing development headers

**Solution:**
```bash
# Install development packages
sudo apt-get install -y \
    build-essential \
    python3-dev \
    libpq-dev \
    libssl-dev \
    libffi-dev \
    libxml2-dev \
    libxslt1-dev \
    libjpeg-dev \
    zlib1g-dev

# Try again
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

#### Issue: "Database migration failed"
**Symptoms:**
- `flask db upgrade` fails
- Error about missing tables or columns

**Solution:**
```bash
# Check database connectivity
psql -U wegweiser -d wegweiser -h localhost -c "SELECT version();"

# Reset migrations (CAUTION: This will drop all data)
rm -rf migrations/
export FLASK_APP=wsgi.py
flask db init
flask db migrate -m "Initial migration"
flask db upgrade

# Create roles
flask create_roles
flask populate_servercore
```

#### Issue: "Permission denied errors"
**Symptoms:**
- Error: "Permission denied" when accessing files
- Services fail to start

**Solution:**
```bash
# Set correct ownership
sudo chown -R www-data:www-data /opt/wegweiser

# Set correct permissions
chmod 600 .env
chmod 755 venv/bin/*
chmod -R 755 app/

# For systemd services
sudo chmod 644 /etc/systemd/system/wegweiser*.service
sudo systemctl daemon-reload
```

---

### Runtime Issues

#### Issue: "Service won't start"
**Symptoms:**
- `systemctl start wegweiser` fails
- Service status shows "failed"

**Solution:**
```bash
# Check service status
sudo systemctl status wegweiser

# View logs
sudo journalctl -u wegweiser -n 100 --no-pager

# Common fixes:
# 1. Check .env file exists and is readable
ls -la .env

# 2. Check virtual environment exists
ls -la venv/

# 3. Test manually
cd /opt/wegweiser
source venv/bin/activate
export FLASK_APP=wsgi.py
flask run
# If this works, issue is with systemd config

# 4. Check gunicorn config
cat gunicorn.conf.py

# 5. Restart services
sudo systemctl restart wegweiser
```

#### Issue: "Celery workers not starting"
**Symptoms:**
- wegweiser-celery service fails
- Background tasks not running

**Solution:**
```bash
# Check Celery service status
sudo systemctl status wegweiser-celery

# View logs
sudo journalctl -u wegweiser-celery -n 100

# Test Celery manually
cd /opt/wegweiser
source venv/bin/activate
celery -A app.celery worker --loglevel=info
# Ctrl+C to stop

# Check Redis connection
redis-cli ping

# Verify Celery configuration
python3 -c "from app import create_app; app = create_app(); print(app.config['CELERY_BROKER_URL'])"

# Restart service
sudo systemctl restart wegweiser-celery
```

#### Issue: "Application runs but can't connect to database"
**Symptoms:**
- Application starts but shows database errors
- Error: "OperationalError: could not connect to server"

**Solution:**
```bash
# Check DATABASE_URL in .env
grep DATABASE_URL .env

# Test connection with psql
psql "$(grep DATABASE_URL .env | cut -d= -f2)"

# Check PostgreSQL is running
sudo systemctl status postgresql

# Check PostgreSQL logs
sudo tail -f /var/log/postgresql/postgresql-*.log

# Verify database exists
sudo -u postgres psql -l | grep wegweiser
```

#### Issue: "502 Bad Gateway" error
**Symptoms:**
- Nginx shows 502 error
- Application not responding

**Solution:**
```bash
# Check if Flask is running
sudo systemctl status wegweiser

# Check if Flask is listening on correct port
sudo netstat -tlnp | grep 5000

# Check Nginx configuration
sudo nginx -t

# View Nginx error logs
sudo tail -f /var/log/nginx/error.log

# Restart services
sudo systemctl restart wegweiser
sudo systemctl restart nginx
```

---

### Performance Issues

#### Issue: "Application is slow"
**Symptoms:**
- Pages take long to load
- Timeouts on requests

**Solution:**
```bash
# Check system resources
htop  # or top

# Check database connections
sudo -u postgres psql -c "SELECT count(*) FROM pg_stat_activity;"

# Check Redis memory usage
redis-cli info memory

# Check Celery workers
celery -A app.celery inspect active

# Optimize PostgreSQL
sudo -u postgres psql wegweiser
VACUUM ANALYZE;
\q

# Increase gunicorn workers (edit gunicorn.conf.py)
nano gunicorn.conf.py
# workers = (2 * CPU_cores) + 1
```

#### Issue: "High memory usage"
**Symptoms:**
- System running out of memory
- Services being killed

**Solution:**
```bash
# Check memory usage
free -h

# Find memory-hungry processes
ps aux --sort=-%mem | head -20

# Reduce Celery workers
# Edit: /etc/systemd/system/wegweiser-celery.service
# Add: --concurrency=2

# Configure Redis max memory
sudo nano /etc/redis/redis.conf
# Add: maxmemory 256mb
# Add: maxmemory-policy allkeys-lru

sudo systemctl restart redis-server
```

---

### AI Provider Issues

#### Issue: "AI features not working"
**Symptoms:**
- Chat doesn't respond
- Error about API keys

**Solution:**
```bash
# Check AI provider configuration
grep -E "^(AI_PROVIDER|OPENAI_API_KEY|AZURE_OPENAI)" .env

# Test API key manually (OpenAI example)
curl https://api.openai.com/v1/models \
  -H "Authorization: Bearer YOUR_API_KEY"

# Update .env with valid keys
nano .env

# Restart application
sudo systemctl restart wegweiser
```

---

### Network Issues

#### Issue: "Cannot reach application from other machines"
**Symptoms:**
- Can access locally but not remotely
- Connection timeout from other IPs

**Solution:**
```bash
# Check if Flask is listening on all interfaces
sudo netstat -tlnp | grep 5000

# Update gunicorn to bind to 0.0.0.0
nano gunicorn.conf.py
# bind = "0.0.0.0:5000"

# Check firewall
sudo ufw status
sudo ufw allow 5000/tcp

# Restart application
sudo systemctl restart wegweiser
```

---

## Recovery Procedures

### Complete Reinstallation

If all else fails:

```bash
# 1. Backup data
sudo -u postgres pg_dump wegweiser > wegweiser_backup.sql
cp .env .env.backup

# 2. Stop services
sudo systemctl stop wegweiser wegweiser-celery wegweiser-celery-beat

# 3. Clean installation
rm -rf venv/
rm .install-state.json

# 4. Reinstall
sudo bash install-enhanced.sh

# 5. Restore data if needed
sudo -u postgres psql wegweiser < wegweiser_backup.sql
```

### Rollback to Backup

```bash
# List available backups
ls -la .install-backup/

# Restore from backup
# (Manual restore - copy files from backup directory)
cp .install-backup/BACKUP_NAME/.env .env

# Restart services
sudo systemctl restart wegweiser
```

---

## Getting Help

If you still have issues:

1. **Collect diagnostic information:**
   ```bash
   # Create diagnostic report
   bash check-prereqs.sh > diagnostics.txt 2>&1
   cat .install-state.json >> diagnostics.txt
   sudo journalctl -u wegweiser -n 200 >> diagnostics.txt
   ```

2. **Check documentation:**
   - README.md
   - documentation/installation-setup.md
   - documentation/getting-started.md

3. **GitHub Issues:**
   - https://github.com/creativeheadz/wegweiser-public/issues

4. **Include in bug reports:**
   - Output of `check-prereqs.sh`
   - Content of `.install-state.json`
   - Relevant log excerpts
   - Steps to reproduce the issue
