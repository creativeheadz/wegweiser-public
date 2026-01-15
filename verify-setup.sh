#!/bin/bash

# Filepath: verify-setup.sh
# Quick setup verification script
# Checks if Wegweiser is properly configured and ready to run

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'
BOLD='\033[1m'

print_status() { echo -e "${GREEN}[✓]${NC} $1"; }
print_error() { echo -e "${RED}[✗]${NC} $1"; }
print_warning() { echo -e "${YELLOW}[!]${NC} $1"; }
print_info() { echo -e "${BLUE}[i]${NC} $1"; }
print_header() { echo -e "\n${BOLD}$1${NC}\n"; }

errors=0
warnings=0

print_header "Wegweiser Setup Verification"

# Check .env file
print_info "Checking configuration files..."
if [ ! -f ".env" ]; then
    print_error ".env file not found"
    errors=$((errors + 1))
else
    print_status ".env file exists"
fi

# Check required files
required_files=("wsgi.py" "requirements.txt" "app/__init__.py" "app/setup.sh")
for file in "${required_files[@]}"; do
    if [ ! -f "$file" ]; then
        print_error "Required file missing: $file"
        errors=$((errors + 1))
    else
        print_status "Found: $file"
    fi
done

print_header "Checking System Requirements"

# Check Python
if command -v python3 &> /dev/null; then
    python_version=$(python3 --version 2>&1 | awk '{print $2}')
    print_status "Python 3 installed: $python_version"
else
    print_error "Python 3 not found"
    errors=$((errors + 1))
fi

# Check virtual environment
if [ -d "venv" ]; then
    print_status "Virtual environment found"
    if [ -f "venv/bin/python" ]; then
        print_status "Python venv activated"
    fi
else
    print_warning "Virtual environment not created - run: python3 -m venv venv"
    warnings=$((warnings + 1))
fi

# Check PostgreSQL
if command -v psql &> /dev/null; then
    print_status "PostgreSQL client installed"
else
    print_warning "PostgreSQL client not found - database commands may not work"
    warnings=$((warnings + 1))
fi

# Check Redis
if command -v redis-cli &> /dev/null; then
    print_status "Redis CLI installed"
else
    print_warning "Redis CLI not found - test connectivity manually"
    warnings=$((warnings + 1))
fi

print_header "Checking Configuration"

# Check .env variables
check_env_var() {
    local var_name=$1
    if grep -q "^${var_name}=" .env 2>/dev/null; then
        print_status "Found: $var_name"
    else
        print_warning "Not configured: $var_name"
        warnings=$((warnings + 1))
    fi
}

required_vars=("DATABASE_URL" "SQLALCHEMY_DATABASE_URI" "SECRET_KEY" "API_KEY" "REDIS_HOST")
for var in "${required_vars[@]}"; do
    check_env_var "$var"
done

print_header "Checking Dependencies"

# Check if requirements.txt is up to date
if [ ! -f "requirements.txt" ]; then
    print_error "requirements.txt not found"
    errors=$((errors + 1))
else
    print_status "requirements.txt found"
    print_info "To install dependencies, run:"
    echo "  source venv/bin/activate && pip install -r requirements.txt"
fi

print_header "Checking Services"

# Check if databases can be accessed
if [ -n "$(grep '^DATABASE_URL=' .env)" ] || [ -n "$(grep '^SQLALCHEMY_DATABASE_URI=' .env)" ]; then
    db_url=$(grep '^SQLALCHEMY_DATABASE_URI=' .env | cut -d'=' -f2-)
    print_info "Database configured: ${db_url:0:50}..."
else
    print_warning "Database URL not configured"
    warnings=$((warnings + 1))
fi

# Check Redis configuration
if [ -n "$(grep '^REDIS_HOST=' .env)" ]; then
    redis_host=$(grep '^REDIS_HOST=' .env | cut -d'=' -f2)
    print_info "Redis host: $redis_host"
else
    print_warning "Redis host not configured"
    warnings=$((warnings + 1))
fi

print_header "Secret Storage Status"

# Check secret storage configuration
if grep -q "^SECRET_STORAGE=" .env; then
    storage=$(grep '^SECRET_STORAGE=' .env | cut -d'=' -f2)
    print_status "Secret storage: $storage"
else
    print_warning "Secret storage not specified (defaulting to local)"
    warnings=$((warnings + 1))
fi

print_header "AI Provider Configuration"

# Check AI provider
if grep -q "^AI_PROVIDER=" .env; then
    provider=$(grep '^AI_PROVIDER=' .env | cut -d'=' -f2)
    print_status "AI provider: $provider"
else
    print_warning "AI provider not configured"
    warnings=$((warnings + 1))
fi

print_header "Verification Summary"

if [ $errors -eq 0 ] && [ $warnings -eq 0 ]; then
    print_status "All checks passed! System is ready to use."
    exit 0
elif [ $errors -eq 0 ]; then
    print_warning "Setup complete with $warnings warning(s)"
    print_info "Review warnings above and configure as needed"
    exit 0
else
    print_error "Setup incomplete with $errors error(s) and $warnings warning(s)"
    exit 1
fi
