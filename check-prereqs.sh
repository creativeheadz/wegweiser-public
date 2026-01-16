#!/bin/bash

# Filepath: check-prereqs.sh
# Wegweiser Pre-Flight Checker
# Validates all prerequisites before installation begins
# Run this BEFORE install.sh to ensure a smooth installation experience

# Enable color support for terminals
export TERM=${TERM:-xterm-256color}
set -e

# Text formatting
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
MAGENTA='\033[0;35m'
NC='\033[0m' # No Color
BOLD='\033[1m'
DIM='\033[2m'

# Check counters
CHECKS_PASSED=0
CHECKS_FAILED=0
CHECKS_WARNING=0
CHECKS_TOTAL=0

# Requirements tracking
CRITICAL_FAILURES=()
WARNINGS=()
RECOMMENDATIONS=()

print_status() {
    echo -e "${GREEN}[✓]${NC} $1"
    CHECKS_PASSED=$((CHECKS_PASSED + 1))
}

print_error() {
    echo -e "${RED}[✗]${NC} $1"
    CHECKS_FAILED=$((CHECKS_FAILED + 1))
    CRITICAL_FAILURES+=("$1")
}

print_warning() {
    echo -e "${YELLOW}[!]${NC} $1"
    CHECKS_WARNING=$((CHECKS_WARNING + 1))
    WARNINGS+=("$1")
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

print_recommendation() {
    RECOMMENDATIONS+=("$1")
}

# Banner
clear
echo -e "${BOLD}${MAGENTA}"
cat << "EOF"
╔════════════════════════════════════════════════════════════╗
║                                                            ║
║        Wegweiser Pre-Flight System Checker                ║
║        AI-Powered Intelligence Layer for MSPs              ║
║                                                            ║
║        Validating prerequisites before installation...     ║
║                                                            ║
╚════════════════════════════════════════════════════════════╝
EOF
echo -e "${NC}\n"

print_info "This checker will validate your system before installation"
print_info "Estimated check time: 30-60 seconds"
echo ""

# ============================================================================
# SYSTEM INFORMATION
# ============================================================================

print_header "System Information"

CHECKS_TOTAL=$((CHECKS_TOTAL + 1))
if [[ "$OSTYPE" == "linux-gnu"* ]]; then
    OS_NAME=$(lsb_release -si 2>/dev/null || cat /etc/os-release | grep ^ID= | cut -d= -f2 | tr -d '"')
    OS_VERSION=$(lsb_release -sr 2>/dev/null || cat /etc/os-release | grep VERSION_ID | cut -d= -f2 | tr -d '"')

    # Check if it's Ubuntu (recommended)
    if [[ "$OS_NAME" == "Ubuntu" ]]; then
        # Check Ubuntu version
        UBUNTU_MAJOR=$(echo $OS_VERSION | cut -d. -f1)
        if [ "$UBUNTU_MAJOR" -ge 20 ]; then
            print_status "Operating System: Ubuntu $OS_VERSION (Recommended ✓)"
        elif [ "$UBUNTU_MAJOR" -ge 18 ]; then
            print_warning "Operating System: Ubuntu $OS_VERSION (Supported but 20.04+ recommended)"
        else
            print_error "Operating System: Ubuntu $OS_VERSION (Too old - minimum 18.04)"
            print_info "Wegweiser requires Ubuntu 20.04 LTS or newer"
        fi
    elif [[ "$OS_NAME" =~ ^(Debian|LinuxMint)$ ]]; then
        print_status "Operating System: $OS_NAME $OS_VERSION (Debian-based, should work)"
    elif [[ "$OS_NAME" =~ ^(CentOS|RedHat|Rocky|AlmaLinux)$ ]]; then
        print_warning "Operating System: $OS_NAME $OS_VERSION (RHEL-based - some commands may differ)"
        print_recommendation "Ubuntu 20.04+ is the recommended platform"
    else
        print_warning "Operating System: $OS_NAME $OS_VERSION (Not tested - Ubuntu recommended)"
        print_recommendation "Wegweiser is primarily tested on Ubuntu 20.04 LTS and newer"
    fi

    # Check if running under WSL
    if grep -qi microsoft /proc/version 2>/dev/null; then
        print_info "Detected: WSL (Windows Subsystem for Linux)"
        print_recommendation "For production, use native Ubuntu server instead of WSL"
    fi
elif [[ "$OSTYPE" == "darwin"* ]]; then
    OS_VERSION=$(sw_vers -productVersion)
    print_warning "Operating System: macOS $OS_VERSION (Development only)"
    print_recommendation "For production deployment, use Ubuntu 20.04+ server"
else
    print_error "Unsupported operating system: $OSTYPE"
    print_info "Wegweiser requires Ubuntu 20.04+ (recommended) or compatible Linux distribution"
    exit 1
fi

CHECKS_TOTAL=$((CHECKS_TOTAL + 1))
ARCHITECTURE=$(uname -m)
if [[ "$ARCHITECTURE" == "x86_64" ]] || [[ "$ARCHITECTURE" == "amd64" ]]; then
    print_status "Architecture: $ARCHITECTURE (64-bit)"
elif [[ "$ARCHITECTURE" == "arm64" ]] || [[ "$ARCHITECTURE" == "aarch64" ]]; then
    print_status "Architecture: $ARCHITECTURE (ARM 64-bit)"
else
    print_warning "Architecture: $ARCHITECTURE (not tested, may have issues)"
fi

# ============================================================================
# USER PERMISSIONS
# ============================================================================

print_header "User Permissions"

CHECKS_TOTAL=$((CHECKS_TOTAL + 1))
if [ "$EUID" -eq 0 ]; then
    print_status "Running as root (required for installation)"
else
    print_error "Not running as root"
    print_info "Installation requires root privileges. Run with: sudo bash check-prereqs.sh"
fi

CHECKS_TOTAL=$((CHECKS_TOTAL + 1))
if command -v sudo &> /dev/null; then
    print_status "sudo available"
else
    print_warning "sudo not found - may be needed for service management"
fi

# ============================================================================
# SYSTEM RESOURCES
# ============================================================================

print_header "System Resources"

# Memory check
CHECKS_TOTAL=$((CHECKS_TOTAL + 1))
if command -v free &> /dev/null; then
    TOTAL_MEMORY=$(free -m | awk '/^Mem:/{print $2}')
    AVAILABLE_MEMORY=$(free -m | awk '/^Mem:/{print $7}')

    if [ "$TOTAL_MEMORY" -ge 8192 ]; then
        print_status "Total Memory: ${TOTAL_MEMORY}MB (Excellent)"
    elif [ "$TOTAL_MEMORY" -ge 4096 ]; then
        print_status "Total Memory: ${TOTAL_MEMORY}MB (Good, meets minimum)"
    elif [ "$TOTAL_MEMORY" -ge 2048 ]; then
        print_warning "Total Memory: ${TOTAL_MEMORY}MB (Below recommended 4GB)"
        print_recommendation "Consider upgrading to at least 4GB RAM for better performance"
    else
        print_error "Total Memory: ${TOTAL_MEMORY}MB (Insufficient - minimum 2GB required)"
    fi

    CHECKS_TOTAL=$((CHECKS_TOTAL + 1))
    if [ "$AVAILABLE_MEMORY" -ge 1024 ]; then
        print_status "Available Memory: ${AVAILABLE_MEMORY}MB"
    else
        print_warning "Available Memory: ${AVAILABLE_MEMORY}MB (Low - close other applications)"
    fi
else
    print_warning "Cannot check memory (free command not available)"
fi

# Disk space check
CHECKS_TOTAL=$((CHECKS_TOTAL + 1))
AVAILABLE_DISK=$(df -BM . | awk 'NR==2{print $4}' | sed 's/M//')
REQUIRED_DISK=20480  # 20GB in MB

if [ "$AVAILABLE_DISK" -ge 51200 ]; then
    print_status "Available Disk Space: ${AVAILABLE_DISK}MB (Excellent)"
elif [ "$AVAILABLE_DISK" -ge "$REQUIRED_DISK" ]; then
    print_status "Available Disk Space: ${AVAILABLE_DISK}MB (Sufficient)"
elif [ "$AVAILABLE_DISK" -ge 10240 ]; then
    print_warning "Available Disk Space: ${AVAILABLE_DISK}MB (Below recommended 20GB)"
    print_recommendation "Free up disk space or expand storage - logs and data can grow quickly"
else
    print_error "Available Disk Space: ${AVAILABLE_DISK}MB (Insufficient - minimum 10GB required)"
fi

# CPU check
CHECKS_TOTAL=$((CHECKS_TOTAL + 1))
if command -v nproc &> /dev/null; then
    CPU_CORES=$(nproc)
    if [ "$CPU_CORES" -ge 4 ]; then
        print_status "CPU Cores: $CPU_CORES (Excellent)"
    elif [ "$CPU_CORES" -ge 2 ]; then
        print_status "CPU Cores: $CPU_CORES (Sufficient)"
    else
        print_warning "CPU Cores: $CPU_CORES (Single core - performance may be limited)"
    fi
else
    print_info "Cannot determine CPU core count"
fi

# ============================================================================
# REQUIRED COMMANDS
# ============================================================================

print_header "Required Commands & Tools"

check_command() {
    local cmd=$1
    local display_name=$2
    local install_hint=$3
    local required=$4  # "required" or "optional"

    CHECKS_TOTAL=$((CHECKS_TOTAL + 1))
    if command -v "$cmd" &> /dev/null; then
        local version=""
        case $cmd in
            python3)
                version=$($cmd --version 2>&1 | awk '{print $2}')
                ;;
            git|curl|wget|psql|redis-cli)
                version=$($cmd --version 2>&1 | head -n1 | grep -oE '[0-9]+\.[0-9]+(\.[0-9]+)?' | head -n1)
                ;;
        esac

        if [ -n "$version" ]; then
            print_status "$display_name: $version"
        else
            print_status "$display_name: installed"
        fi
        return 0
    else
        if [ "$required" == "required" ]; then
            print_error "$display_name: not found"
            print_info "  Install: $install_hint"
        else
            print_warning "$display_name: not found (optional)"
            print_info "  Install: $install_hint"
        fi
        return 1
    fi
}

print_section "Core Tools"
check_command "git" "Git" "apt-get install git" "required"
check_command "curl" "curl" "apt-get install curl" "required"
check_command "wget" "wget" "apt-get install wget" "required"
check_command "bash" "Bash" "Should be pre-installed" "required"

print_section "Python Environment"
if check_command "python3" "Python 3" "apt-get install python3" "required"; then
    PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
    PYTHON_MAJOR=$(echo $PYTHON_VERSION | cut -d. -f1)
    PYTHON_MINOR=$(echo $PYTHON_VERSION | cut -d. -f2)

    CHECKS_TOTAL=$((CHECKS_TOTAL + 1))
    if [ "$PYTHON_MAJOR" -eq 3 ] && [ "$PYTHON_MINOR" -ge 9 ]; then
        print_status "Python version $PYTHON_VERSION is compatible (3.9+ required)"
    else
        print_error "Python version $PYTHON_VERSION is too old (3.9+ required)"
        print_recommendation "Upgrade Python to 3.9 or higher"
    fi
fi

check_command "pip3" "pip3" "apt-get install python3-pip" "required"
check_command "python3-venv" "venv module" "apt-get install python3-venv" "required" || \
    python3 -m venv --help &>/dev/null && print_status "venv module: available"

print_section "Build Tools"
if [[ "$OSTYPE" == "linux-gnu"* ]]; then
    check_command "gcc" "GCC Compiler" "apt-get install build-essential" "required"
    check_command "make" "Make" "apt-get install build-essential" "required"
fi

# ============================================================================
# DATABASE - POSTGRESQL
# ============================================================================

print_header "PostgreSQL Database"

print_section "PostgreSQL Installation"
CHECKS_TOTAL=$((CHECKS_TOTAL + 1))
if command -v psql &> /dev/null; then
    PG_VERSION=$(psql --version | awk '{print $3}' | cut -d. -f1)
    if [ "$PG_VERSION" -ge 12 ]; then
        print_status "PostgreSQL $PG_VERSION installed (12+ required)"
    else
        print_warning "PostgreSQL $PG_VERSION installed (version 12+ recommended)"
    fi

    # Check if PostgreSQL service is running
    CHECKS_TOTAL=$((CHECKS_TOTAL + 1))
    if systemctl is-active --quiet postgresql 2>/dev/null || pgrep -x postgres > /dev/null 2>&1; then
        print_status "PostgreSQL service is running"

        # Try to connect
        CHECKS_TOTAL=$((CHECKS_TOTAL + 1))
        if sudo -u postgres psql -c "SELECT version();" &>/dev/null; then
            print_status "PostgreSQL connection test: successful"

            # Check for existing wegweiser database
            CHECKS_TOTAL=$((CHECKS_TOTAL + 1))
            if sudo -u postgres psql -lqt | cut -d \| -f 1 | grep -qw "wegweiser"; then
                print_warning "Database 'wegweiser' already exists"
                print_info "  Existing database will be used (backup recommended before proceeding)"
            else
                print_info "Database 'wegweiser' does not exist (will be created during installation)"
            fi
        else
            print_warning "Cannot connect to PostgreSQL (may need configuration)"
            print_recommendation "Ensure PostgreSQL accepts local connections"
        fi
    else
        print_error "PostgreSQL service is not running"
        print_info "  Start with: sudo systemctl start postgresql"
    fi
else
    print_error "PostgreSQL not installed"
    print_info "  Install: sudo apt-get install postgresql postgresql-contrib"
    print_recommendation "PostgreSQL 14+ is recommended for best compatibility"
fi

# ============================================================================
# CACHE - REDIS
# ============================================================================

print_header "Redis Cache Server"

print_section "Redis Installation"
CHECKS_TOTAL=$((CHECKS_TOTAL + 1))
if command -v redis-cli &> /dev/null; then
    REDIS_VERSION=$(redis-cli --version | grep -oE '[0-9]+\.[0-9]+\.[0-9]+' | head -n1)
    print_status "Redis CLI installed: $REDIS_VERSION"

    # Check if Redis service is running
    CHECKS_TOTAL=$((CHECKS_TOTAL + 1))
    if systemctl is-active --quiet redis 2>/dev/null || systemctl is-active --quiet redis-server 2>/dev/null || pgrep -x redis-server > /dev/null 2>&1; then
        print_status "Redis service is running"

        # Try to connect
        CHECKS_TOTAL=$((CHECKS_TOTAL + 1))
        if redis-cli ping &>/dev/null | grep -q PONG; then
            print_status "Redis connection test: successful"
        else
            print_warning "Cannot connect to Redis on default port (6379)"
            print_info "  Check if Redis is configured to accept connections"
        fi
    else
        print_error "Redis service is not running"
        print_info "  Start with: sudo systemctl start redis-server"
    fi
else
    print_error "Redis not installed"
    print_info "  Install: sudo apt-get install redis-server"
fi

# ============================================================================
# MESSAGING - NATS (OPTIONAL BUT RECOMMENDED)
# ============================================================================

print_header "NATS Messaging Server (for Agent Communication)"

CHECKS_TOTAL=$((CHECKS_TOTAL + 1))
if command -v nats-server &> /dev/null; then
    print_status "NATS server installed"

    CHECKS_TOTAL=$((CHECKS_TOTAL + 1))
    if pgrep -x nats-server > /dev/null 2>&1; then
        print_status "NATS server is running"
    else
        print_warning "NATS server is not running"
        print_info "  Start manually or it will be configured during installation"
    fi
else
    print_warning "NATS server not installed (optional - needed for agent communication)"
    print_recommendation "Install NATS for full functionality: https://docs.nats.io/running-a-nats-service/introduction/installation"
fi

# ============================================================================
# NETWORK CONNECTIVITY
# ============================================================================

print_header "Network Connectivity"

print_section "Internet Connection"
CHECKS_TOTAL=$((CHECKS_TOTAL + 1))
if ping -c 1 8.8.8.8 &> /dev/null; then
    print_status "Internet connectivity: available"
else
    print_error "No internet connection detected"
    print_info "  Internet required for downloading Python packages"
fi

print_section "External Services"
CHECKS_TOTAL=$((CHECKS_TOTAL + 1))
if curl -s --head --max-time 5 https://pypi.org | head -n 1 | grep -q 200; then
    print_status "PyPI (Python Package Index): reachable"
else
    print_warning "Cannot reach PyPI - package installation may fail"
fi

CHECKS_TOTAL=$((CHECKS_TOTAL + 1))
if curl -s --head --max-time 5 https://github.com | head -n 1 | grep -q 200; then
    print_status "GitHub: reachable"
else
    print_warning "Cannot reach GitHub - may affect git operations"
fi

# ============================================================================
# PORT AVAILABILITY
# ============================================================================

print_header "Port Availability"

check_port() {
    local port=$1
    local service=$2

    CHECKS_TOTAL=$((CHECKS_TOTAL + 1))
    if command -v netstat &> /dev/null; then
        if netstat -tuln | grep -q ":$port "; then
            print_info "Port $port ($service): in use"
        else
            print_status "Port $port ($service): available"
        fi
    elif command -v ss &> /dev/null; then
        if ss -tuln | grep -q ":$port "; then
            print_info "Port $port ($service): in use"
        else
            print_status "Port $port ($service): available"
        fi
    else
        print_info "Port $port ($service): cannot check (netstat/ss not available)"
    fi
}

check_port 5000 "Flask default"
check_port 5432 "PostgreSQL"
check_port 6379 "Redis"
check_port 4222 "NATS"

# ============================================================================
# PYTHON DEPENDENCIES PREVIEW
# ============================================================================

print_header "Python Dependencies Check"

CHECKS_TOTAL=$((CHECKS_TOTAL + 1))
if [ -f "requirements.txt" ]; then
    PACKAGE_COUNT=$(grep -v "^#" requirements.txt | grep -v "^$" | wc -l)
    print_status "requirements.txt found ($PACKAGE_COUNT packages)"

    CHECKS_TOTAL=$((CHECKS_TOTAL + 1))
    if command -v pip3 &> /dev/null; then
        print_info "Checking for common package dependencies..."

        # Check for development headers needed by some packages
        if [[ "$OSTYPE" == "linux-gnu"* ]]; then
            MISSING_DEV_PACKAGES=()

            if ! dpkg -l | grep -q python3-dev; then
                MISSING_DEV_PACKAGES+=("python3-dev")
            fi

            if ! dpkg -l | grep -q libpq-dev; then
                MISSING_DEV_PACKAGES+=("libpq-dev")
            fi

            if ! dpkg -l | grep -q libssl-dev; then
                MISSING_DEV_PACKAGES+=("libssl-dev")
            fi

            if ! dpkg -l | grep -q libffi-dev; then
                MISSING_DEV_PACKAGES+=("libffi-dev")
            fi

            if [ ${#MISSING_DEV_PACKAGES[@]} -gt 0 ]; then
                print_warning "Missing development packages: ${MISSING_DEV_PACKAGES[*]}"
                print_info "  Install: sudo apt-get install ${MISSING_DEV_PACKAGES[*]}"
            else
                print_status "All common development packages installed"
            fi
        fi
    fi
else
    print_error "requirements.txt not found - are you in the correct directory?"
fi

# ============================================================================
# DIRECTORY STRUCTURE
# ============================================================================

print_header "Project Structure"

check_file() {
    local file=$1
    local description=$2

    CHECKS_TOTAL=$((CHECKS_TOTAL + 1))
    if [ -e "$file" ]; then
        print_status "$description: found"
        return 0
    else
        print_error "$description: missing"
        return 1
    fi
}

check_file "wsgi.py" "WSGI entry point"
check_file "requirements.txt" "Requirements file"
check_file "app/__init__.py" "App module"
check_file "install.sh" "Installation script"
check_file ".env.example" "Environment template"

CHECKS_TOTAL=$((CHECKS_TOTAL + 1))
if [ -f ".env" ]; then
    print_warning ".env file already exists (will be used/updated)"
else
    print_info ".env file not found (will be created during installation)"
fi

# ============================================================================
# SECURITY CHECKS
# ============================================================================

print_header "Security Considerations"

CHECKS_TOTAL=$((CHECKS_TOTAL + 1))
if [ -f ".env" ]; then
    ENV_PERMS=$(stat -c %a .env 2>/dev/null || stat -f %A .env 2>/dev/null)
    if [ "$ENV_PERMS" == "600" ] || [ "$ENV_PERMS" == "400" ]; then
        print_status ".env file permissions: secure ($ENV_PERMS)"
    else
        print_warning ".env file permissions: $ENV_PERMS (should be 600)"
        print_recommendation "After installation, run: chmod 600 .env"
    fi
fi

CHECKS_TOTAL=$((CHECKS_TOTAL + 1))
if command -v ufw &> /dev/null; then
    if ufw status | grep -q "Status: active"; then
        print_status "Firewall (ufw): active"
        print_recommendation "Ensure required ports are allowed through firewall"
    else
        print_info "Firewall (ufw): inactive"
    fi
else
    print_info "UFW firewall not installed (optional)"
fi

# ============================================================================
# FINAL SUMMARY
# ============================================================================

print_header "Pre-Flight Check Summary"

echo -e "${BOLD}Total Checks Run:${NC} $CHECKS_TOTAL"
echo -e "${GREEN}${BOLD}Passed:${NC} $CHECKS_PASSED"
echo -e "${RED}${BOLD}Failed:${NC} $CHECKS_FAILED"
echo -e "${YELLOW}${BOLD}Warnings:${NC} $CHECKS_WARNING"
echo ""

# Calculate readiness score
READINESS_SCORE=$((CHECKS_PASSED * 100 / CHECKS_TOTAL))

echo -e "${BOLD}System Readiness:${NC} ${READINESS_SCORE}%"
echo ""

# Show critical failures
if [ ${#CRITICAL_FAILURES[@]} -gt 0 ]; then
    echo -e "${RED}${BOLD}Critical Issues (Must Fix):${NC}"
    for failure in "${CRITICAL_FAILURES[@]}"; do
        echo -e "  ${RED}•${NC} $failure"
    done
    echo ""
fi

# Show warnings
if [ ${#WARNINGS[@]} -gt 0 ]; then
    echo -e "${YELLOW}${BOLD}Warnings (Review Recommended):${NC}"
    for warning in "${WARNINGS[@]}"; do
        echo -e "  ${YELLOW}•${NC} $warning"
    done
    echo ""
fi

# Show recommendations
if [ ${#RECOMMENDATIONS[@]} -gt 0 ]; then
    echo -e "${CYAN}${BOLD}Recommendations:${NC}"
    for rec in "${RECOMMENDATIONS[@]}"; do
        echo -e "  ${CYAN}•${NC} $rec"
    done
    echo ""
fi

# Final verdict
echo -e "${BOLD}═══════════════════════════════════════════════════════════${NC}"
if [ "$CHECKS_FAILED" -eq 0 ]; then
    echo -e "${GREEN}${BOLD}✓ System is ready for installation!${NC}"
    echo ""
    echo -e "Next steps:"
    echo -e "  1. Review any warnings above"
    echo -e "  2. Run: ${BOLD}sudo bash install.sh${NC}"
    echo -e "  3. Follow the installation wizard"
    echo ""
    exit 0
elif [ "$READINESS_SCORE" -ge 80 ]; then
    echo -e "${YELLOW}${BOLD}⚠ System is mostly ready, but has some issues${NC}"
    echo ""
    echo -e "You can proceed with installation, but fix critical issues first."
    echo -e "Run: ${BOLD}sudo bash install.sh${NC} when ready"
    echo ""
    exit 1
else
    echo -e "${RED}${BOLD}✗ System is not ready for installation${NC}"
    echo ""
    echo -e "Please fix the critical issues listed above before proceeding."
    echo -e "Re-run this checker after making fixes: ${BOLD}sudo bash check-prereqs.sh${NC}"
    echo ""
    exit 2
fi
