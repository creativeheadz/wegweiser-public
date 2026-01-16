#!/bin/bash

# Filepath: verify-setup-enhanced.sh
# Wegweiser Enhanced Setup Verification
# Performs actual functional tests, not just file checks

set -e
# Enable color support for terminals
export TERM=${TERM:-xterm-256color}

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
MAGENTA='\033[0;35m'
NC='\033[0m'
BOLD='\033[1m'
DIM='\033[2m'

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
    echo -e "\n${BOLD}▶ $1${NC}"
}

errors=0
warnings=0
tests_passed=0
tests_failed=0

# Banner
clear
echo -e "${BOLD}${MAGENTA}"
cat << "EOF"
╔════════════════════════════════════════════════════════════╗
║                                                            ║
║        Wegweiser Enhanced Verification Suite              ║
║        Functional Testing & Health Checks                 ║
║                                                            ║
╚════════════════════════════════════════════════════════════╝
EOF
echo -e "${NC}\n"

print_info "Running comprehensive verification tests..."
echo ""

# ============================================================================
# FILE STRUCTURE TESTS
# ============================================================================

print_header "File Structure Verification"

check_file() {
    local file=$1
    local description=$2

    if [ -e "$file" ]; then
        print_status "$description: found"
        tests_passed=$((tests_passed + 1))
        return 0
    else
        print_error "$description: missing"
        tests_failed=$((tests_failed + 1))
        errors=$((errors + 1))
        return 1
    fi
}

check_file "wsgi.py" "WSGI entry point"
check_file "requirements.txt" "Requirements file"
check_file "app/__init__.py" "App module"
check_file ".env" "Environment configuration"
check_file "venv/bin/python" "Python virtual environment"
check_file "venv/bin/pip" "Pip in virtual environment"

# ============================================================================
# CONFIGURATION FILE TESTS
# ============================================================================

print_header "Configuration Verification"

if [ -f ".env" ]; then
    print_section "Environment Variables"

    check_env_var() {
        local var_name=$1
        local required=$2

        if grep -q "^${var_name}=" .env 2>/dev/null; then
            local value=$(grep "^${var_name}=" .env | cut -d= -f2-)

            # Check if value is not a placeholder
            if [[ "$value" =~ (change-this|your-|example|REPLACE) ]]; then
                if [ "$required" == "required" ]; then
                    print_warning "$var_name: still has placeholder value"
                    warnings=$((warnings + 1))
                    tests_failed=$((tests_failed + 1))
                else
                    print_info "$var_name: placeholder value (optional)"
                    tests_passed=$((tests_passed + 1))
                fi
            else
                print_status "$var_name: configured"
                tests_passed=$((tests_passed + 1))
            fi
            return 0
        else
            if [ "$required" == "required" ]; then
                print_error "$var_name: missing"
                errors=$((errors + 1))
                tests_failed=$((tests_failed + 1))
            else
                print_info "$var_name: not set (optional)"
                tests_passed=$((tests_passed + 1))
            fi
            return 1
        fi
    }

    # Required variables
    check_env_var "DATABASE_URL" "required"
    check_env_var "SQLALCHEMY_DATABASE_URI" "required"
    check_env_var "SECRET_KEY" "required"
    check_env_var "API_KEY" "required"
    check_env_var "REDIS_HOST" "required"

    # Optional but recommended
    check_env_var "AI_PROVIDER" "optional"
    check_env_var "MAIL_SERVER" "optional"

    # Check .env permissions
    print_section "File Security"
    ENV_PERMS=$(stat -c %a .env 2>/dev/null || stat -f %A .env 2>/dev/null)
    if [ "$ENV_PERMS" == "600" ] || [ "$ENV_PERMS" == "400" ]; then
        print_status ".env permissions: $ENV_PERMS (secure)"
        tests_passed=$((tests_passed + 1))
    else
        print_warning ".env permissions: $ENV_PERMS (should be 600)"
        warnings=$((warnings + 1))
        tests_failed=$((tests_failed + 1))
        print_info "  Fix with: chmod 600 .env"
    fi
else
    print_error ".env file not found"
    errors=$((errors + 1))
    tests_failed=$((tests_failed + 1))
fi

# ============================================================================
# PYTHON ENVIRONMENT TESTS
# ============================================================================

print_header "Python Environment Verification"

print_section "Python Version"
if [ -f "venv/bin/python" ]; then
    PYTHON_VERSION=$(venv/bin/python --version 2>&1 | awk '{print $2}')
    PYTHON_MAJOR=$(echo $PYTHON_VERSION | cut -d. -f1)
    PYTHON_MINOR=$(echo $PYTHON_VERSION | cut -d. -f2)

    if [ "$PYTHON_MAJOR" -eq 3 ] && [ "$PYTHON_MINOR" -ge 9 ]; then
        print_status "Python version: $PYTHON_VERSION (compatible)"
        tests_passed=$((tests_passed + 1))
    else
        print_error "Python version: $PYTHON_VERSION (need 3.9+)"
        errors=$((errors + 1))
        tests_failed=$((tests_failed + 1))
    fi
else
    print_error "Virtual environment Python not found"
    errors=$((errors + 1))
    tests_failed=$((tests_failed + 1))
fi

print_section "Python Packages"
if [ -f "venv/bin/pip" ]; then
    # Check critical packages
    CRITICAL_PACKAGES=("flask" "sqlalchemy" "celery" "redis" "psycopg2")

    for package in "${CRITICAL_PACKAGES[@]}"; do
        if venv/bin/pip show "$package" >/dev/null 2>&1; then
            VERSION=$(venv/bin/pip show "$package" | grep Version | cut -d: -f2 | tr -d ' ')
            print_status "$package: $VERSION installed"
            tests_passed=$((tests_passed + 1))
        else
            print_error "$package: not installed"
            errors=$((errors + 1))
            tests_failed=$((tests_failed + 1))
        fi
    done
else
    print_error "pip not found in virtual environment"
    errors=$((errors + 1))
    tests_failed=$((tests_failed + 1))
fi

# ============================================================================
# DATABASE CONNECTIVITY TESTS
# ============================================================================

print_header "Database Connectivity Tests"

if [ -f ".env" ]; then
    source .env

    print_section "PostgreSQL Connection"

    # Test if we're using SQLite
    if [[ "$DATABASE_URL" == sqlite* ]]; then
        print_info "Using SQLite database"

        # Check if SQLite file exists
        SQLITE_FILE=$(echo "$DATABASE_URL" | sed 's/sqlite:\/\/\///')
        if [ -f "$SQLITE_FILE" ]; then
            print_status "SQLite database file exists: $SQLITE_FILE"
            tests_passed=$((tests_passed + 1))

            # Test if we can query it
            if command -v sqlite3 &> /dev/null; then
                if sqlite3 "$SQLITE_FILE" "SELECT 1;" >/dev/null 2>&1; then
                    print_status "SQLite database is accessible"
                    tests_passed=$((tests_passed + 1))
                else
                    print_error "Cannot query SQLite database"
                    errors=$((errors + 1))
                    tests_failed=$((tests_failed + 1))
                fi
            fi
        else
            print_warning "SQLite database file not created yet"
            print_info "  Will be created on first run"
            tests_passed=$((tests_passed + 1))
        fi
    else
        # PostgreSQL testing
        if command -v psql &> /dev/null; then
            # Extract connection details
            if [ -n "$DB_USER" ] && [ -n "$DB_PASSWORD" ]; then
                export PGPASSWORD="$DB_PASSWORD"

                # Test connection
                if psql -h "${DB_HOST:-localhost}" -p "${DB_PORT:-5432}" -U "$DB_USER" -d "$DB_NAME" -c "SELECT 1;" >/dev/null 2>&1; then
                    print_status "PostgreSQL connection: successful"
                    tests_passed=$((tests_passed + 1))

                    # Test if tables exist
                    TABLE_COUNT=$(psql -h "${DB_HOST:-localhost}" -p "${DB_PORT:-5432}" -U "$DB_USER" -d "$DB_NAME" -t -c "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public';" 2>/dev/null | tr -d ' ')

                    if [ "$TABLE_COUNT" -gt 0 ]; then
                        print_status "Database tables: $TABLE_COUNT tables found"
                        tests_passed=$((tests_passed + 1))
                    else
                        print_warning "No tables found in database"
                        print_info "  Run migrations: flask db upgrade"
                        warnings=$((warnings + 1))
                        tests_failed=$((tests_failed + 1))
                    fi
                else
                    print_error "Cannot connect to PostgreSQL"
                    print_info "  Host: ${DB_HOST:-localhost}:${DB_PORT:-5432}"
                    print_info "  Database: $DB_NAME"
                    print_info "  User: $DB_USER"
                    errors=$((errors + 1))
                    tests_failed=$((tests_failed + 1))
                fi

                unset PGPASSWORD
            else
                print_warning "Database credentials not found in .env"
                warnings=$((warnings + 1))
                tests_failed=$((tests_failed + 1))
            fi
        else
            print_warning "psql not available - cannot test PostgreSQL connection"
            warnings=$((warnings + 1))
            tests_failed=$((tests_failed + 1))
        fi
    fi
fi

# ============================================================================
# REDIS CONNECTIVITY TESTS
# ============================================================================

print_header "Redis Connectivity Tests"

if [ -f ".env" ]; then
    source .env

    print_section "Redis Connection"

    if command -v redis-cli &> /dev/null; then
        # Test Redis connection
        REDIS_HOST=${REDIS_HOST:-localhost}
        REDIS_PORT=${REDIS_PORT:-6379}

        if [ -n "$REDIS_PASSWORD" ]; then
            if redis-cli -h "$REDIS_HOST" -p "$REDIS_PORT" -a "$REDIS_PASSWORD" ping 2>/dev/null | grep -q PONG; then
                print_status "Redis connection: successful (with password)"
                tests_passed=$((tests_passed + 1))
            else
                print_error "Cannot connect to Redis with password"
                errors=$((errors + 1))
                tests_failed=$((tests_failed + 1))
            fi
        else
            if redis-cli -h "$REDIS_HOST" -p "$REDIS_PORT" ping 2>/dev/null | grep -q PONG; then
                print_status "Redis connection: successful"
                tests_passed=$((tests_passed + 1))
            else
                print_error "Cannot connect to Redis"
                print_info "  Host: $REDIS_HOST:$REDIS_PORT"
                errors=$((errors + 1))
                tests_failed=$((tests_failed + 1))
            fi
        fi

        # Test Redis memory info
        REDIS_MEMORY=$(redis-cli -h "$REDIS_HOST" -p "$REDIS_PORT" info memory 2>/dev/null | grep used_memory_human | cut -d: -f2 | tr -d '\r\n')
        if [ -n "$REDIS_MEMORY" ]; then
            print_status "Redis memory usage: $REDIS_MEMORY"
            tests_passed=$((tests_passed + 1))
        fi
    else
        print_warning "redis-cli not available - cannot test Redis connection"
        warnings=$((warnings + 1))
        tests_failed=$((tests_failed + 1))
    fi
fi

# ============================================================================
# FLASK APPLICATION TESTS
# ============================================================================

print_header "Flask Application Tests"

if [ -f "venv/bin/python" ] && [ -f "wsgi.py" ]; then
    print_section "Application Import Test"

    # Test if Flask app can be imported
    if venv/bin/python -c "from app import create_app; app = create_app()" 2>/dev/null; then
        print_status "Flask application: can be imported"
        tests_passed=$((tests_passed + 1))

        # Test Flask commands
        print_section "Flask Commands"

        export FLASK_APP=wsgi.py

        if venv/bin/flask --version >/dev/null 2>&1; then
            FLASK_VERSION=$(venv/bin/flask --version | head -n1)
            print_status "Flask CLI: $FLASK_VERSION"
            tests_passed=$((tests_passed + 1))
        else
            print_error "Flask CLI not working"
            errors=$((errors + 1))
            tests_failed=$((tests_failed + 1))
        fi

        # Check if migrations directory exists
        if [ -d "migrations" ]; then
            print_status "Database migrations: initialized"
            tests_passed=$((tests_passed + 1))
        else
            print_warning "Database migrations: not initialized"
            print_info "  Run: flask db init"
            warnings=$((warnings + 1))
            tests_failed=$((tests_failed + 1))
        fi
    else
        print_error "Cannot import Flask application"
        print_info "  Try: venv/bin/python -c 'from app import create_app; create_app()'"
        errors=$((errors + 1))
        tests_failed=$((tests_failed + 1))
    fi
fi

# ============================================================================
# SYSTEMD SERVICES TESTS
# ============================================================================

print_header "Systemd Services Verification"

check_service() {
    local service_name=$1

    if [ -f "/etc/systemd/system/${service_name}.service" ]; then
        print_status "Service file: $service_name.service exists"
        tests_passed=$((tests_passed + 1))

        # Check if service is enabled
        if systemctl is-enabled "$service_name" >/dev/null 2>&1; then
            print_status "$service_name: enabled"
            tests_passed=$((tests_passed + 1))
        else
            print_info "$service_name: not enabled (optional)"
            tests_passed=$((tests_passed + 1))
        fi

        # Check if service is running
        if systemctl is-active "$service_name" >/dev/null 2>&1; then
            print_status "$service_name: running"
            tests_passed=$((tests_passed + 1))
        else
            print_info "$service_name: not running (start with: systemctl start $service_name)"
            tests_passed=$((tests_passed + 1))
        fi
    else
        print_warning "Service file: $service_name.service not found"
        warnings=$((warnings + 1))
        tests_failed=$((tests_failed + 1))
    fi
}

check_service "wegweiser"
check_service "wegweiser-celery"
check_service "wegweiser-celery-beat"

# ============================================================================
# PORT AVAILABILITY TESTS
# ============================================================================

print_header "Network Port Tests"

check_port() {
    local port=$1
    local service=$2
    local should_be_open=$3

    if command -v ss &> /dev/null; then
        if ss -tuln | grep -q ":$port "; then
            if [ "$should_be_open" == "yes" ]; then
                print_status "Port $port ($service): listening"
                tests_passed=$((tests_passed + 1))
            else
                print_info "Port $port ($service): in use"
                tests_passed=$((tests_passed + 1))
            fi
        else
            if [ "$should_be_open" == "yes" ]; then
                print_warning "Port $port ($service): not listening"
                print_info "  Start the service to open this port"
                warnings=$((warnings + 1))
                tests_failed=$((tests_failed + 1))
            else
                print_status "Port $port ($service): available"
                tests_passed=$((tests_passed + 1))
            fi
        fi
    else
        print_info "Cannot check port $port (ss command not available)"
        tests_passed=$((tests_passed + 1))
    fi
}

# Check if services are running on expected ports
check_port 5432 "PostgreSQL" "yes"
check_port 6379 "Redis" "yes"
check_port 5000 "Flask" "optional"

# ============================================================================
# PERMISSIONS TESTS
# ============================================================================

print_header "File Permissions Verification"

print_section "Critical File Permissions"

# Check app directory ownership
if [ -d "app" ]; then
    APP_OWNER=$(stat -c %U app 2>/dev/null || stat -f %Su app 2>/dev/null)
    APP_GROUP=$(stat -c %G app 2>/dev/null || stat -f %Sg app 2>/dev/null)

    if [ "$APP_OWNER" == "www-data" ] || [ "$APP_OWNER" == "$(whoami)" ]; then
        print_status "App directory owner: $APP_OWNER:$APP_GROUP"
        tests_passed=$((tests_passed + 1))
    else
        print_warning "App directory owner: $APP_OWNER:$APP_GROUP (expected: www-data)"
        warnings=$((warnings + 1))
        tests_failed=$((tests_failed + 1))
    fi
fi

# Check venv permissions
if [ -d "venv" ]; then
    if [ -x "venv/bin/python" ]; then
        print_status "Virtual environment: executable"
        tests_passed=$((tests_passed + 1))
    else
        print_error "Virtual environment: not executable"
        errors=$((errors + 1))
        tests_failed=$((tests_failed + 1))
    fi
fi

# ============================================================================
# FINAL SUMMARY
# ============================================================================

print_header "Verification Summary"

TOTAL_TESTS=$((tests_passed + tests_failed))
if [ $TOTAL_TESTS -gt 0 ]; then
    SUCCESS_RATE=$((tests_passed * 100 / TOTAL_TESTS))
else
    SUCCESS_RATE=0
fi

echo -e "${BOLD}Total Tests:${NC} $TOTAL_TESTS"
echo -e "${GREEN}${BOLD}Passed:${NC} $tests_passed"
echo -e "${RED}${BOLD}Failed:${NC} $tests_failed"
echo -e "${YELLOW}${BOLD}Warnings:${NC} $warnings"
echo -e "${BOLD}Success Rate:${NC} ${SUCCESS_RATE}%"
echo ""

# Visual status bar
if [ $SUCCESS_RATE -ge 90 ]; then
    STATUS_COLOR=$GREEN
    STATUS_TEXT="Excellent"
elif [ $SUCCESS_RATE -ge 75 ]; then
    STATUS_COLOR=$CYAN
    STATUS_TEXT="Good"
elif [ $SUCCESS_RATE -ge 50 ]; then
    STATUS_COLOR=$YELLOW
    STATUS_TEXT="Needs Attention"
else
    STATUS_COLOR=$RED
    STATUS_TEXT="Critical Issues"
fi

echo -e "${BOLD}Overall Status:${NC} ${STATUS_COLOR}${STATUS_TEXT}${NC}"
echo ""

# Recommendations
if [ $errors -gt 0 ] || [ $warnings -gt 0 ]; then
    echo -e "${BOLD}Recommendations:${NC}"

    if [ $errors -gt 0 ]; then
        echo -e "  ${RED}•${NC} Fix critical errors before running application"
    fi

    if [ $warnings -gt 0 ]; then
        echo -e "  ${YELLOW}•${NC} Review warnings for optimal configuration"
    fi

    echo -e "  ${BLUE}•${NC} See TROUBLESHOOTING.md for detailed solutions"
    echo -e "  ${BLUE}•${NC} Run: cat TROUBLESHOOTING.md | less"
    echo ""
fi

# Exit status
echo -e "${BOLD}═══════════════════════════════════════════════════════════${NC}"
if [ $errors -eq 0 ]; then
    echo -e "${GREEN}${BOLD}✓ System verification complete!${NC}"
    echo ""
    if [ $warnings -eq 0 ]; then
        echo "Your Wegweiser installation is fully operational."
    else
        echo "Your Wegweiser installation is operational with minor warnings."
    fi
    echo ""
    exit 0
else
    echo -e "${RED}${BOLD}✗ System verification found critical issues${NC}"
    echo ""
    echo "Please fix the errors listed above before using the application."
    echo "Refer to TROUBLESHOOTING.md for detailed solutions."
    echo ""
    exit 1
fi
