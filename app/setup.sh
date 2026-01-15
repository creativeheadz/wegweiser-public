#!/bin/bash

# Wegweiser Setup Script
# This script automates the deployment of the Wegweiser application

# Enable debugging
set -x

# Ensure we're running in an interactive terminal
if [ ! -t 0 ]; then
    echo "ERROR: This script must be run in an interactive terminal"
    echo "Try running with: sudo bash -i setup.sh"
    exit 1
fi

# Text formatting
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color
BOLD='\033[1m'

# Script version
SCRIPT_VERSION="1.0.0"

# Print script start message
echo "Starting Wegweiser Setup Script v$SCRIPT_VERSION"

# Default values
DEFAULT_APP_DIR="/opt/wegweiser"
DEFAULT_REPO_URL="https://github.com/creativeheadz/wegweiser.git"
DEFAULT_BRANCH="main"
DEFAULT_FLASK_PORT=5000
DEFAULT_REDIS_HOST="localhost"
DEFAULT_REDIS_PORT=6379
DEFAULT_POSTGRES_VERSION="14"
DEFAULT_PYTHON_VERSION="3.10"
DEFAULT_DOMAIN=""
DEFAULT_USE_HTTPS="no"
DEFAULT_ADMIN_EMAIL="admin@example.com"

# Function to print colored output
print_status() {
    echo -e "${GREEN}[+]${NC} $1"
}

print_error() {
    echo -e "${RED}[!]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[!]${NC} $1"
}

print_info() {
    echo -e "${BLUE}[i]${NC} $1"
}

print_header() {
    echo -e "\n${BOLD}$1${NC}\n"
}

# Check if script is run as root
if [ "$EUID" -ne 0 ]; then
    print_error "Please run this script as root"
    exit 1
fi

# Function to check command existence
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to check and install required packages
check_and_install_dependencies() {
    print_header "Checking Dependencies"

    local dependencies=(
        "curl" "wget" "git" "python3" "python3-pip" "python3-venv"
        "build-essential" "libssl-dev" "libffi-dev" "python3-dev"
    )

    local missing_deps=()

    for dep in "${dependencies[@]}"; do
        if ! command_exists "$dep"; then
            print_info "Missing dependency: $dep"
            missing_deps+=("$dep")
        fi
    done

    if [ ${#missing_deps[@]} -gt 0 ]; then
        print_status "Installing missing dependencies..."
        apt-get update
        apt-get install -y "${missing_deps[@]}"
    else
        print_status "All basic dependencies are installed"
    fi
}

# Function to generate random string
generate_random_string() {
    length=$1
    tr -dc A-Za-z0-9 </dev/urandom | head -c $length
}

# Function to get user input with default value
get_input() {
    prompt=$1
    default=$2

    # Force output to be displayed immediately
    echo -e "${prompt} [${default}]: \c"

    # Use a timeout for read to prevent hanging
    if read -t 10 value; then
        echo "${value:-$default}"
    else
        echo "$default"
        echo "Note: Using default value due to input timeout"
    fi
}

# Function to create PostgreSQL configuration
create_pg_config() {
    local db_name=$1
    local db_user=$2
    local db_password=$3
    local pg_version=$4

    if [ -f "/etc/postgresql/${pg_version}/main/pg_hba.conf" ]; then
        # Backup original config
        cp "/etc/postgresql/${pg_version}/main/pg_hba.conf" "/etc/postgresql/${pg_version}/main/pg_hba.conf.bak"

        cat > "/etc/postgresql/${pg_version}/main/pg_hba.conf" <<EOF
# PostgreSQL Client Authentication Configuration File
local   all             postgres                                peer
local   all             all                                     md5
host    all             all             127.0.0.1/32           md5
host    all             all             ::1/128                md5
EOF

        # Restart PostgreSQL to apply changes
        systemctl restart postgresql
        print_status "PostgreSQL configuration updated"
    else
        print_error "PostgreSQL configuration file not found at /etc/postgresql/${pg_version}/main/pg_hba.conf"
        print_warning "You may need to manually configure PostgreSQL"
    fi
}

# Function to setup PostgreSQL
setup_postgresql() {
    print_header "PostgreSQL Setup"

    # Check if PostgreSQL is already installed
    if command_exists "psql"; then
        print_status "PostgreSQL is already installed"
        PG_VERSION=$(psql --version | head -n 1 | cut -d " " -f 3 | cut -d "." -f 1)
    else
        # Install PostgreSQL
        print_status "Installing PostgreSQL..."
        apt-get update
        apt-get install -y postgresql postgresql-contrib
        PG_VERSION=$DEFAULT_POSTGRES_VERSION
    fi

    # Generate database credentials
    DB_NAME=$(get_input "Enter database name" "wegweiser")
    DB_USER=$(get_input "Enter database user" "wegweiser")
    DB_PASSWORD=$(get_input "Enter database password" "$(generate_random_string 16)")
    DB_HOST=$(get_input "Enter database host" "localhost")
    DB_PORT=$(get_input "Enter database port" "5432")

    # Create database and user
    print_status "Creating database and user..."
    if sudo -u postgres psql -lqt | cut -d \| -f 1 | grep -qw "$DB_NAME"; then
        print_warning "Database '$DB_NAME' already exists"
    else
        sudo -u postgres psql <<EOF
CREATE DATABASE $DB_NAME;
EOF
        print_status "Database '$DB_NAME' created"
    fi

    # Check if user exists
    if sudo -u postgres psql -tAc "SELECT 1 FROM pg_roles WHERE rolname='$DB_USER'" | grep -q 1; then
        print_warning "User '$DB_USER' already exists"
    else
        sudo -u postgres psql <<EOF
CREATE USER $DB_USER WITH ENCRYPTED PASSWORD '$DB_PASSWORD';
EOF
        print_status "User '$DB_USER' created"
    fi

    # Grant privileges
    sudo -u postgres psql <<EOF
GRANT ALL PRIVILEGES ON DATABASE $DB_NAME TO $DB_USER;
ALTER USER $DB_USER WITH SUPERUSER;
EOF
    print_status "Privileges granted to user '$DB_USER'"

    # Configure PostgreSQL
    create_pg_config "$DB_NAME" "$DB_USER" "$DB_PASSWORD" "$PG_VERSION"

    # Create database connection string
    DB_CONNECTION_STRING="postgresql://$DB_USER:$DB_PASSWORD@$DB_HOST:$DB_PORT/$DB_NAME"

    print_status "PostgreSQL setup completed"

    # Save database configuration
    echo "DB_NAME=$DB_NAME" >> .env
    echo "DB_USER=$DB_USER" >> .env
    echo "DB_PASSWORD=$DB_PASSWORD" >> .env
    echo "DB_HOST=$DB_HOST" >> .env
    echo "DB_PORT=$DB_PORT" >> .env
    echo "DATABASE_URL=$DB_CONNECTION_STRING" >> .env
    echo "SQLALCHEMY_DATABASE_URI=$DB_CONNECTION_STRING" >> .env
}

# Function to setup Redis
setup_redis() {
    print_header "Redis Setup"

    # Check if Redis is already installed
    if command_exists "redis-cli"; then
        print_status "Redis is already installed"
    else
        # Install Redis
        print_status "Installing Redis..."
        apt-get update
        apt-get install -y redis-server

        # Enable and start Redis
        systemctl enable redis-server
        systemctl start redis-server
    fi

    # Configure Redis
    REDIS_HOST=$(get_input "Enter Redis host" "$DEFAULT_REDIS_HOST")
    REDIS_PORT=$(get_input "Enter Redis port" "$DEFAULT_REDIS_PORT")
    REDIS_PASSWORD=$(get_input "Enter Redis password (leave empty for none)" "")

    # Test Redis connection
    if [ -z "$REDIS_PASSWORD" ]; then
        if redis-cli -h $REDIS_HOST -p $REDIS_PORT ping | grep -q "PONG"; then
            print_status "Redis connection successful"
        else
            print_error "Failed to connect to Redis"
            print_warning "You may need to manually configure Redis"
        fi
    else
        if redis-cli -h $REDIS_HOST -p $REDIS_PORT -a $REDIS_PASSWORD ping | grep -q "PONG"; then
            print_status "Redis connection successful"
        else
            print_error "Failed to connect to Redis"
            print_warning "You may need to manually configure Redis"
        fi
    fi

    # Save Redis configuration
    echo "REDIS_HOST=$REDIS_HOST" >> .env
    echo "REDIS_PORT=$REDIS_PORT" >> .env
    if [ -n "$REDIS_PASSWORD" ]; then
        echo "REDIS_PASSWORD=$REDIS_PASSWORD" >> .env
    fi
}

# Function to setup AI provider
setup_ai_provider() {
    print_header "AI Provider Setup"

    echo "Select AI provider:"
    echo "1) Azure OpenAI (recommended if using Azure)"
    echo "2) OpenAI (standalone OpenAI API)"
    echo "3) Anthropic Claude (Claude models)"
    echo "4) Ollama (Local/self-hosted AI)"
    echo "5) Skip for now (configure later)"

    provider=$(get_input "Enter your choice (1-5)" "1")

    case $provider in
        1)
            setup_azure_openai
            ;;
        2)
            setup_openai
            ;;
        3)
            setup_anthropic
            ;;
        4)
            setup_ollama
            ;;
        5)
            print_status "AI provider setup skipped - configure in .env file later"
            ;;
    esac
}

# Function to setup Azure OpenAI
setup_azure_openai() {
    print_header "Azure OpenAI Configuration"

    echo "AI_PROVIDER=azure" >> .env
    echo "AZURE_OPENAI_API_KEY=$(get_input 'Enter Azure OpenAI API Key' '')" >> .env
    echo "AZURE_OPENAI_ENDPOINT=$(get_input 'Enter Azure OpenAI Endpoint (https://your-resource.openai.azure.com/)' '')" >> .env
    echo "AZURE_OPENAI_API_VERSION=$(get_input 'Enter Azure OpenAI API Version' '2024-02-01')" >> .env
    echo "AZURE_OPENAI_DEPLOYMENT=$(get_input 'Enter Azure OpenAI Deployment Name' 'gpt-4o')" >> .env

    print_status "Azure OpenAI configured"
    print_info "Visit https://portal.azure.com to manage your OpenAI resources"
}

# Function to setup OpenAI
setup_openai() {
    print_header "OpenAI Configuration"

    echo "AI_PROVIDER=openai" >> .env
    echo "OPENAI_API_KEY=$(get_input 'Enter OpenAI API Key' '')" >> .env
    echo "OPENAI_MODEL=$(get_input 'Enter OpenAI Model' 'gpt-4o')" >> .env
    echo "OPENAI_ORG_ID=$(get_input 'Enter OpenAI Organization ID (optional)' '')" >> .env

    print_status "OpenAI configured"
    print_info "Get API keys at https://platform.openai.com/account/api-keys"
}

# Function to setup Anthropic Claude
setup_anthropic() {
    print_header "Anthropic Claude Configuration"

    echo "AI_PROVIDER=anthropic" >> .env
    echo "ANTHROPIC_API_KEY=$(get_input 'Enter Anthropic API Key' '')" >> .env
    echo "ANTHROPIC_MODEL=$(get_input 'Enter Anthropic Model' 'claude-3-5-sonnet-20241022')" >> .env

    print_status "Anthropic Claude configured"
    print_info "Get API keys at https://console.anthropic.com/account/keys"
}

# Function to setup Ollama
setup_ollama() {
    print_header "Ollama Configuration"

    echo "AI_PROVIDER=ollama" >> .env
    echo "OLLAMA_HOST=$(get_input 'Enter Ollama host address' 'http://localhost:11434')" >> .env
    echo "OLLAMA_MODEL=$(get_input 'Enter Ollama Model name' 'llama2')" >> .env

    print_status "Ollama configured"
    print_info "Ensure Ollama is running on the specified host"
}

# Function to setup secret storage
setup_secret_storage() {
    print_header "Secret Storage Setup"

    echo "Select secret storage method:"
    echo "1) Local .env file (development)"
    echo "2) Azure Key Vault (Azure production)"
    echo "3) OpenBao (self-hosted, compatible with Vault API)"
    echo "4) Skip (use environment variables only)"

    storage=$(get_input "Enter your choice (1-4)" "1")

    case $storage in
        1)
            echo "SECRET_STORAGE=local" >> .env
            print_status "Using local .env file for secrets"
            print_warning "Remember: .env files should NOT be committed to version control"
            ;;
        2)
            setup_azure_keyvault
            ;;
        3)
            setup_openbao
            ;;
        4)
            echo "SECRET_STORAGE=env" >> .env
            print_status "Using environment variables only"
            print_warning "Ensure all required secrets are set in environment variables"
            ;;
    esac
}

# Function to setup Azure Key Vault
setup_azure_keyvault() {
    print_header "Azure Key Vault Configuration"

    echo "SECRET_STORAGE=azure" >> .env

    AZURE_KEYVAULT_NAME=$(get_input "Enter Azure Key Vault name" "")
    if [ -z "$AZURE_KEYVAULT_NAME" ]; then
        print_error "Azure Key Vault name cannot be empty"
        return 1
    fi

    AZURE_KEY_VAULT_ENDPOINT="https://${AZURE_KEYVAULT_NAME}.vault.azure.net/"
    echo "AZURE_KEYVAULT_NAME=$AZURE_KEYVAULT_NAME" >> .env
    echo "AZURE_KEY_VAULT_ENDPOINT=$AZURE_KEY_VAULT_ENDPOINT" >> .env
    echo "AZURE_USE_KEYVAULT=true" >> .env

    print_status "Azure Key Vault configured: $AZURE_KEY_VAULT_ENDPOINT"
    print_warning "Make sure your application has proper Azure credentials (Managed Identity or Service Principal)"
}

# Function to setup OpenBao
setup_openbao() {
    print_header "OpenBao Configuration"

    echo "SECRET_STORAGE=openbao" >> .env

    OPENBAO_ADDR=$(get_input "Enter OpenBao server address" "http://localhost:8200")
    OPENBAO_TOKEN=$(get_input "Enter OpenBao authentication token" "")

    if [ -z "$OPENBAO_TOKEN" ]; then
        print_error "OpenBao token cannot be empty"
        return 1
    fi

    OPENBAO_SECRET_PATH=$(get_input "Enter OpenBao secret path (e.g., secret/wegweiser)" "secret/wegweiser")
    OPENBAO_VERIFY_SSL=$(get_input "Verify OpenBao SSL certificate? (true/false)" "true")

    echo "OPENBAO_ADDR=$OPENBAO_ADDR" >> .env
    echo "OPENBAO_TOKEN=$OPENBAO_TOKEN" >> .env
    echo "OPENBAO_SECRET_PATH=$OPENBAO_SECRET_PATH" >> .env
    echo "OPENBAO_VERIFY_SSL=$OPENBAO_VERIFY_SSL" >> .env

    print_status "OpenBao configured: $OPENBAO_ADDR"

    # Test OpenBao connection
    if command_exists curl; then
        if curl -s -H "X-Vault-Token: $OPENBAO_TOKEN" "$OPENBAO_ADDR/v1/sys/health" > /dev/null 2>&1; then
            print_status "OpenBao connection successful"
        else
            print_warning "Could not verify OpenBao connection - check your server address and token"
        fi
    fi
}

# Function to setup Celery service
setup_celery_service() {
    print_header "Celery Service Setup"

    SERVICE_NAME=$(get_input "Enter Celery service name" "wegweiser-celery")

    # Create Celery service file
    cat > /etc/systemd/system/$SERVICE_NAME.service <<EOF
[Unit]
Description=Wegweiser Celery Service
After=network.target postgresql.service redis-server.service

[Service]
Type=forking
User=$APP_USER
Group=$APP_GROUP
EnvironmentFile=/etc/default/$SERVICE_NAME
WorkingDirectory=$APP_DIR
ExecStart=$APP_DIR/app/utilities/celery_worker_wrapper.sh
ExecStop=/bin/sh -c '\${CELERY_BIN} -A \${CELERY_APP} multi stopwait \${CELERYD_NODES} \
    --pidfile=\${CELERYD_PID_FILE}'
ExecReload=/bin/sh -c 'CELERYD_LOG_LEVEL=\$($APP_DIR/venv/bin/python3 $APP_DIR/app/utilities/get_celery_log_level.py 2>/dev/null || echo WARNING) && \${CELERY_BIN} -A \${CELERY_APP} multi restart \${CELERYD_NODES} \
    --pidfile=\${CELERYD_PID_FILE} \
    --logfile=\${CELERYD_LOG_FILE} --loglevel=\${CELERYD_LOG_LEVEL} \
    \${CELERYD_OPTS}'
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

    # Create Celery default configuration
    cat > /etc/default/$SERVICE_NAME <<EOF
# Names of nodes to start
CELERYD_NODES="worker1"

# Absolute or relative path to the 'celery' command:
CELERY_BIN="$APP_DIR/venv/bin/celery"

# App instance to use
CELERY_APP="app.celery"

# How to call manage.py
CELERYD_MULTI="multi"

# Extra command-line arguments to the worker
CELERYD_OPTS="--time-limit=300 --concurrency=8"

# - %n will be replaced with the first part of the nodename.
# - %I will be replaced with the current child process index
#   and is important when using the prefork pool to avoid race conditions.
CELERYD_PID_FILE="/var/run/celery/%n.pid"
CELERYD_LOG_FILE="/var/log/celery/%n%I.log"
CELERYD_LOG_LEVEL="WARNING"

# Environment variables
PYTHONPATH=$APP_DIR
EOF

    # Create necessary directories
    mkdir -p /var/log/celery
    mkdir -p /var/run/celery

    # Set permissions
    chown -R $APP_USER:$APP_GROUP /var/log/celery
    chown -R $APP_USER:$APP_GROUP /var/run/celery
    chmod 755 /var/log/celery
    chmod 755 /var/run/celery

    # Make the Celery wrapper script executable
    chmod +x $APP_DIR/app/utilities/celery_worker_wrapper.sh
    chmod +x $APP_DIR/app/utilities/get_celery_log_level.py

    print_status "Celery service configured"
    print_status "Celery log level will be dynamically determined from config/logging_config.json"

    # Setup logrotate for Celery logs
    setup_celery_logrotate
}

# Function to setup logrotate for Celery logs
setup_celery_logrotate() {
    print_status "Configuring logrotate for Celery logs"

    # Create logrotate configuration for Celery
    cat > /etc/logrotate.d/wegweiser-celery <<EOF
/var/log/celery/*.log {
    size 15M
    rotate 10
    missingok
    notifempty
    compress
    delaycompress
    copytruncate
    postrotate
        systemctl reload celery-worker > /dev/null 2>&1 || true
    endscript
}
EOF

    print_status "Logrotate configuration created for Celery logs (15MB rollover, 10 backups)"
}

# Function to setup Flask application service
setup_flask_service() {
    print_header "Flask Application Service Setup"

    SERVICE_NAME=$(get_input "Enter Flask service name" "wegweiser")
    FLASK_PORT=$(get_input "Enter Flask port" "$DEFAULT_FLASK_PORT")

    # Create Flask service file
    cat > /etc/systemd/system/$SERVICE_NAME.service <<EOF
[Unit]
Description=Wegweiser Flask Application
After=network.target postgresql.service redis-server.service
Wants=postgresql.service redis-server.service

[Service]
User=$APP_USER
Group=$APP_GROUP
WorkingDirectory=$APP_DIR
Environment="PATH=$APP_DIR/venv/bin"
ExecStart=$APP_DIR/venv/bin/gunicorn --workers 4 --bind 0.0.0.0:$FLASK_PORT --access-logfile /var/log/wegweiser/access.log --error-logfile /var/log/wegweiser/error.log --log-level info wsgi:app
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

    # Create log directory
    mkdir -p /var/log/wegweiser
    chown -R $APP_USER:$APP_GROUP /var/log/wegweiser
    chmod 755 /var/log/wegweiser

    print_status "Flask service configured"

    # Setup logrotate for Flask logs
    setup_flask_logrotate

    # Save Flask configuration
    echo "FLASK_PORT=$FLASK_PORT" >> .env
}

# Function to setup logrotate for Flask logs
setup_flask_logrotate() {
    print_status "Configuring logrotate for Flask logs"

    # Create logrotate configuration for Flask
    cat > /etc/logrotate.d/wegweiser-flask <<EOF
/var/log/wegweiser/*.log {
    size 15M
    rotate 10
    missingok
    notifempty
    compress
    delaycompress
    copytruncate
    postrotate
        systemctl reload wegweiser > /dev/null 2>&1 || true
    endscript
}
EOF

    print_status "Logrotate configuration created for Flask logs (15MB rollover, 10 backups)"
}

# Function to create admin user
create_admin_user() {
    print_header "Admin User Setup"

    ADMIN_EMAIL=$(get_input "Enter admin email" "$DEFAULT_ADMIN_EMAIL")
    ADMIN_PASSWORD=$(get_input "Enter admin password" "$(generate_random_string 12)")

    print_status "Admin user will be created during first run"

    # Save admin configuration
    echo "ADMIN_EMAIL=$ADMIN_EMAIL" >> .env
    echo "ADMIN_PASSWORD=$ADMIN_PASSWORD" >> .env
    echo "ADMIN_CREATE_ON_STARTUP=true" >> .env
}

# Function to setup Python environment and install dependencies
setup_python_environment() {
    print_header "Python Environment Setup"

    # Create virtual environment
    print_status "Creating Python virtual environment..."
    python3 -m venv $APP_DIR/venv

    # Activate virtual environment
    source $APP_DIR/venv/bin/activate

    # Upgrade pip
    print_status "Upgrading pip..."
    pip install --upgrade pip

    # Install dependencies
    print_status "Installing Python dependencies..."
    pip install -r $APP_DIR/requirements.txt

    # Install additional dependencies
    print_status "Installing additional dependencies..."
    pip install gunicorn psycopg2-binary redis

    # Deactivate virtual environment
    deactivate

    print_status "Python environment setup completed"
}

# Function to run database migrations
run_database_migrations() {
    print_header "Database Migrations"

    # Activate virtual environment
    source $APP_DIR/venv/bin/activate

    # Run migrations
    print_status "Running database migrations..."
    cd $APP_DIR
    export FLASK_APP=wsgi.py
    flask db upgrade

    # Deactivate virtual environment
    deactivate

    print_status "Database migrations completed"
}

# Function to setup HTTPS with Let's Encrypt
setup_https() {
    print_header "HTTPS Setup"

    USE_HTTPS=$(get_input "Do you want to set up HTTPS with Let's Encrypt? (yes/no)" "$DEFAULT_USE_HTTPS")

    if [ "$USE_HTTPS" = "yes" ] || [ "$USE_HTTPS" = "y" ]; then
        # Install Certbot
        print_status "Installing Certbot..."
        apt-get update
        apt-get install -y certbot python3-certbot-nginx

        # Get domain
        DOMAIN=$(get_input "Enter your domain name" "$DEFAULT_DOMAIN")

        # Check if Nginx is installed
        if ! command_exists "nginx"; then
            print_status "Installing Nginx..."
            apt-get install -y nginx
        fi

        # Configure Nginx
        print_status "Configuring Nginx..."
        cat > /etc/nginx/sites-available/$DOMAIN <<EOF
server {
    listen 80;
    server_name $DOMAIN;

    location / {
        proxy_pass http://127.0.0.1:$FLASK_PORT;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }
}
EOF

        # Enable site
        ln -sf /etc/nginx/sites-available/$DOMAIN /etc/nginx/sites-enabled/

        # Test Nginx configuration
        nginx -t

        # Reload Nginx
        systemctl reload nginx

        # Get SSL certificate
        print_status "Obtaining SSL certificate..."
        certbot --nginx -d $DOMAIN --non-interactive --agree-tos --email $ADMIN_EMAIL

        print_status "HTTPS setup completed"

        # Save HTTPS configuration
        echo "USE_HTTPS=true" >> .env
        echo "DOMAIN=$DOMAIN" >> .env
    else
        print_status "Skipping HTTPS setup"
        echo "USE_HTTPS=false" >> .env
    fi
}

# Function to setup Azure credentials (optional, but recommended for Azure deployments)
setup_azure_credentials() {
    print_header "Azure Credentials Setup (Optional)"

    USE_AZURE=$(get_input "Do you want to configure Azure credentials? (yes/no)" "no")

    if [ "$USE_AZURE" = "yes" ] || [ "$USE_AZURE" = "y" ]; then
        print_info "Azure credentials are used for:"
        print_info "  - Azure AD OAuth (Single Sign-On)"
        print_info "  - Azure Key Vault (Secrets Management)"
        print_info "  - Azure OpenAI API"

        AZURE_TENANT_ID=$(get_input "Enter Azure Tenant ID (Directory ID)" "")
        AZURE_CLIENT_ID=$(get_input "Enter Azure Client ID (Application ID)" "")
        AZURE_CLIENT_SECRET=$(get_input "Enter Azure Client Secret (Password)" "")
        AZURE_REDIRECT_URI=$(get_input "Enter Azure Redirect URI (e.g., https://yourapp.com/auth/microsoft/callback)" "")

        # Save Azure credentials
        if [ -n "$AZURE_TENANT_ID" ]; then
            echo "AZURE_TENANT_ID=$AZURE_TENANT_ID" >> .env
        fi
        if [ -n "$AZURE_CLIENT_ID" ]; then
            echo "AZURE_CLIENT_ID=$AZURE_CLIENT_ID" >> .env
        fi
        if [ -n "$AZURE_CLIENT_SECRET" ]; then
            echo "AZURE_CLIENT_SECRET=$AZURE_CLIENT_SECRET" >> .env
        fi
        if [ -n "$AZURE_REDIRECT_URI" ]; then
            echo "AZURE_REDIRECT_URI=$AZURE_REDIRECT_URI" >> .env
        fi

        print_status "Azure credentials configured"
        print_info "These credentials are sensitive - ensure your .env file is protected (mode 600)"
    else
        print_status "Azure credentials setup skipped"
        print_info "You can configure these later in the .env file if needed"
    fi
}

# Main installation routine
main() {
    print_header "Wegweiser Installation Script v$SCRIPT_VERSION"

    # Check and install dependencies
    check_and_install_dependencies

    # Create .env file if it doesn't exist
    if [ -f ".env" ]; then
        print_warning "Existing .env file found. It will be backed up and a new one will be created."
        cp .env .env.bak.$(date +%Y%m%d%H%M%S)
    fi

    # Create new .env file
    echo "# Wegweiser Environment Configuration" > .env
    echo "# Created by setup.sh on $(date)" >> .env
    echo "" >> .env

    # Get application directory
    APP_DIR=$(get_input "Enter application directory" "$DEFAULT_APP_DIR")
    echo "APP_DIR=$APP_DIR" >> .env

    # Get application user/group
    APP_USER=$(get_input "Enter application user" "www-data")
    APP_GROUP=$(get_input "Enter application group" "www-data")
    echo "APP_USER=$APP_USER" >> .env
    echo "APP_GROUP=$APP_GROUP" >> .env

    # Generate secret key
    SECRET_KEY=$(generate_random_string 32)
    echo "SECRET_KEY=$SECRET_KEY" >> .env

    # Get repository information
    REPO_URL=$(get_input "Enter repository URL" "$DEFAULT_REPO_URL")
    REPO_BRANCH=$(get_input "Enter repository branch" "$DEFAULT_BRANCH")

    # Setup components
    setup_postgresql
    setup_redis
    setup_ai_provider
    setup_secret_storage
    setup_azure_credentials

    # Create application directory
    if [ -d "$APP_DIR" ]; then
        print_warning "Directory $APP_DIR already exists"
    else
        print_status "Creating application directory..."
        mkdir -p $APP_DIR
    fi

    # Clone repository if not in local deployment mode
    if [ "$LOCAL_DEPLOYMENT" = true ]; then
        print_status "Skipping repository cloning (local deployment mode)"
        # Check if we're already in the app directory
        if [ "$(pwd)" != "$APP_DIR" ]; then
            print_warning "Current directory is not $APP_DIR"
            print_status "Make sure all required files are present in $APP_DIR"
        fi
    else
        if [ -d "$APP_DIR/.git" ]; then
            print_warning "Git repository already exists in $APP_DIR"
            print_status "Pulling latest changes..."
            cd $APP_DIR
            git pull
        else
            print_status "Cloning Wegweiser repository..."
            git clone -b $REPO_BRANCH $REPO_URL $APP_DIR
        fi
    fi

    # Setup Python environment
    setup_python_environment

    # Create required directories
    mkdir -p $APP_DIR/logs
    mkdir -p $APP_DIR/flask_session
    mkdir -p $APP_DIR/app/static/images/profilepictures
    mkdir -p $APP_DIR/app/static/images/tenantprofile
    mkdir -p $APP_DIR/app/data/ip_blocker

    # Set permissions
    chown -R $APP_USER:$APP_GROUP $APP_DIR
    chmod -R 755 $APP_DIR

    # Copy .env file to application directory
    cp .env $APP_DIR/.env

    # Run database migrations
    run_database_migrations

    # Create admin user
    create_admin_user

    # Setup services
    setup_celery_service
    setup_flask_service

    # Setup HTTPS
    setup_https

    # Reload systemd
    systemctl daemon-reload

    # Enable and start services
    print_status "Enabling and starting services..."
    systemctl enable wegweiser-celery
    systemctl enable wegweiser
    systemctl start wegweiser-celery
    systemctl start wegweiser

    print_header "Installation Complete!"
    print_status "Wegweiser has been installed to $APP_DIR"
    print_status "Admin credentials: $ADMIN_EMAIL / $ADMIN_PASSWORD"

    if [ "$USE_HTTPS" = "yes" ] || [ "$USE_HTTPS" = "y" ]; then
        print_status "Your application is available at: https://$DOMAIN"
    else
        print_status "Your application is available at: http://$(hostname -I | awk '{print $1}'):$FLASK_PORT"
    fi

    print_status "Please check the $APP_DIR/.env file for your configuration"
    print_warning "Make sure to save your admin credentials in a secure location!"
}

# Function to display help
show_help() {
    echo "Wegweiser Setup Script v$SCRIPT_VERSION"
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  -h, --help     Show this help message and exit"
    echo "  -y, --yes      Non-interactive mode, use default values"
    echo "  -v, --version  Show version information and exit"
    echo "  -l, --local    Skip repository cloning (use when files are already present)"
    echo ""
    echo "For more information, visit: https://github.com/creativeheadz/wegweiser"
}

# Default options
LOCAL_DEPLOYMENT=false

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -h|--help)
            show_help
            exit 0
            ;;
        -y|--yes)
            # TODO: Implement non-interactive mode
            print_warning "Non-interactive mode not yet implemented"
            shift
            ;;
        -v|--version)
            echo "Wegweiser Setup Script v$SCRIPT_VERSION"
            exit 0
            ;;
        -l|--local)
            LOCAL_DEPLOYMENT=true
            print_status "Local deployment mode enabled - will skip repository cloning"
            shift
            ;;
        *)
            print_error "Unknown option: $1"
            show_help
            exit 1
            ;;
    esac
done

# Run main installation
main