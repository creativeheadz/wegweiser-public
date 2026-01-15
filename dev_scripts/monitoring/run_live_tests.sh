#!/bin/bash
# Live Monitoring Tests Runner
# Run via Tactical RMM on a schedule (e.g., every 5-10 minutes)
# Usage: ./run_live_tests.sh [--with-login] [--with-mfa]

set -e

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WEGWEISER_ROOT="/opt/wegweiser"
VENV_PATH="${WEGWEISER_ROOT}/venv"
LOG_FILE="${WEGWEISER_ROOT}/wlog/live_tests.log"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Load environment variables
if [ -f "${WEGWEISER_ROOT}/.env" ]; then
    export $(cat "${WEGWEISER_ROOT}/.env" | grep -v '^#' | xargs)
fi

# Set defaults
WEGWEISER_URL="${WEGWEISER_URL:-http://localhost}"
TEST_USER_EMAIL="${TEST_USER_EMAIL:-monitor@test.local}"
TEST_USER_PASSWORD="${TEST_USER_PASSWORD:-TestPassword123!}"

# Parse arguments
WITH_LOGIN=false
WITH_MFA=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --with-login)
            WITH_LOGIN=true
            shift
            ;;
        --with-mfa)
            WITH_MFA=true
            shift
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

# Activate virtual environment
if [ ! -d "$VENV_PATH" ]; then
    echo -e "${RED}Virtual environment not found at $VENV_PATH${NC}"
    exit 1
fi

source "$VENV_PATH/bin/activate"

# Run tests
echo -e "${YELLOW}Starting Wegweiser Live Monitoring Tests${NC}"
echo "URL: $WEGWEISER_URL"
echo "Timestamp: $(date)"
echo "---"

cd "$WEGWEISER_ROOT"

# Run basic tests
python3 "$SCRIPT_DIR/live_tests.py"
BASIC_RESULT=$?

# Run login simulation if requested
if [ "$WITH_LOGIN" = true ]; then
    echo -e "${YELLOW}Running login simulation...${NC}"
    python3 << 'EOF'
import sys
sys.path.insert(0, '/opt/wegweiser')
from dev_scripts.monitoring.login_simulator import LoginSimulator
import os

simulator = LoginSimulator(base_url=os.getenv('WEGWEISER_URL', 'http://localhost'))
result = simulator.simulate_login_with_mfa(
    email=os.getenv('TEST_USER_EMAIL', 'monitor@test.local'),
    password=os.getenv('TEST_USER_PASSWORD', 'TestPassword123!'),
    use_backup_code=False
)

print(f"Login Result: {'✓ PASS' if result.success else '✗ FAIL'}")
print(f"Duration: {result.duration_ms:.0f}ms")
print(f"Message: {result.message}")
print(f"MFA Required: {result.mfa_required}")
print(f"MFA Verified: {result.mfa_verified}")

sys.exit(0 if result.success else 1)
EOF
    LOGIN_RESULT=$?
else
    LOGIN_RESULT=0
fi

# Determine overall result
if [ $BASIC_RESULT -eq 0 ] && [ $LOGIN_RESULT -eq 0 ]; then
    echo -e "${GREEN}All tests passed!${NC}"
    exit 0
else
    echo -e "${RED}Some tests failed!${NC}"
    exit 1
fi

