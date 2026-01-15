#!/bin/bash

# Filepath: install.sh
# Wegweiser Installation Wizard
# Simple entry point that wraps the enhanced setup.sh with deployment mode selection

set -e

# Text formatting
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color
BOLD='\033[1m'

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

# Banner
print_header "╔════════════════════════════════════════════════════════════╗"
echo "║           Wegweiser Installation Wizard                    ║"
echo "║  AI-Powered Intelligence Layer for MSPs                    ║"
echo "║  https://github.com/creativeheadz/wegweiser               ║"
echo "╚════════════════════════════════════════════════════════════╝"

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    print_error "This installation requires root privileges"
    print_info "Please run with: sudo bash install.sh"
    exit 1
fi

# Check if we're in the right directory
if [ ! -f "wsgi.py" ] || [ ! -d "app" ]; then
    print_error "This script must be run from the Wegweiser root directory"
    print_info "Ensure wsgi.py and app/ directory exist in the current directory"
    exit 1
fi

print_status "Running Wegweiser Installation Wizard"
print_info "Your current directory: $(pwd)"

print_header "Deployment Mode Selection"

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
echo "4) ${BOLD}Hybrid (Custom)${NC}"
echo "   - Choose your own configuration"
echo "   - Maximum flexibility"
echo ""

read -p "Select deployment mode (1-4): " mode

case $mode in
    1)
        print_header "Development Mode Setup"
        print_info "Configuration: Local .env with PostgreSQL"
        export LOCAL_DEPLOYMENT=true
        ;;
    2)
        print_header "Production (Self-Hosted) Setup"
        print_info "Configuration: OpenBao secrets with PostgreSQL"
        export LOCAL_DEPLOYMENT=true
        export SETUP_MODE="production-self-hosted"
        ;;
    3)
        print_header "Production (Azure) Setup"
        print_info "Configuration: Azure Key Vault with Azure Database"
        export LOCAL_DEPLOYMENT=true
        export SETUP_MODE="production-azure"
        ;;
    4)
        print_header "Custom Hybrid Setup"
        print_info "Configuration: You'll choose each component"
        export LOCAL_DEPLOYMENT=true
        export SETUP_MODE="custom"
        ;;
    *)
        print_error "Invalid selection"
        exit 1
        ;;
esac

print_header "Pre-Flight Checks"

# Check required commands
required_commands=("git" "python3" "bash" "curl" "wget")
missing_commands=()

for cmd in "${required_commands[@]}"; do
    if ! command -v "$cmd" &> /dev/null; then
        missing_commands+=("$cmd")
    fi
done

if [ ${#missing_commands[@]} -gt 0 ]; then
    print_error "Missing required commands: ${missing_commands[*]}"
    print_info "Please install them before running this installer"
    exit 1
fi

print_status "All required commands available"

# Check system resources
print_info "Checking system resources..."
available_memory=$(free -m | awk '/^Mem:/{print $7}')
required_memory=1024

if [ "$available_memory" -lt "$required_memory" ]; then
    print_warning "Low memory available (${available_memory}MB, recommended: ${required_memory}MB)"
    read -p "Continue anyway? (yes/no): " continue_low_memory
    if [ "$continue_low_memory" != "yes" ]; then
        exit 1
    fi
fi

print_status "System resources check passed"

# Check disk space
available_disk=$(df -m . | awk 'NR==2{print $4}')
required_disk=5000

if [ "$available_disk" -lt "$required_disk" ]; then
    print_error "Insufficient disk space (${available_disk}MB available, ${required_disk}MB required)"
    exit 1
fi

print_status "Disk space check passed (${available_disk}MB available)"

print_header "Configuration Summary"

echo "Deployment Mode: "
case $mode in
    1) echo "  Development with local .env" ;;
    2) echo "  Production with OpenBao" ;;
    3) echo "  Production with Azure" ;;
    4) echo "  Custom hybrid setup" ;;
esac

echo ""
echo "The following will be configured:"
echo "  ✓ System dependencies"
echo "  ✓ PostgreSQL database"
echo "  ✓ Redis cache and session storage"
echo "  ✓ Python virtual environment"
echo "  ✓ Application dependencies"
echo "  ✓ Database migrations"
echo "  ✓ Systemd services (Flask, Celery)"
echo "  ✓ AI provider configuration"
echo "  ✓ Secret storage backend"

echo ""
read -p "Ready to proceed with installation? (yes/no): " confirm

if [ "$confirm" != "yes" ]; then
    print_info "Installation cancelled"
    exit 0
fi

# Check if setup.sh exists
if [ ! -f "app/setup.sh" ]; then
    print_error "setup.sh not found at app/setup.sh"
    exit 1
fi

print_header "Starting Installation Process"

# Run the setup script with appropriate flags
if [ "$SETUP_MODE" == "production-azure" ]; then
    print_info "Running setup in Azure mode..."
    # Will be handled by the interactive prompts in setup.sh
fi

# Make setup.sh executable
chmod +x app/setup.sh

# Run the setup script
print_info "Executing app/setup.sh..."
bash app/setup.sh "$@"

installation_status=$?

if [ $installation_status -eq 0 ]; then
    print_header "Installation Complete!"
    print_status "Wegweiser has been successfully installed"

    echo ""
    print_info "Next steps:"
    echo "  1. Review the .env file for any missing or incorrect values"
    echo "  2. Start the services:"
    echo "     systemctl start wegweiser"
    echo "     systemctl start wegweiser-celery"
    echo "  3. Check the logs:"
    echo "     journalctl -u wegweiser -f"
    echo "     journalctl -u wegweiser-celery -f"
    echo ""
    echo "  4. Access the application at: http://localhost:5000"
    echo ""
    print_warning "IMPORTANT SECURITY NOTES:"
    echo "  - Secure your .env file: chmod 600 .env"
    echo "  - Never commit secrets to version control"
    echo "  - For production, use a proper secrets management system"
    echo "  - Regularly backup your database and secrets"
    echo ""
else
    print_error "Installation failed with status code $installation_status"
    exit $installation_status
fi
