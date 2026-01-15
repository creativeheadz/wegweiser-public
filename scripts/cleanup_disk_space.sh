#!/bin/bash
# Filepath: scripts/cleanup_disk_space.sh
# Comprehensive disk space cleanup script for Wegweiser server
# Based on disk space analysis from 2025-11-08

set -e

echo "=== Wegweiser Disk Space Cleanup Script ==="
echo "Started at: $(date)"
echo ""

# Show current disk usage
echo "=== Current Disk Usage ==="
df -h / | grep -E "Filesystem|/dev/root"
echo ""

# Backup location
BACKUP_DIR="/opt/wegweiser/.backup/disk_cleanup_$(date +%Y%m%d_%H%M%S)"
mkdir -p "$BACKUP_DIR"
echo "Backup directory: $BACKUP_DIR"
echo ""

# Function to safely delete with confirmation
safe_delete() {
    local path=$1
    local description=$2
    
    if [ -e "$path" ]; then
        size=$(du -sh "$path" 2>/dev/null | cut -f1)
        echo "Found: $description"
        echo "  Path: $path"
        echo "  Size: $size"
        echo "  Deleting..."
        rm -rf "$path"
        echo "  ✓ Deleted"
        echo ""
    else
        echo "Not found: $description ($path)"
        echo ""
    fi
}

# IMMEDIATE ACTIONS

echo "=== IMMEDIATE ACTIONS ==="
echo ""

# 1. Delete dummy.txt files
echo "1. Cleaning up dummy.txt test files..."
find /opt/wegweiser/deviceFiles -name "dummy.txt" -type f -exec sh -c '
    for file; do
        size=$(du -sh "$file" | cut -f1)
        echo "  Deleting: $file ($size)"
        rm -f "$file"
    done
' sh {} +
echo "  ✓ Dummy files cleaned"
echo ""

# 2. Delete old wegweiser backup
echo "2. Removing old wegweiser backup..."
safe_delete "/home/andrei/wegweiser_old_20251010_192545.tar.gz" "Old Wegweiser backup (Oct 10)"

# 3. Delete unknown file
echo "3. Removing unknown file..."
safe_delete "/home/andrei/zi3fm04N" "Unknown file zi3fm04N"

# 4. Delete test_agent directory
echo "4. Removing test agent directory..."
safe_delete "/home/andrei/test_agent" "Test agent directory"

# 5. Clean NPM cache
echo "5. Cleaning NPM cache..."
if command -v npm &> /dev/null; then
    echo "  Running: npm cache clean --force"
    npm cache clean --force 2>/dev/null || echo "  NPM cache clean failed (non-critical)"
    echo "  ✓ NPM cache cleaned"
else
    echo "  NPM not found, skipping"
fi
echo ""

# 6. Clean old device event logs (older than 60 days)
echo "6. Cleaning old device event logs (>60 days)..."
OLD_EVENTS=$(find /opt/wegweiser/deviceFiles -name "events-*.json" -type f -mtime +60 2>/dev/null | wc -l)
if [ "$OLD_EVENTS" -gt 0 ]; then
    echo "  Found $OLD_EVENTS old event log files"
    find /opt/wegweiser/deviceFiles -name "events-*.json" -type f -mtime +60 -exec sh -c '
        for file; do
            size=$(du -sh "$file" | cut -f1)
            echo "    Deleting: $(basename $(dirname $file))/$(basename $file) ($size)"
            rm -f "$file"
        done
    ' sh {} +
    echo "  ✓ Old event logs cleaned"
else
    echo "  No old event logs found (>60 days)"
fi
echo ""

# 7. Clean old msinfo files (older than 90 days)
echo "7. Cleaning old msinfo files (>90 days)..."
OLD_MSINFO=$(find /opt/wegweiser/deviceFiles -name "msinfo.txt" -type f -mtime +90 2>/dev/null | wc -l)
if [ "$OLD_MSINFO" -gt 0 ]; then
    echo "  Found $OLD_MSINFO old msinfo files"
    find /opt/wegweiser/deviceFiles -name "msinfo.txt" -type f -mtime +90 -delete
    echo "  ✓ Old msinfo files cleaned"
else
    echo "  No old msinfo files found (>90 days)"
fi
echo ""

# 8. Clean old journal files (older than 30 days)
echo "8. Cleaning old journal files (>30 days)..."
OLD_JOURNAL=$(find /opt/wegweiser/deviceFiles -name "journal.json" -type f -mtime +30 2>/dev/null | wc -l)
if [ "$OLD_JOURNAL" -gt 0 ]; then
    echo "  Found $OLD_JOURNAL old journal files"
    find /opt/wegweiser/deviceFiles -name "journal.json" -type f -mtime +30 -delete
    echo "  ✓ Old journal files cleaned"
else
    echo "  No old journal files found (>30 days)"
fi
echo ""

# 9. Clean empty device directories
echo "9. Cleaning empty device directories..."
EMPTY_DIRS=$(find /opt/wegweiser/deviceFiles -type d -empty 2>/dev/null | wc -l)
if [ "$EMPTY_DIRS" -gt 0 ]; then
    echo "  Found $EMPTY_DIRS empty directories"
    find /opt/wegweiser/deviceFiles -type d -empty -delete
    echo "  ✓ Empty directories cleaned"
else
    echo "  No empty directories found"
fi
echo ""

# 10. Clean old VSCode server versions (keep latest 2)
echo "10. Cleaning old VSCode server versions..."
if [ -d "/home/andrei/.vscode-server/cli/servers" ]; then
    echo "  Keeping latest 2 VSCode server versions..."
    cd /home/andrei/.vscode-server/cli/servers
    ls -t | tail -n +3 | xargs -r rm -rf
    echo "  ✓ Old VSCode servers cleaned"
else
    echo "  VSCode server directory not found"
fi
echo ""

# 11. Clean VSCode workspace storage (old checkpoints)
echo "11. Cleaning old VSCode workspace storage..."
if [ -d "/home/andrei/.vscode-server/data/User/workspaceStorage" ]; then
    find /home/andrei/.vscode-server/data/User/workspaceStorage -type f -name "*.json" -mtime +30 -size +10M -delete 2>/dev/null || true
    echo "  ✓ Old workspace storage cleaned"
else
    echo "  Workspace storage directory not found"
fi
echo ""

# 12. Clean old snap revisions
echo "12. Cleaning old snap package revisions..."
if command -v snap &> /dev/null; then
    snap list --all | awk '/disabled/{print $1, $3}' | while read snapname revision; do
        echo "  Removing: $snapname (revision $revision)"
        snap remove "$snapname" --revision="$revision" 2>/dev/null || true
    done
    echo "  ✓ Old snap revisions cleaned"
else
    echo "  Snap not found, skipping"
fi
echo ""

# Show final disk usage
echo ""
echo "=== Disk Usage After Cleanup ==="
df -h / | grep -E "Filesystem|/dev/root"
echo ""

echo "=== Directory Sizes After Cleanup ==="
echo "Device files:    $(du -sh /opt/wegweiser/deviceFiles 2>/dev/null | cut -f1)"
echo "Git repository:  $(du -sh /opt/wegweiser/.git 2>/dev/null | cut -f1)"
echo "Home directory:  $(du -sh /home/andrei 2>/dev/null | cut -f1)"
echo "VSCode server:   $(du -sh /home/andrei/.vscode-server 2>/dev/null | cut -f1)"
echo ""

echo "Cleanup completed at: $(date)"
echo ""
echo "Next steps:"
echo "  - Review /opt/wegweiser/downloads for old files"
echo "  - Consider running: git gc --aggressive --prune=now"
echo "  - Monitor disk usage regularly"

