#!/usr/bin/env bash
set -euo pipefail

# Install or update the Wegweiser NATS Receiver systemd service
# Usage: sudo ./dev_scripts/ops/install_nats_receiver_service.sh

SERVICE_NAME="wegweiser-nats-receiver"
SERVICE_FILE_SOURCE="/opt/wegweiser/config/systemd/${SERVICE_NAME}.service"
SERVICE_FILE_TARGET="/etc/systemd/system/${SERVICE_NAME}.service"
APP_DIR="/opt/wegweiser"
SVC_USER="weg-nats-svc"
SVC_GROUP="weg-nats-svc"
PYTHON_BIN="$(command -v python3)"

if [[ $EUID -ne 0 ]]; then
  echo "Please run as root (sudo)" >&2
  exit 1
fi

# Ensure dependencies
if ! grep -qi "nats-py" "$APP_DIR/requirements.txt"; then
  echo "Adding nats-py to requirements.txt"
  echo "nats-py>=2.11.0" >> "$APP_DIR/requirements.txt"
fi

# Create service user if missing
if ! id -u "$SVC_USER" >/dev/null 2>&1; then
  useradd -r -s /usr/sbin/nologin -d "$APP_DIR" -M "$SVC_USER"
fi

# Ensure ownership of wlog directory
install -d -o "$SVC_USER" -g "$SVC_GROUP" "$APP_DIR/wlog"

# Install Python dependencies (system-wide or venv if present)
if [[ -d "$APP_DIR/venv" ]]; then
  echo "Using venv at $APP_DIR/venv"
  "$APP_DIR/venv/bin/pip" install -r "$APP_DIR/requirements.txt"
else
  pip3 install -r "$APP_DIR/requirements.txt"
fi

# Copy systemd unit
install -m 0644 "$SERVICE_FILE_SOURCE" "$SERVICE_FILE_TARGET"

# Reload and enable service
systemctl daemon-reload
systemctl enable "$SERVICE_NAME"
systemctl restart "$SERVICE_NAME"

# Show status
systemctl --no-pager --full status "$SERVICE_NAME"
