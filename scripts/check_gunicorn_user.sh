#!/bin/bash
# Filepath: scripts/check_gunicorn_user.sh
# Verify gunicorn is running as the correct user, not root
# This should be run before deployments or as part of health checks

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

EXPECTED_USER="wegweiser"

echo "Checking gunicorn process ownership..."

# Check for any root-owned gunicorn processes
ROOT_PROCS=$(ps aux | grep -E "gunicorn|wegweiser.*python" | grep "^root" | grep -v grep || true)

if [ -n "$ROOT_PROCS" ]; then
    echo -e "${RED}ERROR: Found gunicorn/python processes running as root:${NC}"
    echo "$ROOT_PROCS"
    echo ""
    echo -e "${YELLOW}This will cause permission issues!${NC}"
    echo ""
    echo "To fix, kill these processes and restart via systemd:"
    echo "  1. Get the PIDs from above output"
    echo "  2. sudo kill -9 <PIDs>"
    echo "  3. sudo systemctl restart wegweiser"
    exit 1
else
    echo -e "${GREEN}✓ No root-owned gunicorn processes found${NC}"
fi

# Check that wegweiser user processes exist
WEGWEISER_PROCS=$(ps aux | grep gunicorn | grep "$EXPECTED_USER" | grep -v grep || true)

if [ -z "$WEGWEISER_PROCS" ]; then
    echo -e "${RED}ERROR: No gunicorn processes found running as $EXPECTED_USER${NC}"
    echo "The application may not be running properly."
    exit 1
else
    PROC_COUNT=$(echo "$WEGWEISER_PROCS" | wc -l)
    echo -e "${GREEN}✓ Found $PROC_COUNT gunicorn process(es) running as $EXPECTED_USER${NC}"
fi

# Check systemd service status
if systemctl is-active --quiet wegweiser; then
    echo -e "${GREEN}✓ wegweiser systemd service is active${NC}"
else
    echo -e "${YELLOW}WARNING: wegweiser systemd service is not active${NC}"
fi

echo ""
echo "All checks passed!"
exit 0
