# Wegweiser Setup & Installation Guide

This guide covers the installation and configuration of Wegweiser across different deployment scenarios.

## Quick Start

For the fastest setup experience, run the interactive installation wizard:

```bash
sudo bash install.sh
```

This will guide you through:
- Deployment mode selection (Development, Self-Hosted, Azure, or Custom)
- System dependency installation
- Database and Redis configuration
- AI provider setup
- Secret storage backend selection
- Service configuration

## Installation Methods

### 1. Interactive Installation (Recommended)

```bash
sudo bash install.sh
```

The wizard will:
- Auto-detect your system
- Install required dependencies
- Configure PostgreSQL and Redis
- Set up Python virtual environment
- Deploy systemd services
- Configure based on your chosen deployment mode

### 2. Manual Installation

If you prefer more control or need to customize the installation:

```bash
sudo bash app/setup.sh
```

The setup script offers:
- Individual component configuration
- Advanced options for each service
- Support for existing databases

### 3. Docker Installation (Coming Soon)

```bash
docker run -e DEPLOYMENT_MODE=development wegweiser:latest
```

## Deployment Scenarios

### Development Setup

**Best for:** Testing, local development, small deployments

**Configuration:**
- Secret Storage: Local `.env` file
- Database: PostgreSQL (local or remote)
- Redis: Local instance
- AI Provider: Your choice (OpenAI, Azure, Anthropic, Ollama)

**Quick Setup:**
```bash
sudo bash install.sh
# Choose option 1 when prompted
```

**Minimal .env:**
```env
DATABASE_URL=postgresql://user:password@localhost/wegweiser
REDIS_HOST=localhost
REDIS_PORT=6379
SECRET_STORAGE=local
AI_PROVIDER=openai
OPENAI_API_KEY=sk_your_key
```

### Production (Self-Hosted/On-Premises)

**Best for:** Maximum control, private cloud, on-premises deployments

**Configuration:**
- Secret Storage: OpenBao (compatible with HashiCorp Vault)
- Database: External PostgreSQL
- Redis: External Redis cluster
- AI Provider: Your choice

**Key Benefits:**
- No dependency on cloud providers
- Full control over secrets and data
- Self-healing capabilities
- Audit logging

**Setup Instructions:**

1. **Install OpenBao** (if not already running):
   ```bash
   # Docker
   docker run -d -p 8200:8200 openbao:latest

   # Or binary: https://openbao.org/downloads
   ```

2. **Configure Wegweiser:**
   ```bash
   sudo bash install.sh
   # Choose option 2 when prompted
   # Enter OpenBao address and token when asked
   ```

3. **Add secrets to OpenBao:**
   ```bash
   export VAULT_ADDR=http://localhost:8200
   export VAULT_TOKEN=your-token

   vault kv put secret/wegweiser/databaseurl \
     value="postgresql://user:pass@db-server/wegweiser"

   vault kv put secret/wegweiser/secretkey \
     value="your-random-secret-key"
   ```

See `config/secrets.openbao.example` for complete secret setup.

### Production (Azure)

**Best for:** Microsoft Azure deployments, enterprise environments

**Configuration:**
- Secret Storage: Azure Key Vault
- Database: Azure Database for PostgreSQL
- Cache: Azure Cache for Redis
- AI Provider: Azure OpenAI (recommended) or others

**Key Benefits:**
- Native Azure integration
- Managed services (no infrastructure to maintain)
- Enterprise-grade security
- SSO with Azure AD

**Setup Instructions:**

1. **Prerequisites:**
   - Azure subscription
   - Azure Key Vault created
   - Azure Database for PostgreSQL provisioned
   - Azure Cache for Redis provisioned
   - Azure AD application registered

2. **Configure Wegweiser:**
   ```bash
   sudo bash install.sh
   # Choose option 3 when prompted
   # Enter Azure details when asked
   ```

3. **Add secrets to Azure Key Vault:**
   ```bash
   az keyvault secret set --vault-name your-vault \
     --name DatabaseUrl \
     --value "postgresql://user:pass@server:5432/wegweiser"

   az keyvault secret set --vault-name your-vault \
     --name AzureOpenaiApikey \
     --value "your-api-key"
   ```

4. **Configure Azure AD OAuth:**
   - Add redirect URI: `https://yourapp.com/auth/microsoft/callback`
   - Note the Client ID and Secret
   - Note the Tenant ID

## Configuration Options

### Environment Variables

All configuration can be done via `.env` file. See `.env.example` for all available options.

**Critical Variables:**
```env
# Database
DATABASE_URL=postgresql://user:pass@host/dbname
SQLALCHEMY_DATABASE_URI=postgresql://user:pass@host/dbname

# Redis
REDIS_HOST=localhost
REDIS_PORT=6379

# Security
SECRET_KEY=your-32-character-random-key
API_KEY=your-api-key

# AI Provider
AI_PROVIDER=openai
OPENAI_API_KEY=sk_your_openai_key
```

### Secret Storage Options

#### Local (Development)
```env
SECRET_STORAGE=local
# Secrets stored in .env file - remember to protect it!
```

#### Azure Key Vault
```env
SECRET_STORAGE=azure
AZURE_KEY_VAULT_ENDPOINT=https://your-vault.vault.azure.net/
```

#### OpenBao
```env
SECRET_STORAGE=openbao
OPENBAO_ADDR=http://localhost:8200
OPENBAO_TOKEN=your-token
OPENBAO_SECRET_PATH=secret/wegweiser
```

### AI Provider Configuration

#### Azure OpenAI
```env
AI_PROVIDER=azure
AZURE_OPENAI_API_KEY=your-key
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
AZURE_OPENAI_API_VERSION=2024-02-01
AZURE_OPENAI_DEPLOYMENT=gpt-4o
```

#### OpenAI
```env
AI_PROVIDER=openai
OPENAI_API_KEY=sk_your_key
OPENAI_MODEL=gpt-4o
```

#### Anthropic Claude
```env
AI_PROVIDER=anthropic
ANTHROPIC_API_KEY=sk_ant_your_key
ANTHROPIC_MODEL=claude-3-5-sonnet-20241022
```

#### Ollama (Local)
```env
AI_PROVIDER=ollama
OLLAMA_HOST=http://localhost:11434
OLLAMA_MODEL=llama2
```

## Post-Installation

### 1. Verify Setup
```bash
bash verify-setup.sh
```

### 2. Start Services
```bash
# Enable and start services
sudo systemctl enable wegweiser
sudo systemctl enable wegweiser-celery
sudo systemctl start wegweiser
sudo systemctl start wegweiser-celery

# Check status
sudo systemctl status wegweiser
sudo systemctl status wegweiser-celery
```

### 3. Check Logs
```bash
# Flask application logs
sudo journalctl -u wegweiser -f

# Celery worker logs
sudo journalctl -u wegweiser-celery -f

# Application logs
tail -f wlog/wegweiser.log
```

### 4. Access Application
- Development: `http://localhost:5000`
- Production: `https://yourdomain.com` (with HTTPS configured)

### 5. Initial Login
- Email: Admin email configured during setup
- Password: Admin password configured during setup

## Troubleshooting

### Database Connection Error
```bash
# Test PostgreSQL connection
psql -U wegweiser -h localhost -d wegweiser

# Check DATABASE_URL in .env
grep DATABASE_URL .env
```

### Redis Connection Error
```bash
# Test Redis connection
redis-cli -h localhost -p 6379 ping

# Should return: PONG
```

### Secret Not Found Error
```bash
# If using Azure Key Vault:
az keyvault secret list --vault-name your-vault

# If using OpenBao:
vault kv list secret/wegweiser

# Check SECRET_STORAGE setting
grep SECRET_STORAGE .env
```

### Service Won't Start
```bash
# Check service status and errors
sudo systemctl status wegweiser
sudo systemctl status wegweiser-celery

# View system logs
sudo journalctl -xe

# Check for permission issues
sudo chown -R www-data:www-data /opt/wegweiser
```

## Security Best Practices

1. **Protect .env File**
   ```bash
   chmod 600 .env
   ```

2. **Don't Commit Secrets**
   ```bash
   echo ".env" >> .gitignore
   ```

3. **Use HTTPS in Production**
   - Run through Nginx reverse proxy
   - Enable Let's Encrypt certificates
   - Set `USE_HTTPS=true` in .env

4. **Regular Backups**
   ```bash
   # Database backup
   pg_dump -U wegweiser -d wegweiser > backup.sql

   # Key backup
   cp .env .env.backup
   ```

5. **Rotate Credentials Regularly**
   - API keys every 90 days
   - Passwords every 60 days
   - Database passwords on personnel changes

6. **Monitor Access**
   - Enable audit logging
   - Monitor secret access patterns
   - Review application logs regularly

## Upgrading Wegweiser

```bash
# Stop services
sudo systemctl stop wegweiser wegweiser-celery

# Pull latest changes
cd /opt/wegweiser
git pull origin main

# Update dependencies
source venv/bin/activate
pip install -r requirements.txt

# Run migrations
export FLASK_APP=wsgi.py
flask db upgrade

# Restart services
sudo systemctl start wegweiser wegweiser-celery
```

## Uninstalling Wegweiser

```bash
# Stop services
sudo systemctl stop wegweiser
sudo systemctl stop wegweiser-celery

# Remove service files
sudo systemctl disable wegweiser
sudo systemctl disable wegweiser-celery
sudo rm /etc/systemd/system/wegweiser.service
sudo rm /etc/systemd/system/wegweiser-celery.service

# Reload systemd
sudo systemctl daemon-reload

# Remove application (optional)
sudo rm -rf /opt/wegweiser

# Remove database (optional - DESTRUCTIVE!)
sudo -u postgres dropdb wegweiser
sudo -u postgres dropuser wegweiser
```

## Getting Help

- **Documentation**: https://docs.wegweiser.app
- **GitHub Issues**: https://github.com/creativeheadz/wegweiser/issues
- **Community Chat**: https://discord.gg/wegweiser (if available)

## Additional Resources

- [Architecture Overview](./documentation/ARCHITECTURE.md)
- [Configuration Reference](./documentation/CONFIGURATION.md)
- [API Documentation](./documentation/API.md)
- [Troubleshooting Guide](./documentation/TROUBLESHOOTING.md)
