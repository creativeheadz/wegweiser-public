#!/bin/bash
# Filepath: scripts/check_permissions.sh
# Check and fix critical directory permissions for Wegweiser
# This script monitors and auto-corrects permission issues that break the application

set -e

APP_DIR="/opt/wegweiser"
APP_USER="wegweiser"
APP_GROUP="www-data"
LOG_FILE="/var/log/wegweiser/permission_check.log"
ALERT_EMAIL="${WEGWEISER_ALERT_EMAIL:-}"

# Text formatting
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log_msg() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

log_error() {
    echo -e "${RED}[$(date '+%Y-%m-%d %H:%M:%S')] ERROR: $1${NC}" | tee -a "$LOG_FILE"
}

log_warning() {
    echo -e "${YELLOW}[$(date '+%Y-%m-%d %H:%M:%S')] WARNING: $1${NC}" | tee -a "$LOG_FILE"
}

log_success() {
    echo -e "${GREEN}[$(date '+%Y-%m-%d %H:%M:%S')] SUCCESS: $1${NC}" | tee -a "$LOG_FILE"
}

send_alert() {
    local message="$1"
    
    # Log the alert
    log_error "ALERT: $message"
    
    # Send email if configured
    if [ -n "$ALERT_EMAIL" ]; then
        echo "$message" | mail -s "Wegweiser Permission Alert" "$ALERT_EMAIL" 2>/dev/null || true
    fi
    
    # Log to syslog
    logger -t wegweiser-permissions "ALERT: $message"
}

check_and_fix_dir() {
    local dir="$1"
    local expected_owner="$2"
    local expected_group="$3"
    local expected_perms="$4"
    local fixed=0
    
    if [ ! -d "$dir" ]; then
        log_warning "Directory does not exist: $dir (will be created by application)"
        return 0
    fi
    
    # Check ownership
    local current_owner=$(stat -c '%U' "$dir")
    local current_group=$(stat -c '%G' "$dir")
    local current_perms=$(stat -c '%a' "$dir")
    
    # Check if ownership is correct
    if [ "$current_owner" != "$expected_owner" ] || [ "$current_group" != "$expected_group" ]; then
        log_warning "Incorrect ownership on $dir: $current_owner:$current_group (expected $expected_owner:$expected_group)"
        send_alert "Permission issue detected on $dir - owner: $current_owner:$current_group, expected: $expected_owner:$expected_group. Auto-fixing..."
        
        chown "$expected_owner:$expected_group" "$dir"
        log_success "Fixed ownership on $dir -> $expected_owner:$expected_group"
        fixed=1
    fi
    
    # Check permissions
    if [ "$current_perms" != "$expected_perms" ]; then
        log_warning "Incorrect permissions on $dir: $current_perms (expected $expected_perms)"
        chmod "$expected_perms" "$dir"
        log_success "Fixed permissions on $dir -> $expected_perms"
        fixed=1
    fi
    
    if [ $fixed -eq 0 ]; then
        log_msg "✓ $dir: $current_owner:$current_group ($current_perms) - OK"
    fi
    
    return $fixed
}

# Ensure log directory exists
mkdir -p /var/log/wegweiser
chown wegweiser:www-data /var/log/wegweiser 2>/dev/null || true

log_msg "========== Wegweiser Permission Check Starting =========="

# Track if any fixes were made
FIXES_MADE=0

# Critical directories that must have correct permissions
CRITICAL_DIRS=(
    "$APP_DIR/payloads:$APP_USER:$APP_GROUP:775"
    "$APP_DIR/payloads/queue:$APP_USER:$APP_GROUP:775"
    "$APP_DIR/payloads/invalid:$APP_USER:$APP_GROUP:775"
    "$APP_DIR/payloads/noDeviceUuid:$APP_USER:$APP_GROUP:775"
    "$APP_DIR/payloads/ophanedCollectors:$APP_USER:$APP_GROUP:775"
    "$APP_DIR/payloads/sucessfulImport:$APP_USER:$APP_GROUP:775"
    "$APP_DIR/deviceFiles:$APP_USER:$APP_GROUP:775"
    "$APP_DIR/logs:$APP_USER:$APP_GROUP:775"
    "$APP_DIR/wlog:$APP_USER:$APP_GROUP:775"
    "$APP_DIR/data:$APP_USER:$APP_GROUP:775"
    "$APP_DIR/data/uploads:$APP_USER:$APP_GROUP:775"
    "$APP_DIR/data/cache:$APP_USER:$APP_GROUP:775"
    "$APP_DIR/downloads:$APP_USER:$APP_GROUP:775"
    "$APP_DIR/tmp:$APP_USER:$APP_GROUP:775"
    "$APP_DIR/flask_session:$APP_USER:$APP_GROUP:775"
    "$APP_DIR/backups:$APP_USER:$APP_GROUP:775"
    "$APP_DIR/snippets:$APP_USER:$APP_GROUP:775"
)

# Check each critical directory
for dir_spec in "${CRITICAL_DIRS[@]}"; do
    IFS=':' read -r dir owner group perms <<< "$dir_spec"
    check_and_fix_dir "$dir" "$owner" "$group" "$perms"
    if [ $? -eq 1 ]; then
        FIXES_MADE=1
    fi
done

log_msg "========== Wegweiser Permission Check Complete =========="

if [ $FIXES_MADE -eq 1 ]; then
    log_warning "Permission fixes were applied. Check log for details."
    exit 1
else
    log_msg "All permissions are correct."
    exit 0
fi
