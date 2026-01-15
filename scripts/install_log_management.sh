#!/bin/bash
# Filepath: scripts/install_log_management.sh
# Installation script for Wegweiser log management

set -e

echo "=== Installing Wegweiser Log Management ==="

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
    echo "Please run as root or with sudo"
    exit 1
fi

# Install logrotate configuration
echo "Installing logrotate configuration..."
cp /opt/wegweiser/config/logrotate.conf /etc/logrotate.d/wegweiser
chmod 644 /etc/logrotate.d/wegweiser
echo "  Logrotate configuration installed"

# Install systemd service and timer
echo "Installing systemd service and timer..."
cp /opt/wegweiser/config/wegweiser-log-cleanup.service /etc/systemd/system/
cp /opt/wegweiser/config/wegweiser-log-cleanup.timer /etc/systemd/system/
chmod 644 /etc/systemd/system/wegweiser-log-cleanup.service
chmod 644 /etc/systemd/system/wegweiser-log-cleanup.timer
echo "  Systemd files installed"

# Reload systemd
echo "Reloading systemd..."
systemctl daemon-reload

# Enable and start the timer
echo "Enabling log cleanup timer..."
systemctl enable wegweiser-log-cleanup.timer
systemctl start wegweiser-log-cleanup.timer

# Show timer status
echo ""
echo "=== Timer Status ==="
systemctl status wegweiser-log-cleanup.timer --no-pager

echo ""
echo "=== Next Scheduled Run ==="
systemctl list-timers wegweiser-log-cleanup.timer --no-pager

echo ""
echo "Installation complete!"
echo ""
echo "You can:"
echo "  - Run cleanup manually: sudo /opt/wegweiser/scripts/cleanup_logs.sh"
echo "  - Test logrotate: sudo logrotate -f /etc/logrotate.d/wegweiser"
echo "  - Check timer status: systemctl status wegweiser-log-cleanup.timer"
echo "  - View timer logs: journalctl -u wegweiser-log-cleanup.service"

