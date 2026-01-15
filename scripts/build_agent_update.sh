#!/bin/bash
# Filepath: scripts/build_agent_update.sh
# Build agent update package with version manifest and SHA256 hash
#
# Usage: ./build_agent_update.sh <version> <platform> [changelog]
# Example: ./build_agent_update.sh 3.0.2 Linux "Bug fixes and performance improvements"

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored output
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check arguments
if [ $# -lt 2 ]; then
    log_error "Usage: $0 <version> <platform> [changelog]"
    log_error "Example: $0 3.0.2 Linux 'Bug fixes and performance improvements'"
    log_error ""
    log_error "Platforms: Linux, MacOS, Windows"
    exit 1
fi

VERSION=$1
PLATFORM=$2
CHANGELOG=${3:-"Agent update $VERSION"}

# Validate platform
if [[ ! "$PLATFORM" =~ ^(Linux|MacOS|Windows)$ ]]; then
    log_error "Invalid platform: $PLATFORM"
    log_error "Valid platforms: Linux, MacOS, Windows"
    exit 1
fi

# Paths
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BASE_DIR="$(dirname "$SCRIPT_DIR")"
SOURCE_DIR="$BASE_DIR/installerFiles/$PLATFORM/Agent"
OUTPUT_DIR="$BASE_DIR/installerFiles/$PLATFORM/updates"
OUTPUT_FILE="$OUTPUT_DIR/agent-$VERSION.tar.gz"
HASH_FILE="$OUTPUT_FILE.sha256"
MANIFEST_FILE="$SOURCE_DIR/VERSION_MANIFEST.json"

log_info "Building agent update package"
log_info "Version: $VERSION"
log_info "Platform: $PLATFORM"
log_info "Source: $SOURCE_DIR"
log_info "Output: $OUTPUT_FILE"

# Check if source directory exists
if [ ! -d "$SOURCE_DIR" ]; then
    log_error "Source directory not found: $SOURCE_DIR"
    exit 1
fi

# Create output directory
log_info "Creating output directory: $OUTPUT_DIR"
mkdir -p "$OUTPUT_DIR"

# Check if update package already exists
if [ -f "$OUTPUT_FILE" ]; then
    log_warn "Update package already exists: $OUTPUT_FILE"
    read -p "Overwrite? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        log_info "Aborted by user"
        exit 0
    fi
    rm -f "$OUTPUT_FILE" "$HASH_FILE"
fi

# Create version manifest
log_info "Creating version manifest"
cat > "$MANIFEST_FILE" <<EOF
{
  "version": "$VERSION",
  "build_date": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "platform": "$PLATFORM",
  "changelog": "$CHANGELOG",
  "builder": "$(whoami)@$(hostname)",
  "build_machine": "$(uname -a)"
}
EOF

log_info "Manifest created: $MANIFEST_FILE"
cat "$MANIFEST_FILE"

# Create tarball
log_info "Creating tarball..."
cd "$(dirname "$SOURCE_DIR")"
tar -czf "$OUTPUT_FILE" "$(basename "$SOURCE_DIR")" 2>&1 | grep -v "Removing leading" || true

if [ ! -f "$OUTPUT_FILE" ]; then
    log_error "Failed to create tarball"
    exit 1
fi

# Get file size
FILE_SIZE=$(stat -f%z "$OUTPUT_FILE" 2>/dev/null || stat -c%s "$OUTPUT_FILE" 2>/dev/null)
FILE_SIZE_MB=$(echo "scale=2; $FILE_SIZE / 1024 / 1024" | bc)

log_info "Tarball created successfully"
log_info "Size: $FILE_SIZE_MB MB ($FILE_SIZE bytes)"

# Generate SHA256 hash
log_info "Generating SHA256 hash..."
if command -v sha256sum &> /dev/null; then
    SHA256=$(sha256sum "$OUTPUT_FILE" | awk '{print $1}')
elif command -v shasum &> /dev/null; then
    SHA256=$(shasum -a 256 "$OUTPUT_FILE" | awk '{print $1}')
else
    log_error "Neither sha256sum nor shasum found"
    exit 1
fi

echo "$SHA256" > "$HASH_FILE"

log_info "SHA256 hash: $SHA256"
log_info "Hash file: $HASH_FILE"

# Verify the package can be extracted
log_info "Verifying package integrity..."
TEMP_VERIFY_DIR=$(mktemp -d)
tar -tzf "$OUTPUT_FILE" > /dev/null 2>&1
if [ $? -eq 0 ]; then
    log_info "Package integrity verified successfully"
else
    log_error "Package integrity verification failed"
    rm -rf "$TEMP_VERIFY_DIR"
    exit 1
fi
rm -rf "$TEMP_VERIFY_DIR"

# Summary
log_info ""
log_info "========================================="
log_info "Update Package Build Complete!"
log_info "========================================="
log_info "Version:    $VERSION"
log_info "Platform:   $PLATFORM"
log_info "Package:    $OUTPUT_FILE"
log_info "Size:       $FILE_SIZE_MB MB"
log_info "SHA256:     $SHA256"
log_info "Changelog:  $CHANGELOG"
log_info "========================================="
log_info ""
log_info "Next steps:"
log_info "1. Test the update package on a non-production device"
log_info "2. Deploy via Admin UI: https://app.wegweiser.tech/admin/agent-updates"
log_info "3. Monitor update deployment in the update history"
log_info ""
log_info "Update URL for deployment:"
log_info "https://app.wegweiser.tech/installerFiles/$PLATFORM/updates/agent-$VERSION.tar.gz"
