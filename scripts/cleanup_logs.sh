#!/bin/bash
# Filepath: scripts/cleanup_logs.sh
# Log cleanup script for Wegweiser
# This script cleans up old logs and manages disk space

set -e

# Configuration
LOG_DIR="/opt/wegweiser/wlog"
VAR_LOG_DIR="/var/log/wegweiser"
PAYLOADS_DIR="/opt/wegweiser/payloads"
DAYS_TO_KEEP=7
SUCCESSFUL_IMPORT_DAYS=3

echo "=== Wegweiser Log Cleanup Script ==="
echo "Started at: $(date)"

# Function to safely delete files older than N days
cleanup_old_files() {
    local dir=$1
    local days=$2
    local pattern=$3
    
    if [ -d "$dir" ]; then
        echo "Cleaning up files in $dir older than $days days (pattern: $pattern)"
        find "$dir" -name "$pattern" -type f -mtime +$days -delete 2>/dev/null || true
        echo "  Done"
    else
        echo "  Directory $dir does not exist, skipping"
    fi
}

# Function to truncate large log files
truncate_large_logs() {
    local dir=$1
    local max_size_mb=$2
    
    if [ -d "$dir" ]; then
        echo "Checking for log files larger than ${max_size_mb}MB in $dir"
        find "$dir" -name "*.log" -type f -size +${max_size_mb}M -exec sh -c '
            for file; do
                echo "  Truncating large file: $file ($(du -h "$file" | cut -f1))"
                # Keep last 1000 lines
                tail -n 1000 "$file" > "$file.tmp" && mv "$file.tmp" "$file"
            done
        ' sh {} +
    fi
}

# Clean up old log files in wlog directory
cleanup_old_files "$LOG_DIR" "$DAYS_TO_KEEP" "*.log.*"
cleanup_old_files "$LOG_DIR" "$DAYS_TO_KEEP" "*.gz"

# Clean up old log files in /var/log/wegweiser
cleanup_old_files "$VAR_LOG_DIR" "$DAYS_TO_KEEP" "*.log.*"
cleanup_old_files "$VAR_LOG_DIR" "$DAYS_TO_KEEP" "*.gz"

# Clean up old device backups
cleanup_old_files "$VAR_LOG_DIR/device_backups" "$DAYS_TO_KEEP" "*.json"

# Clean up old tenant backups
cleanup_old_files "$VAR_LOG_DIR/tenant_backups" "$DAYS_TO_KEEP" "*.json"

# Clean up old successfully imported payloads
cleanup_old_files "$PAYLOADS_DIR/sucessfulImport" "$SUCCESSFUL_IMPORT_DAYS" "*"

# Clean up old invalid payloads
cleanup_old_files "$PAYLOADS_DIR/invalid" "$DAYS_TO_KEEP" "*"

# Clean up old orphaned collectors
cleanup_old_files "$PAYLOADS_DIR/ophanedCollectors" "$DAYS_TO_KEEP" "*"

# Truncate very large log files (over 100MB)
truncate_large_logs "$LOG_DIR" 100
truncate_large_logs "$VAR_LOG_DIR" 100

# Clean up old compressed logs
echo "Cleaning up old compressed logs"
find /var/log -name "*.gz" -type f -mtime +$DAYS_TO_KEEP -delete 2>/dev/null || true

# Show disk usage after cleanup
echo ""
echo "=== Disk Usage After Cleanup ==="
df -h / | grep -E "Filesystem|/dev/root"
echo ""
echo "Log directory sizes:"
du -sh "$LOG_DIR" 2>/dev/null || echo "  $LOG_DIR: N/A"
du -sh "$VAR_LOG_DIR" 2>/dev/null || echo "  $VAR_LOG_DIR: N/A"
du -sh "$PAYLOADS_DIR" 2>/dev/null || echo "  $PAYLOADS_DIR: N/A"

echo ""
echo "Cleanup completed at: $(date)"

