#!/bin/bash
# Celery Worker Wrapper Script
# This script dynamically determines the log level from logging_config.json
# and starts the Celery worker with the appropriate log level

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APP_DIR="$(dirname "$(dirname "$SCRIPT_DIR")")"

# Source the environment file if it exists
if [ -f /etc/default/celery-worker ]; then
    source /etc/default/celery-worker
fi

# Get the log level from the Python utility
CELERY_LOG_LEVEL=$("${APP_DIR}/venv/bin/python3" "${SCRIPT_DIR}/get_celery_log_level.py" 2>/dev/null)

# Default to WARNING if we couldn't determine the level
if [ -z "$CELERY_LOG_LEVEL" ]; then
    CELERY_LOG_LEVEL="WARNING"
fi

# Export the log level for use in the systemd service
export CELERYD_LOG_LEVEL="$CELERY_LOG_LEVEL"

# Ensure PID and LOG directories exist, with safe fallbacks
resolve_dir() {
    local path="$1"
    # Extract directory component
    local dir
    dir=$(dirname "$path")
    echo "$dir"
}

# Default/fallback locations under the application directory
APP_RUN_DIR="${APP_DIR}/run/celery"
APP_LOG_DIR="${APP_DIR}/wlog"

# Prepare PID directory
PID_DIR="$(resolve_dir "${CELERYD_PID_FILE}")"
if [ -z "${PID_DIR}" ] || [ "${PID_DIR}" = "." ]; then
    PID_DIR="/run/celery"
fi

# Try to ensure PID_DIR exists; if not writable, fallback to app-local run dir
if ! mkdir -p "${PID_DIR}" 2>/dev/null; then
    mkdir -p "${APP_RUN_DIR}"
    PID_DIR="${APP_RUN_DIR}"
    CELERYD_PID_FILE="${PID_DIR}/%n.pid"
fi

# Prepare LOG directory
LOG_DIR="$(resolve_dir "${CELERYD_LOG_FILE}")"
if [ -z "${LOG_DIR}" ] || [ "${LOG_DIR}" = "." ]; then
    LOG_DIR="${APP_LOG_DIR}"
fi
mkdir -p "${LOG_DIR}" 2>/dev/null || true

# Execute the original Celery command with the determined log level
exec "${CELERY_BIN}" -A "${CELERY_APP}" multi start "${CELERYD_NODES}" \
    --pidfile="${CELERYD_PID_FILE}" \
    --logfile="${CELERYD_LOG_FILE}" --loglevel="${CELERYD_LOG_LEVEL}" \
    ${CELERYD_OPTS}

