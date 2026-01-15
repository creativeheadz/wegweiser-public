# Installation & Setup

Complete guide for installing and configuring Wegweiser.

## Prerequisites

### System Requirements
- **OS** - Linux (Ubuntu 20.04+, CentOS 8+) or macOS
- **Python** - 3.9 or higher
- **PostgreSQL** - 12 or higher
- **Redis** - 6 or higher
- **RAM** - Minimum 4GB (8GB+ recommended)
- **Disk** - Minimum 20GB (depends on data volume)

### Required Services
- PostgreSQL database server
- Redis cache server
- NATS messaging server (for agent communication)

## Installation Steps

### 1. Clone Repository
```bash
git clone https://github.com/creativeheadz/wegweiser.git
cd wegweiser
```

### 2. Create Virtual Environment
```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 3. Install Dependencies
```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### 4. Configure Environment

Create `.env` file in project root:
```bash
cp .env.example .env
```

Edit `.env` with your configuration:
```
# Flask
FLASK_ENV=production
FLASK_APP=wsgi.py
SECRET_KEY=your-secret-key-here

# Database
DATABASE_URL=postgresql://user:password@localhost:5432/wegweiser_db

# Redis
REDIS_URL=redis://localhost:6379/0

# Azure Key Vault
AZURE_KEYVAULT_URL=https://your-keyvault.vault.azure.net/
AZURE_TENANT_ID=your-tenant-id
AZURE_CLIENT_ID=your-client-id
AZURE_CLIENT_SECRET=your-client-secret

# NATS
NATS_URL=nats://localhost:4222

# AI Providers (configure at least one)
OPENAI_API_KEY=your-key
AZURE_OPENAI_API_KEY=your-key
ANTHROPIC_API_KEY=your-key

# Email
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your-email
SMTP_PASSWORD=your-password
```

### 5. Initialize Database

```bash
# Create database
createdb wegweiser_db

# Run migrations
export FLASK_APP=wsgi.py
flask db upgrade

# Create roles
flask create_roles

# Populate server core data (optional)
flask populate_servercore
```

### 6. Start Services

**Development:**
```bash
# Terminal 1: Flask app
python wsgi.py

# Terminal 2: Celery worker
celery -A app.celery worker --loglevel=info

# Terminal 3: Celery beat
celery -A app.celery beat --loglevel=info
```

**Production:**
```bash
# Using Gunicorn
gunicorn --config gunicorn.conf.py wsgi:app

# Celery worker (systemd service)
systemctl start wegweiser-celery-worker

# Celery beat (systemd service)
systemctl start wegweiser-celery-beat
```

## Configuration

### Database Configuration
- Connection pooling: Configured in `app/__init__.py`
- Migrations: Managed by Flask-Migrate
- Backups: Use `pg_dump` for PostgreSQL

### Redis Configuration
- Session storage: Configured in `app/__init__.py`
- Cache backend: Redis with fallback to filesystem
- Persistence: Configure in Redis config file

### NATS Configuration
- Server: Configure URL in `.env`
- Authentication: Tenant-specific credentials
- Subjects: Tenant-based subject hierarchy

### Azure Key Vault
- Create Key Vault in Azure
- Add secrets for all sensitive configuration
- Configure service principal credentials

## Deployment

### Docker Deployment
```bash
# Build image
docker build -t wegweiser:latest .

# Run container
docker run -d \
  -e DATABASE_URL=postgresql://... \
  -e REDIS_URL=redis://... \
  -p 5000:5000 \
  wegweiser:latest
```

### Systemd Services
Create `/etc/systemd/system/wegweiser.service`:
```ini
[Unit]
Description=Wegweiser Flask Application
After=network.target

[Service]
Type=notify
User=wegweiser
WorkingDirectory=/opt/wegweiser
ExecStart=/opt/wegweiser/venv/bin/gunicorn \
  --config gunicorn.conf.py wsgi:app
Restart=always

[Install]
WantedBy=multi-user.target
```

### Nginx Configuration
```nginx
upstream wegweiser {
    server 127.0.0.1:8000;
}

server {
    listen 80;
    server_name app.wegweiser.tech;
    
    location / {
        proxy_pass http://wegweiser;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

## Verification

### Check Installation
```bash
# Test Flask app
python wsgi.py

# Test database connection
flask shell
>>> from app import db
>>> db.session.execute('SELECT 1')

# Test Redis connection
redis-cli ping

# Test NATS connection
nats-sub -s nats://localhost:4222 ">"
```

### Run Tests
```bash
pytest
pytest --cov=app tests/
```

## Troubleshooting

### Database Connection Issues
```bash
# Check PostgreSQL
psql -U postgres -h localhost

# Check credentials in .env
grep DATABASE_URL .env

# Check logs
tail -f /opt/wegweiser/wlog/wegweiser.log
```

### Redis Connection Issues
```bash
# Check Redis
redis-cli ping

# Check Redis URL in .env
grep REDIS_URL .env
```

### NATS Connection Issues
```bash
# Check NATS server
nats-sub -s nats://localhost:4222 ">"

# Check NATS URL in .env
grep NATS_URL .env
```

## Next Steps

1. Review [Getting Started](./getting-started.md)
2. Configure [Security](./security-overview.md)
3. Deploy [Agents](./agent-development.md)
4. Review [Architecture](./architecture-overview.md)

---

**Need help?** Check [Troubleshooting](./getting-started.md#troubleshooting) section.

