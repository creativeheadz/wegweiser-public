#!/bin/bash

# Filepath: configure-env.sh
# Wegweiser Environment Configuration Wizard
# Interactive .env file generator with validation and smart defaults

set -e
# Enable color support for terminals
export TERM=${TERM:-xterm-256color}

# Text formatting
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
MAGENTA='\033[0;35m'
NC='\033[0m'
BOLD='\033[1m'
DIM='\033[2m'

# Configuration storage
declare -A CONFIG

print_status() { echo -e "${GREEN}[✓]${NC} $1"; }
print_error() { echo -e "${RED}[✗]${NC} $1"; }
print_warning() { echo -e "${YELLOW}[!]${NC} $1"; }
print_info() { echo -e "${BLUE}[i]${NC} $1"; }

print_header() {
    echo -e "\n${BOLD}${CYAN}═══════════════════════════════════════════════════════════${NC}"
    echo -e "${BOLD}${CYAN}  $1${NC}"
    echo -e "${BOLD}${CYAN}═══════════════════════════════════════════════════════════${NC}\n"
}

print_section() {
    echo -e "\n${BOLD}${MAGENTA}▶ $1${NC}"
}

# Generate random secure string
generate_secret() {
    local length=${1:-32}
    openssl rand -base64 48 | tr -d "=+/" | cut -c1-${length}
}

# Generate UUID
generate_uuid() {
    if command -v uuidgen &> /dev/null; then
        uuidgen
    else
        cat /proc/sys/kernel/random/uuid 2>/dev/null || \
        python3 -c 'import uuid; print(uuid.uuid4())' 2>/dev/null || \
        echo "$(date +%s)-$(shuf -i 1000-9999 -n 1)"
    fi
}

# Prompt for input with default value
prompt_input() {
    local prompt_text="$1"
    local default_value="$2"
    local is_secret="${3:-false}"
    local value=""

    if [ "$is_secret" == "true" ]; then
        echo -ne "${CYAN}${prompt_text}${NC}"
        if [ -n "$default_value" ]; then
            echo -ne " ${DIM}[auto-generated]${NC}"
        fi
        echo -ne ": "
        read -s value
        echo ""
        if [ -z "$value" ]; then
            value="$default_value"
        fi
    else
        if [ -n "$default_value" ]; then
            echo -ne "${CYAN}${prompt_text}${NC} ${DIM}[$default_value]${NC}: "
        else
            echo -ne "${CYAN}${prompt_text}${NC}: "
        fi
        read value
        if [ -z "$value" ]; then
            value="$default_value"
        fi
    fi

    echo "$value"
}

# Prompt yes/no question
prompt_yes_no() {
    local prompt_text="$1"
    local default_value="${2:-n}"
    local response

    if [ "$default_value" == "y" ] || [ "$default_value" == "yes" ]; then
        echo -ne "${CYAN}${prompt_text}${NC} ${DIM}[Y/n]${NC}: "
    else
        echo -ne "${CYAN}${prompt_text}${NC} ${DIM}[y/N]${NC}: "
    fi

    read response
    response=${response:-$default_value}

    case "$response" in
        [yY][eE][sS]|[yY])
            return 0
            ;;
        *)
            return 1
            ;;
    esac
}

# Prompt for choice from list
prompt_choice() {
    local prompt_text="$1"
    shift
    local options=("$@")
    local choice

    echo -e "${CYAN}${prompt_text}${NC}"
    for i in "${!options[@]}"; do
        echo -e "  ${BOLD}$((i+1)))${NC} ${options[$i]}"
    done

    while true; do
        echo -ne "${CYAN}Enter choice [1-${#options[@]}]${NC}: "
        read choice

        if [[ "$choice" =~ ^[0-9]+$ ]] && [ "$choice" -ge 1 ] && [ "$choice" -le "${#options[@]}" ]; then
            echo "${options[$((choice-1))]}"
            return 0
        else
            print_error "Invalid choice. Please enter a number between 1 and ${#options[@]}"
        fi
    done
}

# Test PostgreSQL connection
test_postgres_connection() {
    local db_user="$1"
    local db_password="$2"
    local db_host="$3"
    local db_port="$4"
    local db_name="$5"

    export PGPASSWORD="$db_password"
    if psql -h "$db_host" -p "$db_port" -U "$db_user" -d postgres -c "SELECT 1;" &>/dev/null; then
        return 0
    else
        return 1
    fi
}

# Test Redis connection
test_redis_connection() {
    local redis_host="$1"
    local redis_port="$2"
    local redis_password="$3"

    if [ -n "$redis_password" ]; then
        if redis-cli -h "$redis_host" -p "$redis_port" -a "$redis_password" ping &>/dev/null | grep -q PONG; then
            return 0
        fi
    else
        if redis-cli -h "$redis_host" -p "$redis_port" ping &>/dev/null | grep -q PONG; then
            return 0
        fi
    fi
    return 1
}

# Validate email format
validate_email() {
    local email="$1"
    if [[ "$email" =~ ^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$ ]]; then
        return 0
    else
        return 1
    fi
}

# Banner
clear
echo -e "${BOLD}${MAGENTA}"
cat << "EOF"
╔════════════════════════════════════════════════════════════╗
║                                                            ║
║        Wegweiser Configuration Wizard                      ║
║        Interactive .env File Generator                     ║
║                                                            ║
╚════════════════════════════════════════════════════════════╝
EOF
echo -e "${NC}\n"

print_info "This wizard will help you configure Wegweiser"
print_info "Press Enter to accept default values shown in [brackets]"
echo ""

# Check if .env already exists
if [ -f ".env" ]; then
    echo ""
    print_warning ".env file already exists!"
    if prompt_yes_no "Do you want to back it up and create a new one?" "n"; then
        BACKUP_FILE=".env.backup.$(date +%Y%m%d_%H%M%S)"
        cp .env "$BACKUP_FILE"
        print_status "Backed up existing .env to: $BACKUP_FILE"
    else
        print_info "Exiting without changes"
        exit 0
    fi
fi

# ============================================================================
# DEPLOYMENT MODE
# ============================================================================

print_header "Step 1: Deployment Configuration"

DEPLOYMENT_MODE=$(prompt_choice "Select deployment mode:" \
    "Development (local testing, SQLite option)" \
    "Production - Self-Hosted (OpenBao, PostgreSQL)" \
    "Production - Azure (Key Vault, Azure DB)" \
    "Custom (manual configuration)")

case "$DEPLOYMENT_MODE" in
    *"Development"*)
        CONFIG[DEPLOYMENT_MODE]="development"
        CONFIG[SECRET_STORAGE]="local"
        print_info "Development mode: Using local .env for secrets"
        ;;
    *"Self-Hosted"*)
        CONFIG[DEPLOYMENT_MODE]="production-self-hosted"
        CONFIG[SECRET_STORAGE]="openbao"
        print_info "Production Self-Hosted: Will configure OpenBao"
        ;;
    *"Azure"*)
        CONFIG[DEPLOYMENT_MODE]="production-azure"
        CONFIG[SECRET_STORAGE]="azure"
        print_info "Production Azure: Will configure Azure Key Vault"
        ;;
    *"Custom"*)
        CONFIG[DEPLOYMENT_MODE]="custom"
        CONFIG[SECRET_STORAGE]=$(prompt_choice "Select secret storage backend:" "local" "azure" "openbao")
        ;;
esac

# ============================================================================
# APPLICATION BASICS
# ============================================================================

print_header "Step 2: Application Configuration"

CONFIG[APP_DIR]=$(prompt_input "Installation directory" "/opt/wegweiser")
CONFIG[APP_USER]=$(prompt_input "Application user" "www-data")
CONFIG[APP_GROUP]=$(prompt_input "Application group" "www-data")
CONFIG[FLASK_PORT]=$(prompt_input "Flask application port" "5000")

print_section "Security Keys (Auto-Generated)"
CONFIG[SECRET_KEY]=$(generate_secret 64)
CONFIG[API_KEY]=$(generate_secret 32)
print_status "Generated SECRET_KEY (64 chars)"
print_status "Generated API_KEY (32 chars)"

# ============================================================================
# DATABASE CONFIGURATION
# ============================================================================

print_header "Step 3: Database Configuration"

if [ "${CONFIG[DEPLOYMENT_MODE]}" == "development" ]; then
    if prompt_yes_no "Use SQLite instead of PostgreSQL? (easier for development)" "y"; then
        CONFIG[DB_TYPE]="sqlite"
        CONFIG[DATABASE_URL]="sqlite:///wegweiser.db"
        CONFIG[SQLALCHEMY_DATABASE_URI]="sqlite:///wegweiser.db"
        print_status "Using SQLite database: wegweiser.db"
    else
        CONFIG[DB_TYPE]="postgresql"
    fi
else
    CONFIG[DB_TYPE]="postgresql"
fi

if [ "${CONFIG[DB_TYPE]}" == "postgresql" ]; then
    print_section "PostgreSQL Configuration"

    CONFIG[DB_NAME]=$(prompt_input "Database name" "wegweiser")
    CONFIG[DB_USER]=$(prompt_input "Database user" "wegweiser")
    CONFIG[DB_PASSWORD]=$(prompt_input "Database password" "$(generate_secret 24)" "true")
    CONFIG[DB_HOST]=$(prompt_input "Database host" "localhost")
    CONFIG[DB_PORT]=$(prompt_input "Database port" "5432")

    # Build connection strings
    CONFIG[DATABASE_URL]="postgresql://${CONFIG[DB_USER]}:${CONFIG[DB_PASSWORD]}@${CONFIG[DB_HOST]}:${CONFIG[DB_PORT]}/${CONFIG[DB_NAME]}"
    CONFIG[SQLALCHEMY_DATABASE_URI]="${CONFIG[DATABASE_URL]}"

    # Test connection
    echo ""
    print_info "Testing database connection..."
    if command -v psql &> /dev/null; then
        if test_postgres_connection "${CONFIG[DB_USER]}" "${CONFIG[DB_PASSWORD]}" "${CONFIG[DB_HOST]}" "${CONFIG[DB_PORT]}" "${CONFIG[DB_NAME]}"; then
            print_status "Database connection successful!"
        else
            print_warning "Could not connect to database"
            print_info "This is OK if the database/user will be created during installation"
        fi
    else
        print_warning "psql not available - skipping connection test"
    fi
fi

# ============================================================================
# REDIS CONFIGURATION
# ============================================================================

print_header "Step 4: Redis Configuration"

CONFIG[REDIS_HOST]=$(prompt_input "Redis host" "localhost")
CONFIG[REDIS_PORT]=$(prompt_input "Redis port" "6379")

if prompt_yes_no "Does Redis require a password?" "n"; then
    CONFIG[REDIS_PASSWORD]=$(prompt_input "Redis password" "" "true")
else
    CONFIG[REDIS_PASSWORD]=""
fi

# Build Redis URLs
if [ -n "${CONFIG[REDIS_PASSWORD]}" ]; then
    CONFIG[CELERY_BROKER_URL]="redis://:${CONFIG[REDIS_PASSWORD]}@${CONFIG[REDIS_HOST]}:${CONFIG[REDIS_PORT]}/0"
    CONFIG[CELERY_RESULT_BACKEND]="redis://:${CONFIG[REDIS_PASSWORD]}@${CONFIG[REDIS_HOST]}:${CONFIG[REDIS_PORT]}/0"
else
    CONFIG[CELERY_BROKER_URL]="redis://${CONFIG[REDIS_HOST]}:${CONFIG[REDIS_PORT]}/0"
    CONFIG[CELERY_RESULT_BACKEND]="redis://${CONFIG[REDIS_HOST]}:${CONFIG[REDIS_PORT]}/0"
fi

# Test Redis connection
echo ""
print_info "Testing Redis connection..."
if command -v redis-cli &> /dev/null; then
    if test_redis_connection "${CONFIG[REDIS_HOST]}" "${CONFIG[REDIS_PORT]}" "${CONFIG[REDIS_PASSWORD]}"; then
        print_status "Redis connection successful!"
    else
        print_warning "Could not connect to Redis"
        print_info "Make sure Redis is running: sudo systemctl start redis-server"
    fi
else
    print_warning "redis-cli not available - skipping connection test"
fi

# ============================================================================
# SECRET STORAGE CONFIGURATION
# ============================================================================

print_header "Step 5: Secret Storage Configuration"

echo -e "Selected storage backend: ${BOLD}${CONFIG[SECRET_STORAGE]}${NC}"
echo ""

if [ "${CONFIG[SECRET_STORAGE]}" == "azure" ]; then
    print_section "Azure Key Vault Configuration"

    CONFIG[AZURE_KEYVAULT_NAME]=$(prompt_input "Azure Key Vault name" "")
    CONFIG[AZURE_KEY_VAULT_ENDPOINT]="https://${CONFIG[AZURE_KEYVAULT_NAME]}.vault.azure.net/"
    CONFIG[AZURE_USE_KEYVAULT]="true"

    print_info "You'll need to configure Azure AD authentication separately"
    print_info "See documentation for setting up Managed Identity or Service Principal"

elif [ "${CONFIG[SECRET_STORAGE]}" == "openbao" ]; then
    print_section "OpenBao Configuration"

    CONFIG[OPENBAO_ADDR]=$(prompt_input "OpenBao server address" "http://localhost:8200")
    CONFIG[OPENBAO_TOKEN]=$(prompt_input "OpenBao token" "" "true")
    CONFIG[OPENBAO_SECRET_PATH]=$(prompt_input "Secret path" "secret/wegweiser")

    if prompt_yes_no "Verify SSL certificates?" "y"; then
        CONFIG[OPENBAO_VERIFY_SSL]="true"
    else
        CONFIG[OPENBAO_VERIFY_SSL]="false"
    fi
else
    print_info "Using local .env file for secret storage"
fi

# ============================================================================
# AI PROVIDER CONFIGURATION
# ============================================================================

print_header "Step 6: AI Provider Configuration"

AI_PROVIDER=$(prompt_choice "Select AI provider:" \
    "OpenAI" \
    "Azure OpenAI" \
    "Anthropic (Claude)" \
    "Ollama (Local)" \
    "Skip (configure later)")

case "$AI_PROVIDER" in
    "OpenAI")
        CONFIG[AI_PROVIDER]="openai"
        CONFIG[OPENAI_API_KEY]=$(prompt_input "OpenAI API key" "" "true")
        CONFIG[OPENAI_MODEL]=$(prompt_input "OpenAI model" "gpt-4o")
        CONFIG[OPENAI_ORG_ID]=$(prompt_input "OpenAI organization ID (optional)" "")
        ;;

    "Azure OpenAI")
        CONFIG[AI_PROVIDER]="azure"
        CONFIG[AZURE_OPENAI_API_KEY]=$(prompt_input "Azure OpenAI API key" "" "true")
        CONFIG[AZURE_OPENAI_ENDPOINT]=$(prompt_input "Azure OpenAI endpoint" "https://your-resource.openai.azure.com/")
        CONFIG[AZURE_OPENAI_API_VERSION]=$(prompt_input "API version" "2024-02-01")
        CONFIG[AZURE_OPENAI_DEPLOYMENT]=$(prompt_input "Deployment name" "gpt-4o")
        ;;

    "Anthropic (Claude)")
        CONFIG[AI_PROVIDER]="anthropic"
        CONFIG[ANTHROPIC_API_KEY]=$(prompt_input "Anthropic API key" "" "true")
        CONFIG[ANTHROPIC_MODEL]=$(prompt_input "Model" "claude-3-5-sonnet-20241022")
        ;;

    "Ollama (Local)")
        CONFIG[AI_PROVIDER]="ollama"
        CONFIG[OLLAMA_HOST]=$(prompt_input "Ollama host" "http://localhost:11434")
        CONFIG[OLLAMA_MODEL]=$(prompt_input "Model name" "llama2")
        ;;

    *)
        print_info "Skipping AI provider configuration"
        ;;
esac

# ============================================================================
# OPTIONAL SERVICES
# ============================================================================

print_header "Step 7: Optional Services"

# Email Configuration
if prompt_yes_no "Configure email (for notifications, password resets)?" "n"; then
    print_section "Email Configuration"

    CONFIG[MAIL_SERVER]=$(prompt_input "SMTP server" "smtp.gmail.com")
    CONFIG[MAIL_PORT]=$(prompt_input "SMTP port" "587")

    if prompt_yes_no "Use TLS?" "y"; then
        CONFIG[MAIL_USE_TLS]="true"
        CONFIG[MAIL_USE_SSL]="false"
    else
        CONFIG[MAIL_USE_TLS]="false"
        if prompt_yes_no "Use SSL?" "y"; then
            CONFIG[MAIL_USE_SSL]="true"
        else
            CONFIG[MAIL_USE_SSL]="false"
        fi
    fi

    CONFIG[MAIL_USERNAME]=$(prompt_input "Email username" "")
    CONFIG[MAIL_PASSWORD]=$(prompt_input "Email password" "" "true")
    CONFIG[MAIL_DEFAULT_SENDER]=$(prompt_input "Default sender email" "noreply@example.com")
fi

# Azure AD OAuth
if prompt_yes_no "Configure Azure AD OAuth (Single Sign-On)?" "n"; then
    print_section "Azure AD OAuth Configuration"

    CONFIG[AZURE_TENANT_ID]=$(prompt_input "Azure Tenant ID" "")
    CONFIG[AZURE_CLIENT_ID]=$(prompt_input "Azure Client ID" "")
    CONFIG[AZURE_CLIENT_SECRET]=$(prompt_input "Azure Client Secret" "" "true")
    CONFIG[AZURE_REDIRECT_URI]=$(prompt_input "Redirect URI" "https://yourapp.com/auth/microsoft/callback")
fi

# Stripe Payments
if prompt_yes_no "Configure Stripe (for payments/subscriptions)?" "n"; then
    print_section "Stripe Configuration"

    CONFIG[STRIPE_SECRET_KEY]=$(prompt_input "Stripe secret key" "" "true")
    CONFIG[STRIPE_WEBHOOK_SECRET]=$(prompt_input "Stripe webhook secret" "" "true")
fi

# ============================================================================
# ADMIN USER
# ============================================================================

print_header "Step 8: Admin User Configuration"

if prompt_yes_no "Create admin user on first startup?" "y"; then
    CONFIG[ADMIN_CREATE_ON_STARTUP]="true"

    while true; do
        CONFIG[ADMIN_EMAIL]=$(prompt_input "Admin email" "admin@example.com")
        if validate_email "${CONFIG[ADMIN_EMAIL]}"; then
            break
        else
            print_error "Invalid email format"
        fi
    done

    CONFIG[ADMIN_PASSWORD]=$(prompt_input "Admin password" "$(generate_secret 16)" "true")
else
    CONFIG[ADMIN_CREATE_ON_STARTUP]="false"
fi

# ============================================================================
# ADDITIONAL SETTINGS
# ============================================================================

print_header "Step 9: Additional Settings"

# Domain and HTTPS
if prompt_yes_no "Configure domain and HTTPS?" "n"; then
    CONFIG[DOMAIN]=$(prompt_input "Domain name" "example.com")
    if prompt_yes_no "Use HTTPS?" "y"; then
        CONFIG[USE_HTTPS]="true"
    else
        CONFIG[USE_HTTPS]="false"
    fi
else
    CONFIG[USE_HTTPS]="false"
    CONFIG[DOMAIN]=""
fi

# IP Blocker storage
if prompt_yes_no "Use Redis for IP blocker (recommended for distributed systems)?" "n"; then
    CONFIG[IP_BLOCKER_USE_REDIS]="true"
    CONFIG[IP_BLOCKER_USE_LMDB]="false"
else
    CONFIG[IP_BLOCKER_USE_REDIS]="false"
    CONFIG[IP_BLOCKER_USE_LMDB]="true"
fi

# Logging
if prompt_yes_no "Enable remote logging?" "n"; then
    CONFIG[REMOTE_LOGGING_ENABLED]="true"
    CONFIG[REMOTE_LOGGING_SERVER]=$(prompt_input "Remote logging server" "localhost")
    CONFIG[REMOTE_LOGGING_PORT]=$(prompt_input "Remote logging port" "6379")
else
    CONFIG[REMOTE_LOGGING_ENABLED]="false"
fi

# ============================================================================
# GENERATE .env FILE
# ============================================================================

print_header "Generating Configuration File"

cat > .env << EOF
# Wegweiser Environment Configuration
# Generated by configure-env.sh on $(date)
# Deployment Mode: ${CONFIG[DEPLOYMENT_MODE]}

# ============================================================================
# APPLICATION CONFIGURATION
# ============================================================================

APP_DIR=${CONFIG[APP_DIR]}
APP_USER=${CONFIG[APP_USER]}
APP_GROUP=${CONFIG[APP_GROUP]}
SECRET_KEY=${CONFIG[SECRET_KEY]}
API_KEY=${CONFIG[API_KEY]}
FLASK_PORT=${CONFIG[FLASK_PORT]}

# ============================================================================
# DATABASE CONFIGURATION
# ============================================================================

EOF

if [ "${CONFIG[DB_TYPE]}" == "postgresql" ]; then
cat >> .env << EOF
DB_NAME=${CONFIG[DB_NAME]}
DB_USER=${CONFIG[DB_USER]}
DB_PASSWORD=${CONFIG[DB_PASSWORD]}
DB_HOST=${CONFIG[DB_HOST]}
DB_PORT=${CONFIG[DB_PORT]}
EOF
fi

cat >> .env << EOF
DATABASE_URL=${CONFIG[DATABASE_URL]}
SQLALCHEMY_DATABASE_URI=${CONFIG[SQLALCHEMY_DATABASE_URI]}

# ============================================================================
# REDIS CONFIGURATION
# ============================================================================

REDIS_HOST=${CONFIG[REDIS_HOST]}
REDIS_PORT=${CONFIG[REDIS_PORT]}
REDIS_PASSWORD=${CONFIG[REDIS_PASSWORD]:-}
CELERY_BROKER_URL=${CONFIG[CELERY_BROKER_URL]}
CELERY_RESULT_BACKEND=${CONFIG[CELERY_RESULT_BACKEND]}

# ============================================================================
# SECRET STORAGE CONFIGURATION
# ============================================================================

SECRET_STORAGE=${CONFIG[SECRET_STORAGE]}
EOF

if [ "${CONFIG[SECRET_STORAGE]}" == "azure" ]; then
cat >> .env << EOF

# Azure Key Vault
AZURE_KEY_VAULT_ENDPOINT=${CONFIG[AZURE_KEY_VAULT_ENDPOINT]:-}
AZURE_KEYVAULT_NAME=${CONFIG[AZURE_KEYVAULT_NAME]:-}
AZURE_USE_KEYVAULT=${CONFIG[AZURE_USE_KEYVAULT]:-false}
EOF
fi

if [ "${CONFIG[SECRET_STORAGE]}" == "openbao" ]; then
cat >> .env << EOF

# OpenBao
OPENBAO_ADDR=${CONFIG[OPENBAO_ADDR]:-}
OPENBAO_TOKEN=${CONFIG[OPENBAO_TOKEN]:-}
OPENBAO_SECRET_PATH=${CONFIG[OPENBAO_SECRET_PATH]:-}
OPENBAO_VERIFY_SSL=${CONFIG[OPENBAO_VERIFY_SSL]:-true}
EOF
fi

cat >> .env << EOF

# ============================================================================
# AI PROVIDER CONFIGURATION
# ============================================================================

AI_PROVIDER=${CONFIG[AI_PROVIDER]:-openai}
EOF

if [ -n "${CONFIG[OPENAI_API_KEY]}" ]; then
cat >> .env << EOF

# OpenAI
OPENAI_API_KEY=${CONFIG[OPENAI_API_KEY]}
OPENAI_MODEL=${CONFIG[OPENAI_MODEL]:-gpt-4o}
OPENAI_ORG_ID=${CONFIG[OPENAI_ORG_ID]:-}
EOF
fi

if [ -n "${CONFIG[AZURE_OPENAI_API_KEY]}" ]; then
cat >> .env << EOF

# Azure OpenAI
AZURE_OPENAI_API_KEY=${CONFIG[AZURE_OPENAI_API_KEY]}
AZURE_OPENAI_ENDPOINT=${CONFIG[AZURE_OPENAI_ENDPOINT]}
AZURE_OPENAI_API_VERSION=${CONFIG[AZURE_OPENAI_API_VERSION]}
AZURE_OPENAI_DEPLOYMENT=${CONFIG[AZURE_OPENAI_DEPLOYMENT]}
EOF
fi

if [ -n "${CONFIG[ANTHROPIC_API_KEY]}" ]; then
cat >> .env << EOF

# Anthropic Claude
ANTHROPIC_API_KEY=${CONFIG[ANTHROPIC_API_KEY]}
ANTHROPIC_MODEL=${CONFIG[ANTHROPIC_MODEL]}
EOF
fi

if [ -n "${CONFIG[OLLAMA_HOST]}" ]; then
cat >> .env << EOF

# Ollama
OLLAMA_HOST=${CONFIG[OLLAMA_HOST]}
OLLAMA_MODEL=${CONFIG[OLLAMA_MODEL]}
EOF
fi

if [ -n "${CONFIG[MAIL_SERVER]}" ]; then
cat >> .env << EOF

# ============================================================================
# EMAIL CONFIGURATION
# ============================================================================

MAIL_SERVER=${CONFIG[MAIL_SERVER]}
MAIL_PORT=${CONFIG[MAIL_PORT]}
MAIL_USE_TLS=${CONFIG[MAIL_USE_TLS]:-true}
MAIL_USE_SSL=${CONFIG[MAIL_USE_SSL]:-false}
MAIL_USERNAME=${CONFIG[MAIL_USERNAME]}
MAIL_PASSWORD=${CONFIG[MAIL_PASSWORD]}
MAIL_DEFAULT_SENDER=${CONFIG[MAIL_DEFAULT_SENDER]}
EOF
fi

if [ -n "${CONFIG[AZURE_TENANT_ID]}" ]; then
cat >> .env << EOF

# ============================================================================
# AZURE AUTHENTICATION & SERVICES
# ============================================================================

AZURE_TENANT_ID=${CONFIG[AZURE_TENANT_ID]}
AZURE_CLIENT_ID=${CONFIG[AZURE_CLIENT_ID]}
AZURE_CLIENT_SECRET=${CONFIG[AZURE_CLIENT_SECRET]}
AZURE_REDIRECT_URI=${CONFIG[AZURE_REDIRECT_URI]}
EOF
fi

if [ -n "${CONFIG[STRIPE_SECRET_KEY]}" ]; then
cat >> .env << EOF

# ============================================================================
# STRIPE PAYMENT CONFIGURATION
# ============================================================================

STRIPE_SECRET_KEY=${CONFIG[STRIPE_SECRET_KEY]}
STRIPE_WEBHOOK_SECRET=${CONFIG[STRIPE_WEBHOOK_SECRET]}
EOF
fi

cat >> .env << EOF

# ============================================================================
# ADMIN USER CONFIGURATION
# ============================================================================

ADMIN_EMAIL=${CONFIG[ADMIN_EMAIL]:-admin@example.com}
ADMIN_PASSWORD=${CONFIG[ADMIN_PASSWORD]:-}
ADMIN_CREATE_ON_STARTUP=${CONFIG[ADMIN_CREATE_ON_STARTUP]:-false}

# ============================================================================
# HTTPS & DOMAIN CONFIGURATION
# ============================================================================

USE_HTTPS=${CONFIG[USE_HTTPS]:-false}
DOMAIN=${CONFIG[DOMAIN]:-}

# ============================================================================
# IP BLOCKER CONFIGURATION
# ============================================================================

IP_BLOCKER_USE_REDIS=${CONFIG[IP_BLOCKER_USE_REDIS]:-false}
IP_BLOCKER_USE_LMDB=${CONFIG[IP_BLOCKER_USE_LMDB]:-true}
IP_BLOCKER_REDIS_HOST=${CONFIG[REDIS_HOST]:-localhost}
IP_BLOCKER_REDIS_PORT=${CONFIG[REDIS_PORT]:-6379}
IP_BLOCKER_REDIS_PASSWORD=${CONFIG[REDIS_PASSWORD]:-}

# ============================================================================
# LOGGING CONFIGURATION
# ============================================================================

REMOTE_LOGGING_ENABLED=${CONFIG[REMOTE_LOGGING_ENABLED]:-false}
REMOTE_LOGGING_SERVER=${CONFIG[REMOTE_LOGGING_SERVER]:-localhost}
REMOTE_LOGGING_PORT=${CONFIG[REMOTE_LOGGING_PORT]:-6379}
REMOTE_LOGGING_PASSWORD=
REMOTE_LOGGING_TIMEOUT=2
REMOTE_LOGGING_RETRY_COUNT=1
LOG_DEVICE_HEALTH_SCORE=false
EOF

# Secure the .env file
chmod 600 .env

print_status ".env file created successfully!"
print_status "File permissions set to 600 (owner read/write only)"
echo ""

# ============================================================================
# SUMMARY
# ============================================================================

print_header "Configuration Summary"

echo -e "${BOLD}Deployment Mode:${NC} ${CONFIG[DEPLOYMENT_MODE]}"
echo -e "${BOLD}Database:${NC} ${CONFIG[DB_TYPE]}"
echo -e "${BOLD}Secret Storage:${NC} ${CONFIG[SECRET_STORAGE]}"
if [ -n "${CONFIG[AI_PROVIDER]}" ]; then
    echo -e "${BOLD}AI Provider:${NC} ${CONFIG[AI_PROVIDER]}"
fi
echo ""

print_status "Configuration complete!"
echo ""
print_info "Next steps:"
echo -e "  1. Review .env file: ${BOLD}nano .env${NC}"
echo -e "  2. Run installation: ${BOLD}sudo bash install.sh${NC}"
echo ""
print_warning "SECURITY REMINDER:"
echo -e "  • Never commit .env to version control"
echo -e "  • Backup .env securely"
echo -e "  • Rotate secrets regularly"
echo ""
