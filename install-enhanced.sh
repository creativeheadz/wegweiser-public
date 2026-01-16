#!/bin/bash

# Filepath: install-enhanced.sh
# Wegweiser Enhanced Installation Wizard
# Features: Progress tracking, state management, error recovery, resume capability

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

# Source state tracking library
if [ -f ".install-state.sh" ]; then
    source .install-state.sh
else
    echo "ERROR: .install-state.sh not found"
    exit 1
fi

print_status() {
    echo -e "${GREEN}[✓]${NC} $1"
}

print_error() {
    echo -e "${RED}[✗]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[!]${NC} $1"
}

print_info() {
    echo -e "${BLUE}[i]${NC} $1"
}

print_header() {
    echo -e "\n${BOLD}${CYAN}═══════════════════════════════════════════════════════════${NC}"
    echo -e "${BOLD}${CYAN}  $1${NC}"
    echo -e "${BOLD}${CYAN}═══════════════════════════════════════════════════════════${NC}\n"
}

print_section() {
    echo -e "\n${BOLD}▶ $1${NC}"
}

# Error handler
error_handler() {
    local line_num=$1
    local error_code=$2

    print_error "Installation failed at line $line_num with exit code $error_code"

    if [ -n "$CURRENT_STEP" ]; then
        step_fail "$CURRENT_STEP" "Failed at line $line_num (exit code: $error_code)"
    fi

    install_failed "Installation interrupted at line $line_num"

    echo ""
    print_warning "Installation state has been saved"
    print_info "You can resume by running: sudo bash install-enhanced.sh --resume"
    echo ""

    exit $error_code
}

trap 'error_handler ${LINENO} $?' ERR

# Banner
clear
echo -e "${BOLD}${MAGENTA}"
cat << "EOF"
╔════════════════════════════════════════════════════════════╗
║                                                            ║
║        Wegweiser Enhanced Installation Wizard             ║
║        AI-Powered Intelligence Layer for MSPs              ║
║                                                            ║
║        With Progress Tracking & Error Recovery            ║
║                                                            ║
╚════════════════════════════════════════════════════════════╝
EOF
echo -e "${NC}\n"

# Check for resume flag
RESUME_MODE=false
if [ "$1" == "--resume" ]; then
    RESUME_MODE=true
fi

# Check if can resume
if $RESUME_MODE; then
    if can_resume; then
        print_header "Resuming Previous Installation"
        show_status
        echo ""
        read -p "Do you want to continue from where it left off? (yes/no): " confirm
        if [ "$confirm" != "yes" ]; then
            print_info "Exiting without changes"
            exit 0
        fi
    else
        print_error "No installation to resume"
        print_info "Starting fresh installation"
        RESUME_MODE=false
    fi
fi

# Initialize state if not resuming
if ! $RESUME_MODE; then
    init_state
fi

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    print_error "This installation requires root privileges"
    print_info "Please run with: sudo bash install-enhanced.sh"
    exit 1
fi

# Check if we're in the right directory
if [ ! -f "wsgi.py" ] || [ ! -d "app" ]; then
    print_error "This script must be run from the Wegweiser root directory"
    print_info "Ensure wsgi.py and app/ directory exist in the current directory"
    exit 1
fi

print_status "Running from: $(pwd)"
echo ""

# ============================================================================
# STEP 0: PRE-FLIGHT CHECKS
# ============================================================================

CURRENT_STEP="preflight"
if ! is_step_completed "$CURRENT_STEP"; then
    step_start "$CURRENT_STEP" "Running pre-flight checks"
    print_header "Step 0: Pre-Flight Checks"

    print_info "Checking prerequisites..."

    if [ -f "check-prereqs.sh" ]; then
        if bash check-prereqs.sh; then
            print_status "Pre-flight checks passed!"
        else
            print_warning "Pre-flight checks found issues"
            read -p "Continue anyway? (yes/no): " continue_anyway
            if [ "$continue_anyway" != "yes" ]; then
                step_fail "$CURRENT_STEP" "User cancelled after pre-flight check failures"
                exit 1
            fi
        fi
    else
        print_warning "check-prereqs.sh not found - skipping pre-flight checks"
    fi

    step_complete "$CURRENT_STEP"
else
    print_info "Skipping completed step: Pre-flight checks"
fi

show_progress
echo ""

# ============================================================================
# STEP 1: DEPLOYMENT MODE SELECTION
# ============================================================================

CURRENT_STEP="deployment_mode"
if ! is_step_completed "$CURRENT_STEP"; then
    step_start "$CURRENT_STEP" "Selecting deployment mode"
    print_header "Step 1: Deployment Mode Selection"

    echo "Select your deployment scenario:"
    echo ""
    echo "1) ${BOLD}Development${NC}"
    echo "   - Local .env file for secrets"
    echo "   - SQLite or local PostgreSQL"
    echo "   - Best for: Testing, development, small deployments"
    echo ""
    echo "2) ${BOLD}Production (Self-Hosted)${NC}"
    echo "   - OpenBao for secrets management"
    echo "   - External PostgreSQL database"
    echo "   - Best for: On-premises, private cloud, maximum control"
    echo ""
    echo "3) ${BOLD}Production (Azure)${NC}"
    echo "   - Azure Key Vault for secrets"
    echo "   - Azure Database for PostgreSQL"
    echo "   - Best for: Azure cloud deployment, enterprise"
    echo ""
    echo "4) ${BOLD}Custom${NC}"
    echo "   - Choose your own configuration"
    echo "   - Maximum flexibility"
    echo ""

    read -p "Select deployment mode (1-4): " mode

    case $mode in
        1)
            DEPLOYMENT_MODE="development"
            print_status "Selected: Development Mode"
            export LOCAL_DEPLOYMENT=true
            ;;
        2)
            DEPLOYMENT_MODE="production-self-hosted"
            print_status "Selected: Production (Self-Hosted)"
            export LOCAL_DEPLOYMENT=true
            export SETUP_MODE="production-self-hosted"
            ;;
        3)
            DEPLOYMENT_MODE="production-azure"
            print_status "Selected: Production (Azure)"
            export LOCAL_DEPLOYMENT=true
            export SETUP_MODE="production-azure"
            ;;
        4)
            DEPLOYMENT_MODE="custom"
            print_status "Selected: Custom"
            export LOCAL_DEPLOYMENT=true
            export SETUP_MODE="custom"
            ;;
        *)
            print_error "Invalid selection"
            step_fail "$CURRENT_STEP" "Invalid deployment mode selection"
            exit 1
            ;;
    esac

    set_deployment_mode "$DEPLOYMENT_MODE"
    step_complete "$CURRENT_STEP"
else
    print_info "Skipping completed step: Deployment mode selection"
    DEPLOYMENT_MODE=$(jq -r '.deployment_mode' .install-state.json)
fi

show_progress
echo ""

# ============================================================================
# STEP 2: ENVIRONMENT CONFIGURATION
# ============================================================================

CURRENT_STEP="environment_config"
if ! is_step_completed "$CURRENT_STEP"; then
    step_start "$CURRENT_STEP" "Configuring environment variables"
    print_header "Step 2: Environment Configuration"

    if [ -f ".env" ]; then
        print_warning ".env file already exists"
        read -p "Do you want to keep it? (yes/no): " keep_env
        if [ "$keep_env" != "yes" ]; then
            if [ -f "configure-env.sh" ]; then
                print_info "Running configuration wizard..."
                bash configure-env.sh
            else
                print_warning "configure-env.sh not found"
                print_info "Please copy .env.example to .env and edit manually"
                cp .env.example .env
            fi
        fi
    else
        print_info "No .env file found"
        if [ -f "configure-env.sh" ]; then
            read -p "Run interactive configuration wizard? (yes/no): " run_wizard
            if [ "$run_wizard" == "yes" ]; then
                bash configure-env.sh
            else
                print_info "Copying .env.example to .env"
                cp .env.example .env
                print_warning "Please edit .env file before continuing"
                read -p "Press Enter when ready to continue..."
            fi
        else
            cp .env.example .env
            print_warning "Please edit .env file before continuing"
            read -p "Press Enter when ready to continue..."
        fi
    fi

    # Verify .env exists
    if [ ! -f ".env" ]; then
        print_error ".env file not found - cannot continue"
        step_fail "$CURRENT_STEP" ".env file missing"
        exit 1
    fi

    # Secure .env
    chmod 600 .env
    print_status ".env file secured (permissions: 600)"

    step_complete "$CURRENT_STEP"
else
    print_info "Skipping completed step: Environment configuration"
fi

show_progress
echo ""

# ============================================================================
# STEP 3: CREATE BACKUP
# ============================================================================

CURRENT_STEP="create_backup"
if ! is_step_completed "$CURRENT_STEP"; then
    step_start "$CURRENT_STEP" "Creating installation backup"
    print_header "Step 3: Creating Backup"

    BACKUP_NAME="pre-install-$(date +%Y%m%d_%H%M%S)"
    BACKUP_PATH=$(create_backup "$BACKUP_NAME")

    print_status "Backup created: $BACKUP_PATH"
    step_complete "$CURRENT_STEP"
else
    print_info "Skipping completed step: Create backup"
fi

show_progress
echo ""

# ============================================================================
# STEP 4: INSTALL SYSTEM DEPENDENCIES
# ============================================================================

CURRENT_STEP="system_dependencies"
if ! is_step_completed "$CURRENT_STEP"; then
    step_start "$CURRENT_STEP" "Installing system dependencies"
    print_header "Step 4: System Dependencies"

    print_info "Updating package lists..."
    apt-get update -qq

    print_info "Installing required packages..."
    DEBIAN_FRONTEND=noninteractive apt-get install -y \
        build-essential \
        python3-dev \
        python3-pip \
        python3-venv \
        libpq-dev \
        libssl-dev \
        libffi-dev \
        git \
        curl \
        wget \
        jq \
        >/dev/null 2>&1

    print_status "System dependencies installed"
    step_complete "$CURRENT_STEP"
else
    print_info "Skipping completed step: System dependencies"
fi

show_progress
echo ""

# ============================================================================
# STEP 5: SETUP PYTHON VIRTUAL ENVIRONMENT
# ============================================================================

CURRENT_STEP="python_venv"
if ! is_step_completed "$CURRENT_STEP"; then
    step_start "$CURRENT_STEP" "Setting up Python virtual environment"
    print_header "Step 5: Python Virtual Environment"

    if [ ! -d "venv" ]; then
        print_info "Creating virtual environment..."
        python3 -m venv venv
        print_status "Virtual environment created"
    else
        print_warning "Virtual environment already exists"
    fi

    print_info "Activating virtual environment..."
    source venv/bin/activate

    print_info "Upgrading pip..."
    pip install --upgrade pip >/dev/null 2>&1

    print_status "Python environment ready"
    step_complete "$CURRENT_STEP"
else
    print_info "Skipping completed step: Python virtual environment"
    source venv/bin/activate
fi

show_progress
echo ""

# ============================================================================
# STEP 6: INSTALL PYTHON DEPENDENCIES
# ============================================================================

CURRENT_STEP="python_dependencies"
if ! is_step_completed "$CURRENT_STEP"; then
    step_start "$CURRENT_STEP" "Installing Python dependencies"
    print_header "Step 6: Python Dependencies"

    print_info "This may take 5-10 minutes..."

    if pip install -r requirements.txt >/dev/null 2>&1; then
        print_status "Python dependencies installed successfully"
        step_complete "$CURRENT_STEP"
    else
        print_error "Failed to install Python dependencies"
        print_info "Trying with verbose output..."
        pip install -r requirements.txt
        step_fail "$CURRENT_STEP" "Python dependency installation failed"
        exit 1
    fi
else
    print_info "Skipping completed step: Python dependencies"
fi

show_progress
echo ""

# ============================================================================
# STEP 7: DATABASE SETUP
# ============================================================================

CURRENT_STEP="database_setup"
if ! is_step_completed "$CURRENT_STEP"; then
    step_start "$CURRENT_STEP" "Setting up database"
    print_header "Step 7: Database Setup"

    # Source .env for database credentials
    source .env

    if [[ "$DATABASE_URL" == sqlite* ]]; then
        print_info "Using SQLite database"
        print_status "SQLite database configured"
    else
        print_info "Setting up PostgreSQL database..."

        # Check if database exists
        if sudo -u postgres psql -lqt | cut -d \| -f 1 | grep -qw "$DB_NAME"; then
            print_warning "Database '$DB_NAME' already exists"
        else
            print_info "Creating database: $DB_NAME"
            sudo -u postgres psql -c "CREATE DATABASE $DB_NAME;"
        fi

        # Check if user exists
        if sudo -u postgres psql -tAc "SELECT 1 FROM pg_roles WHERE rolname='$DB_USER'" | grep -q 1; then
            print_warning "User '$DB_USER' already exists"
        else
            print_info "Creating user: $DB_USER"
            sudo -u postgres psql -c "CREATE USER $DB_USER WITH ENCRYPTED PASSWORD '$DB_PASSWORD';"
        fi

        # Grant privileges
        sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE $DB_NAME TO $DB_USER;"
        sudo -u postgres psql -c "ALTER USER $DB_USER WITH SUPERUSER;"

        print_status "PostgreSQL database configured"
    fi

    step_complete "$CURRENT_STEP"
else
    print_info "Skipping completed step: Database setup"
fi

show_progress
echo ""

# ============================================================================
# STEP 8: DATABASE MIGRATIONS
# ============================================================================

CURRENT_STEP="database_migrations"
if ! is_step_completed "$CURRENT_STEP"; then
    step_start "$CURRENT_STEP" "Running database migrations"
    print_header "Step 8: Database Migrations"

    export FLASK_APP=wsgi.py

    # Initialize migrations if needed
    if [ ! -d "migrations" ]; then
        print_info "Initializing database migrations..."
        flask db init
    fi

    # Run migrations
    print_info "Running database migrations..."
    flask db upgrade

    # Create roles
    print_info "Creating user roles..."
    flask create_roles || true

    # Populate server core data
    print_info "Populating server core data..."
    flask populate_servercore || true

    print_status "Database migrations completed"
    step_complete "$CURRENT_STEP"
else
    print_info "Skipping completed step: Database migrations"
fi

show_progress
echo ""

# ============================================================================
# STEP 9: SETUP REDIS
# ============================================================================

CURRENT_STEP="redis_setup"
if ! is_step_completed "$CURRENT_STEP"; then
    step_start "$CURRENT_STEP" "Configuring Redis"
    print_header "Step 9: Redis Configuration"

    if systemctl is-active --quiet redis-server || systemctl is-active --quiet redis; then
        print_status "Redis is already running"
    else
        print_info "Starting Redis..."
        systemctl start redis-server || systemctl start redis || true
        systemctl enable redis-server || systemctl enable redis || true
    fi

    # Test Redis connection
    if redis-cli ping >/dev/null 2>&1; then
        print_status "Redis connection successful"
    else
        print_warning "Could not connect to Redis"
    fi

    step_complete "$CURRENT_STEP"
else
    print_info "Skipping completed step: Redis setup"
fi

show_progress
echo ""

# ============================================================================
# STEP 10: SETUP SYSTEMD SERVICES
# ============================================================================

CURRENT_STEP="systemd_services"
if ! is_step_completed "$CURRENT_STEP"; then
    step_start "$CURRENT_STEP" "Creating systemd services"
    print_header "Step 10: Systemd Services"

    APP_DIR=$(pwd)
    VENV_PATH="$APP_DIR/venv"

    # Create Flask service
    print_info "Creating wegweiser.service..."
    cat > /etc/systemd/system/wegweiser.service << EOF
[Unit]
Description=Wegweiser Flask Application
After=network.target postgresql.service redis.service

[Service]
Type=notify
User=www-data
Group=www-data
WorkingDirectory=$APP_DIR
Environment="PATH=$VENV_PATH/bin"
ExecStart=$VENV_PATH/bin/gunicorn --config gunicorn.conf.py wsgi:app
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

    # Create Celery worker service
    print_info "Creating wegweiser-celery.service..."
    cat > /etc/systemd/system/wegweiser-celery.service << EOF
[Unit]
Description=Wegweiser Celery Worker
After=network.target redis.service

[Service]
Type=forking
User=www-data
Group=www-data
WorkingDirectory=$APP_DIR
Environment="PATH=$VENV_PATH/bin"
ExecStart=$VENV_PATH/bin/celery -A app.celery worker --loglevel=info --detach
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

    # Create Celery beat service
    print_info "Creating wegweiser-celery-beat.service..."
    cat > /etc/systemd/system/wegweiser-celery-beat.service << EOF
[Unit]
Description=Wegweiser Celery Beat Scheduler
After=network.target redis.service

[Service]
Type=simple
User=www-data
Group=www-data
WorkingDirectory=$APP_DIR
Environment="PATH=$VENV_PATH/bin"
ExecStart=$VENV_PATH/bin/celery -A app.celery beat --loglevel=info
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

    systemctl daemon-reload
    print_status "Systemd services created"

    step_complete "$CURRENT_STEP"
else
    print_info "Skipping completed step: Systemd services"
fi

show_progress
echo ""

# ============================================================================
# STEP 11: SET PERMISSIONS
# ============================================================================

CURRENT_STEP="permissions"
if ! is_step_completed "$CURRENT_STEP"; then
    step_start "$CURRENT_STEP" "Setting file permissions"
    print_header "Step 11: File Permissions"

    print_info "Setting ownership..."
    chown -R www-data:www-data "$APP_DIR"

    print_info "Securing sensitive files..."
    chmod 600 .env
    chmod 755 venv/bin/*

    print_status "Permissions configured"
    step_complete "$CURRENT_STEP"
else
    print_info "Skipping completed step: File permissions"
fi

show_progress
echo ""

# ============================================================================
# STEP 12: FINAL VERIFICATION
# ============================================================================

CURRENT_STEP="verification"
if ! is_step_completed "$CURRENT_STEP"; then
    step_start "$CURRENT_STEP" "Running final verification"
    print_header "Step 12: Final Verification"

    if [ -f "verify-setup.sh" ]; then
        print_info "Running verification script..."
        if bash verify-setup.sh; then
            print_status "Verification passed!"
        else
            print_warning "Verification found issues - review output above"
        fi
    else
        print_warning "verify-setup.sh not found - skipping verification"
    fi

    step_complete "$CURRENT_STEP"
else
    print_info "Skipping completed step: Final verification"
fi

show_progress
echo ""

# ============================================================================
# INSTALLATION COMPLETE
# ============================================================================

install_complete

print_header "Installation Complete!"
echo ""
print_status "Wegweiser has been successfully installed!"
echo ""

# Show final status
show_status
echo ""

# Cleanup old backups
cleanup_backups

print_header "Next Steps"
echo ""
echo "1. ${BOLD}Review Configuration:${NC}"
echo "   nano .env"
echo ""
echo "2. ${BOLD}Start Services:${NC}"
echo "   systemctl start wegweiser"
echo "   systemctl start wegweiser-celery"
echo "   systemctl start wegweiser-celery-beat"
echo ""
echo "3. ${BOLD}Enable Auto-start:${NC}"
echo "   systemctl enable wegweiser"
echo "   systemctl enable wegweiser-celery"
echo "   systemctl enable wegweiser-celery-beat"
echo ""
echo "4. ${BOLD}Check Status:${NC}"
echo "   systemctl status wegweiser"
echo "   journalctl -u wegweiser -f"
echo ""
echo "5. ${BOLD}Access Application:${NC}"
echo "   http://localhost:5000"
echo ""

print_warning "IMPORTANT SECURITY REMINDERS:"
echo "  • Keep .env file secure (already set to 600)"
echo "  • Never commit secrets to version control"
echo "  • Regularly backup database and secrets"
echo "  • Update system and dependencies regularly"
echo ""

print_status "Installation log saved to: .install-state.json"
echo ""
