#!/bin/bash
###############################################################################
# Wegweiser Documentation Cleanup Script
#
# Automatically organizes markdown files in the project root:
# - Moves important documentation to /documentation/
# - Deletes status reports and implementation files
# - Preserves project configuration files
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
LOG_FILE="$PROJECT_ROOT/wlog/md_cleanup.log"
BACKUP_DIR="$PROJECT_ROOT/.backup/md_cleanup_$(date +%s)"

# Files to always preserve in root
PRESERVE_FILES=("CLAUDE.md")

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
)

# Stats
MOVED=0
DELETED=0
PRESERVED=0
INVALID=0

# Ensure directories exist
mkdir -p "$DOCS_DIR"
mkdir -p "${BACKUP_DIR}"
mkdir -p "$(dirname "$LOG_FILE")"

# Initialize log
{
    echo "=== Markdown Cleanup Log ==="
    echo "Timestamp: $(date)"
    echo "Project Root: $PROJECT_ROOT"
    echo ""
} > "$LOG_FILE"

echo -e "${CYAN}=== Wegweiser Documentation Cleanup ===${NC}"
echo -e "${CYAN}Project Root: $PROJECT_ROOT${NC}"
echo ""

###############################################################################
# Helper Functions
###############################################################################

log() {
    echo "$1" | tee -a "$LOG_FILE"
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

    # Create backup
    cp "$file" "$BACKUP_DIR/$filename"

    # Move to documentation
    cp "$file" "$DOCS_DIR/$filename"
    rm "$file"

    log "  ${GREEN}✓${NC} MOVED: $filename → documentation/"
    ((MOVED++))
}

delete_file() {
    local file=$1
    local filename=$(basename "$file")

    # Create backup
    cp "$file" "$BACKUP_DIR/$filename"

    # Delete
    rm "$file"

    log "  ${RED}🗑️${NC} DELETED: $filename (obsolete)"
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

log ""
log "${BLUE}Scanning markdown files in root directory...${NC}"
log ""

# Process each .md file in root
for md_file in "$PROJECT_ROOT"/*.md; do
    # Skip if no .md files found
    [[ -e "$md_file" ]] || continue

    filename=$(basename "$md_file")

    # Check if file should be preserved
    if is_preserved "$filename"; then
        preserve_file "$filename"
        continue
    fi

    # Validate markdown
    if ! validate_markdown "$md_file"; then
        log "  ${RED}❌${NC} INVALID: $filename (empty or no markdown structure)"
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

    # Default: if it has content but not matching any pattern, ask what to do
    log "  ${YELLOW}❓${NC} UNKNOWN: $filename (doesn't match criteria)"
    log "     First 20 chars: $(head -c 50 "$md_file" | tr '\n' ' ')..."
    log "     Recommendation: Review and delete or move manually"
done

###############################################################################
# Summary Report
###############################################################################

log ""
log "${BLUE}=== Cleanup Summary ===${NC}"
log "Files moved to /documentation/: ${GREEN}$MOVED${NC}"
log "Files deleted: ${RED}$DELETED${NC}"
log "Files preserved: ${YELLOW}$PRESERVED${NC}"
log "Invalid files: ${RED}$INVALID${NC}"
log ""

if [[ $DELETED -gt 0 ]]; then
    log "${YELLOW}⚠️  Backup created in: ${BACKUP_DIR}${NC}"
    log "   Restore with: cp ${BACKUP_DIR}/* ."
fi

log "${GREEN}✅ Cleanup complete!${NC}"
log "   Full log: $LOG_FILE"

# Also print to stdout
echo ""
echo -e "${BLUE}=== Cleanup Summary ===${NC}"
echo -e "Files moved to /documentation/: ${GREEN}$MOVED${NC}"
echo -e "Files deleted: ${RED}$DELETED${NC}"
echo -e "Files preserved: ${YELLOW}$PRESERVED${NC}"
echo -e "Invalid files: ${RED}$INVALID${NC}"
echo ""

if [[ $DELETED -gt 0 ]]; then
    echo -e "${YELLOW}⚠️  Backup created at: ${BACKUP_DIR}${NC}"
fi

echo -e "${GREEN}✅ Cleanup complete!${NC}"
echo ""

# Show documentation directory stats
doc_count=$(find "$DOCS_DIR" -name "*.md" -type f | wc -l)
echo -e "${CYAN}Documentation files: $doc_count${NC}"
echo ""

# Show log location
echo -e "Full log saved to: ${CYAN}$LOG_FILE${NC}"

# Exit successfully
exit 0
