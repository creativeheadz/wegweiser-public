#!/bin/bash
# Filepath: scripts/cleanup_device_files.sh
# Device file retention management for Wegweiser
# Implements retention policies for device event logs and system information

set -e

# Configuration - Retention periods in days
SECURITY_LOGS_RETENTION=60
APPLICATION_LOGS_RETENTION=30
SYSTEM_LOGS_RETENTION=30
JOURNAL_RETENTION=30
MSINFO_RETENTION=90
SERVICES_RETENTION=90

# Dry run mode - set to 1 to preview without deleting
DRY_RUN=${1:-0}

echo "=== Wegweiser Device Files Cleanup ==="
echo "Started at: $(date)"
echo ""

if [ "$DRY_RUN" = "1" ] || [ "$DRY_RUN" = "--dry-run" ]; then
    echo "*** DRY RUN MODE - No files will be deleted ***"
    echo ""
    DRY_RUN=1
else
    DRY_RUN=0
fi

DEVICE_FILES_DIR="/opt/wegweiser/deviceFiles"

if [ ! -d "$DEVICE_FILES_DIR" ]; then
    echo "Error: Device files directory not found: $DEVICE_FILES_DIR"
    exit 1
fi

# Function to clean files by pattern and age
cleanup_files() {
    local pattern=$1
    local retention_days=$2
    local description=$3
    
    echo "Cleaning: $description (retention: $retention_days days)"
    
    local files_found=$(find "$DEVICE_FILES_DIR" -name "$pattern" -type f -mtime +$retention_days 2>/dev/null | wc -l)
    
    if [ "$files_found" -eq 0 ]; then
        echo "  No files found older than $retention_days days"
        echo ""
        return
    fi
    
    echo "  Found $files_found files to clean"
    
    local total_size=0
    local count=0
    
    find "$DEVICE_FILES_DIR" -name "$pattern" -type f -mtime +$retention_days 2>/dev/null | while read file; do
        size=$(stat -f%z "$file" 2>/dev/null || stat -c%s "$file" 2>/dev/null)
        size_mb=$(echo "scale=1; $size/1024/1024" | bc)
        device_dir=$(basename $(dirname "$file"))
        filename=$(basename "$file")
        age_days=$(( ($(date +%s) - $(stat -f%m "$file" 2>/dev/null || stat -c%Y "$file" 2>/dev/null)) / 86400 ))
        
        echo "    $device_dir/$filename - ${size_mb}MB (${age_days} days old)"
        
        if [ "$DRY_RUN" -eq 0 ]; then
            rm -f "$file"
        fi
    done
    
    if [ "$DRY_RUN" -eq 0 ]; then
        echo "  ✓ Cleaned $files_found files"
    else
        echo "  [DRY RUN] Would clean $files_found files"
    fi
    echo ""
}

# Show current disk usage
echo "=== Current Disk Usage ==="
df -h / | grep -E "Filesystem|/dev/root"
echo ""
echo "Device files directory: $(du -sh $DEVICE_FILES_DIR 2>/dev/null | cut -f1)"
echo ""

# Count files by type
echo "=== File Inventory ==="
echo "Security logs:     $(find $DEVICE_FILES_DIR -name "events-Security.json" 2>/dev/null | wc -l) files"
echo "Application logs:  $(find $DEVICE_FILES_DIR -name "events-Application.json" 2>/dev/null | wc -l) files"
echo "System logs:       $(find $DEVICE_FILES_DIR -name "events-System.json" 2>/dev/null | wc -l) files"
echo "Journal files:     $(find $DEVICE_FILES_DIR -name "journal.json" 2>/dev/null | wc -l) files"
echo "MSInfo files:      $(find $DEVICE_FILES_DIR -name "msinfo.txt" 2>/dev/null | wc -l) files"
echo "Services files:    $(find $DEVICE_FILES_DIR -name "services.json" 2>/dev/null | wc -l) files"
echo "Dummy files:       $(find $DEVICE_FILES_DIR -name "dummy.txt" 2>/dev/null | wc -l) files"
echo "Total device dirs: $(find $DEVICE_FILES_DIR -mindepth 1 -maxdepth 1 -type d 2>/dev/null | wc -l) directories"
echo ""

# Clean up files by type and retention policy
echo "=== Applying Retention Policies ==="
echo ""

# Always delete dummy/test files regardless of age
echo "Cleaning: Test/dummy files (immediate deletion)"
DUMMY_COUNT=$(find "$DEVICE_FILES_DIR" -name "dummy.txt" -type f 2>/dev/null | wc -l)
if [ "$DUMMY_COUNT" -gt 0 ]; then
    echo "  Found $DUMMY_COUNT dummy files"
    find "$DEVICE_FILES_DIR" -name "dummy.txt" -type f 2>/dev/null | while read file; do
        size=$(stat -f%z "$file" 2>/dev/null || stat -c%s "$file" 2>/dev/null)
        size_mb=$(echo "scale=1; $size/1024/1024" | bc)
        device_dir=$(basename $(dirname "$file"))
        echo "    $device_dir/dummy.txt - ${size_mb}MB"
        if [ "$DRY_RUN" -eq 0 ]; then
            rm -f "$file"
        fi
    done
    if [ "$DRY_RUN" -eq 0 ]; then
        echo "  ✓ Deleted $DUMMY_COUNT dummy files"
    else
        echo "  [DRY RUN] Would delete $DUMMY_COUNT dummy files"
    fi
else
    echo "  No dummy files found"
fi
echo ""

# Clean event logs by type
cleanup_files "events-Security.json" $SECURITY_LOGS_RETENTION "Security event logs"
cleanup_files "events-Application.json" $APPLICATION_LOGS_RETENTION "Application event logs"
cleanup_files "events-System.json" $SYSTEM_LOGS_RETENTION "System event logs"

# Clean other files
cleanup_files "journal.json" $JOURNAL_RETENTION "Journal files"
cleanup_files "msinfo.txt" $MSINFO_RETENTION "MSInfo files"
cleanup_files "services.json" $SERVICES_RETENTION "Services files"

# Clean empty device directories
echo "Cleaning: Empty device directories"
EMPTY_DIRS=$(find "$DEVICE_FILES_DIR" -mindepth 1 -maxdepth 1 -type d -empty 2>/dev/null | wc -l)
if [ "$EMPTY_DIRS" -gt 0 ]; then
    echo "  Found $EMPTY_DIRS empty directories"
    find "$DEVICE_FILES_DIR" -mindepth 1 -maxdepth 1 -type d -empty 2>/dev/null | while read dir; do
        device_uuid=$(basename "$dir")
        echo "    $device_uuid"
        if [ "$DRY_RUN" -eq 0 ]; then
            rmdir "$dir"
        fi
    done
    if [ "$DRY_RUN" -eq 0 ]; then
        echo "  ✓ Removed $EMPTY_DIRS empty directories"
    else
        echo "  [DRY RUN] Would remove $EMPTY_DIRS empty directories"
    fi
else
    echo "  No empty directories found"
fi
echo ""

# Show final statistics
echo "=== Final Statistics ==="
df -h / | grep -E "Filesystem|/dev/root"
echo ""
echo "Device files directory: $(du -sh $DEVICE_FILES_DIR 2>/dev/null | cut -f1)"
echo ""

if [ "$DRY_RUN" -eq 1 ]; then
    echo "*** DRY RUN COMPLETE - No files were deleted ***"
    echo "Run without --dry-run to perform actual cleanup"
else
    echo "Cleanup completed at: $(date)"
fi

