#!/bin/bash
###############################################################################
# Global Markdown Cleanup Script
#
# Scans the entire project for stray markdown files and organizes them:
# - Moves important project docs to /documentation/
# - Deletes status reports and implementation files
# - Preserves configuration files
# - Skips vendor directories (venv, node_modules, .git, installerFiles, loki, etc.)
###############################################################################

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Configuration
PROJECT_ROOT="${1:-.}"
DOCS_DIR="$PROJECT_ROOT/documentation"
LOG_FILE="$PROJECT_ROOT/wlog/md_cleanup_global.log"
BACKUP_DIR="$PROJECT_ROOT/.backup/md_cleanup_$(date +%s)"

# Files to always preserve
PRESERVE_FILES=("CLAUDE.md")

# Directories to skip (vendor, dependencies, archives)
SKIP_DIRS=(
    "\.git"
    "venv"
    "node_modules"
    "installerFiles"
    "loki"
    "mcp/gguf"
)

# Important documentation patterns (move these to /documentation/)
IMPORTANT_PATTERNS=(
    "README"
    "SETUP"
    "GUIDE"
    "QUICKSTART"
    "ARCHITECTURE"
    "DEVELOPER"
    "SECURITY"
    "API"
    "REFERENCE"
    "PORTABILITY"
    "DESIGN"
    "MECHANISM"
    "FIX_LOG"
    "BACKGROUND_OPTIONS"
    "NATS"
    "INTEGRATION"
)

# Obsolete patterns (delete these)
OBSOLETE_PATTERNS=(
    "READY"
    "COMPLETE"
    "CHECKLIST"
    "SUMMARY"
    "IMPLEMENTATION"
    "DEPLOYMENT_GUIDE_.*UPDATE"
    "MCP_DEPLOYMENT"
    "AGENT_UPDATE_IMPLEMENTATION"
    "PHASE_.*_COMPLETE"
    "DESIGN_CHANGES"
    "DRIVE_DATA_FIX"
    "KEYVAULT_MIGRATION"
    "NEXT_DESIGN"
    "ROUTES_MISSING"
    "SIDEBAR_.*"
    "UNIFIED_CHAT"
    "TESTING_CHECKLIST"
    "STACK"
)

# Location-specific rules
# These are "okay to delete" because they're in specialized locations
LOCATION_RULES=(
    "dev_scripts/monitoring"  # monitoring guides are implementation-specific
)

# Stats
MOVED=0
DELETED=0
PRESERVED=0
INVALID=0
SKIPPED=0
REVIEWED=0

# Ensure directories exist
mkdir -p "$DOCS_DIR"
mkdir -p "$BACKUP_DIR"
mkdir -p "$(dirname "$LOG_FILE")"

# Initialize log
{
    echo "=== Global Markdown Cleanup Log ==="
    echo "Timestamp: $(date)"
    echo "Project Root: $PROJECT_ROOT"
    echo ""
} > "$LOG_FILE"

echo -e "${CYAN}=== Global Markdown Cleanup ===${NC}"
echo -e "${CYAN}Project Root: $PROJECT_ROOT${NC}"
echo -e "${CYAN}Scanning all directories (excluding vendor/dependencies)${NC}"
echo ""

###############################################################################
# Helper Functions
###############################################################################

log() {
    echo "$1" | tee -a "$LOG_FILE"
}

# Check if path should be skipped
should_skip() {
    local path=$1

    for skip_dir in "${SKIP_DIRS[@]}"; do
        if [[ "$path" =~ $skip_dir ]]; then
            return 0
        fi
    done

    return 1
}

# Check if file is in a monitored location
is_in_location() {
    local file=$1
    local location=$2

    [[ "$file" == *"$location"* ]]
}

validate_markdown() {
    local file=$1

    # Check if file has content
    if [[ ! -s "$file" ]]; then
        return 1
    fi

    # Check if it has markdown structure (at least one header or meaningful content)
    if grep -q "^#" "$file" || [[ $(wc -l < "$file") -gt 5 ]]; then
        return 0
    fi

    return 1
}

is_important() {
    local filename=$1

    for pattern in "${IMPORTANT_PATTERNS[@]}"; do
        if [[ "$filename" =~ $pattern ]]; then
            return 0
        fi
    done

    return 1
}

is_obsolete() {
    local filename=$1

    for pattern in "${OBSOLETE_PATTERNS[@]}"; do
        if [[ "$filename" =~ $pattern ]]; then
            return 0
        fi
    done

    return 1
}

is_preserved() {
    local filename=$1

    for pfile in "${PRESERVE_FILES[@]}"; do
        if [[ "$filename" == "$pfile" ]]; then
            return 0
        fi
    done

    return 1
}

move_file() {
    local file=$1
    local filename=$(basename "$file")
    local dir=$(dirname "$file")

    # Create backup
    cp "$file" "$BACKUP_DIR/$filename"

    # Move to documentation
    cp "$file" "$DOCS_DIR/$filename"
    rm "$file"

    log "  ${GREEN}✓${NC} MOVED: $file → documentation/"
    ((MOVED++))
}

delete_file() {
    local file=$1
    local filename=$(basename "$file")

    # Create backup
    cp "$file" "$BACKUP_DIR/$filename"

    # Delete
    rm "$file"

    log "  ${RED}🗑️${NC} DELETED: $file"
    ((DELETED++))
}

preserve_file() {
    local filename=$1

    log "  ${YELLOW}📌${NC} PRESERVED: $filename (project config)"
    ((PRESERVED++))
}

###############################################################################
# Main Processing
###############################################################################

# Find all .md files, excluding vendor directories
while IFS= read -r md_file; do
    # Skip if should be skipped
    if should_skip "$md_file"; then
        ((SKIPPED++))
        continue
    fi

    filename=$(basename "$md_file")
    dir=$(dirname "$md_file")

    ((REVIEWED++))

    # Check if file should be preserved
    if is_preserved "$filename"; then
        preserve_file "$filename"
        continue
    fi

    # Validate markdown
    if ! validate_markdown "$md_file"; then
        log "  ${RED}❌${NC} INVALID: $md_file (empty or no markdown structure)"
        ((INVALID++))
        continue
    fi

    # Check if obsolete (delete these first)
    if is_obsolete "$filename"; then
        delete_file "$md_file"
        continue
    fi

    # Check if important (move these)
    if is_important "$filename"; then
        move_file "$md_file"
        continue
    fi

    # Location-specific handling
    is_in_monitoring_location=0
    for loc in "${LOCATION_RULES[@]}"; do
        if is_in_location "$md_file" "$loc"; then
            is_in_monitoring_location=1
            break
        fi
    done

    if [[ $is_in_monitoring_location -eq 1 ]]; then
        # These are in specialized locations; they're safe to delete if not important
        delete_file "$md_file"
        continue
    fi

    # Default: if it has content but not matching any pattern, ask what to do
    log "  ${YELLOW}❓${NC} UNKNOWN: $md_file"
    log "     Recommendation: Review manually (not matching criteria)"
done < <(find "$PROJECT_ROOT" -name "*.md" -type f | grep -v "\.git/" | grep -v "venv/" | grep -v "node_modules/" | grep -v "installerFiles/" | grep -v "loki/" | grep -v "mcp/gguf/")

###############################################################################
# Summary Report
###############################################################################

log ""
log "${BLUE}=== Global Cleanup Summary ===${NC}"
log "Files reviewed: ${CYAN}$REVIEWED${NC}"
log "Files moved to /documentation/: ${GREEN}$MOVED${NC}"
log "Files deleted: ${RED}$DELETED${NC}"
log "Files preserved: ${YELLOW}$PRESERVED${NC}"
log "Invalid files: ${RED}$INVALID${NC}"
log "Files skipped (vendor/dependencies): ${CYAN}$SKIPPED${NC}"
log ""

if [[ $DELETED -gt 0 ]]; then
    log "${YELLOW}⚠️  Backup created in: ${BACKUP_DIR}${NC}"
    log "   Restore with: cp ${BACKUP_DIR}/* ."
fi

log "${GREEN}✅ Global cleanup complete!${NC}"
log "   Full log: $LOG_FILE"

# Also print to stdout
echo ""
echo -e "${BLUE}=== Global Cleanup Summary ===${NC}"
echo -e "Files reviewed: ${CYAN}$REVIEWED${NC}"
echo -e "Files moved to /documentation/: ${GREEN}$MOVED${NC}"
echo -e "Files deleted: ${RED}$DELETED${NC}"
echo -e "Files preserved: ${YELLOW}$PRESERVED${NC}"
echo -e "Invalid files: ${RED}$INVALID${NC}"
echo -e "Files skipped (vendor/dependencies): ${CYAN}$SKIPPED${NC}"
echo ""

if [[ $DELETED -gt 0 ]]; then
    echo -e "${YELLOW}⚠️  Backup created at: ${BACKUP_DIR}${NC}"
fi

echo -e "${GREEN}✅ Global cleanup complete!${NC}"
echo ""

# Show documentation directory stats
doc_count=$(find "$DOCS_DIR" -name "*.md" -type f | wc -l)
echo -e "${CYAN}Documentation files: $doc_count${NC}"
echo ""

# Show log location
echo -e "Full log saved to: ${CYAN}$LOG_FILE${NC}"

# Exit successfully
exit 0
