#!/usr/bin/env python3
"""
Global Markdown Cleanup Script

Scans the entire project for stray markdown files and organizes them:
- Moves important project docs to /documentation/
- Deletes status reports and implementation files
- Preserves configuration files
- Skips vendor directories
"""

import os
import shutil
import sys
from pathlib import Path
from datetime import datetime

# Colors
RED = '\033[0;31m'
GREEN = '\033[0;32m'
YELLOW = '\033[1;33m'
BLUE = '\033[0;34m'
CYAN = '\033[0;36m'
NC = '\033[0m'

# Configuration
PROJECT_ROOT = Path(sys.argv[1]) if len(sys.argv) > 1 else Path.cwd()
DOCS_DIR = PROJECT_ROOT / "documentation"
BACKUP_DIR = PROJECT_ROOT / ".backup" / f"md_cleanup_{int(datetime.now().timestamp())}"

# Files to always preserve
PRESERVE_FILES = {"CLAUDE.md"}

# Directories to skip
SKIP_DIRS = {".git", "venv", "node_modules", "installerFiles", "loki", "mcp/gguf"}

# Important documentation patterns
IMPORTANT_PATTERNS = {
    "README", "SETUP", "GUIDE", "QUICKSTART", "ARCHITECTURE",
    "DEVELOPER", "SECURITY", "API", "REFERENCE", "PORTABILITY",
    "DESIGN", "MECHANISM", "FIX_LOG", "BACKGROUND_OPTIONS", "NATS",
    "INTEGRATION", "CORE", "DATA", "FEATURES", "INFRASTRUCTURE",
    "TESTING", "GLOSSARY", "STRUCTURE"
}

# Obsolete patterns
OBSOLETE_PATTERNS = {
    "READY", "COMPLETE", "CHECKLIST", "SUMMARY", "IMPLEMENTATION",
    "DEPLOYMENT_GUIDE", "MCP_DEPLOYMENT", "AGENT_UPDATE_IMPLEMENTATION",
    "PHASE_", "DESIGN_CHANGES", "DRIVE_DATA_FIX", "KEYVAULT_MIGRATION",
    "NEXT_DESIGN", "ROUTES_MISSING", "SIDEBAR_", "UNIFIED_CHAT",
    "TESTING_CHECKLIST", "STACK", "SETUP_SUMMARY"
}

# Location-specific rules
LOCATION_RULES = {
    "dev_scripts/monitoring": True  # These guides are implementation-specific
}

# Stats
stats = {
    "moved": 0,
    "deleted": 0,
    "preserved": 0,
    "invalid": 0,
    "skipped": 0,
    "reviewed": 0
}

def should_skip(path):
    """Check if path should be skipped"""
    path_str = str(path)
    for skip_dir in SKIP_DIRS:
        if skip_dir in path_str:
            return True
    return False

def validate_markdown(file_path):
    """Validate if file has markdown content"""
    try:
        if not file_path.stat().st_size > 0:
            return False
        with open(file_path, 'r', errors='ignore') as f:
            content = f.read()
            return '#' in content or len(content.split('\n')) > 5
    except:
        return False

def is_important(filename):
    """Check if filename matches important patterns"""
    filename_upper = filename.upper()
    for pattern in IMPORTANT_PATTERNS:
        if pattern in filename_upper:
            return True
    return False

def is_obsolete(filename):
    """Check if filename matches obsolete patterns"""
    filename_upper = filename.upper()
    for pattern in OBSOLETE_PATTERNS:
        if pattern in filename_upper:
            return True
    return False

def is_in_location(path_str, location):
    """Check if file is in a specific location"""
    return location in path_str

def is_preserved(filename):
    """Check if file should be preserved"""
    return filename in PRESERVE_FILES

def log_msg(msg):
    """Print and log message"""
    print(msg)

def process_files():
    """Process all markdown files"""
    global stats

    # Create backup directory
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    DOCS_DIR.mkdir(parents=True, exist_ok=True)

    log_msg(f"{CYAN}=== Global Markdown Cleanup ==={NC}")
    log_msg(f"{CYAN}Project Root: {PROJECT_ROOT}{NC}")
    log_msg(f"{CYAN}Scanning all directories (excluding vendor/dependencies){NC}")
    log_msg("")

    # Find all .md files
    md_files = sorted(PROJECT_ROOT.rglob("*.md"))

    for md_file in md_files:
        # Skip if in excluded directory
        if should_skip(md_file):
            stats["skipped"] += 1
            continue

        filename = md_file.name
        path_str = str(md_file)

        stats["reviewed"] += 1

        # Check if should be preserved
        if is_preserved(filename):
            log_msg(f"  {YELLOW}📌{NC} PRESERVED: {filename}")
            stats["preserved"] += 1
            continue

        # Validate markdown
        if not validate_markdown(md_file):
            log_msg(f"  {RED}❌{NC} INVALID: {path_str}")
            stats["invalid"] += 1
            continue

        # Check if obsolete
        if is_obsolete(filename):
            try:
                BACKUP_DIR.mkdir(parents=True, exist_ok=True)
                shutil.copy2(md_file, BACKUP_DIR / filename)
                md_file.unlink()
                log_msg(f"  {RED}🗑️{NC} DELETED: {path_str}")
                stats["deleted"] += 1
            except Exception as e:
                log_msg(f"  {RED}ERROR{NC} deleting {filename}: {e}")
            continue

        # Check if important
        if is_important(filename):
            try:
                BACKUP_DIR.mkdir(parents=True, exist_ok=True)
                shutil.copy2(md_file, BACKUP_DIR / filename)
                shutil.copy2(md_file, DOCS_DIR / filename)
                md_file.unlink()
                log_msg(f"  {GREEN}✓{NC} MOVED: {path_str} → documentation/")
                stats["moved"] += 1
            except Exception as e:
                log_msg(f"  {RED}ERROR{NC} moving {filename}: {e}")
            continue

        # Location-specific handling
        for location in LOCATION_RULES:
            if is_in_location(path_str, location):
                try:
                    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(md_file, BACKUP_DIR / filename)
                    md_file.unlink()
                    log_msg(f"  {RED}🗑️{NC} DELETED: {path_str} (location-specific)")
                    stats["deleted"] += 1
                except Exception as e:
                    log_msg(f"  {RED}ERROR{NC} deleting {filename}: {e}")
                break
        else:
            # Unknown classification
            log_msg(f"  {YELLOW}❓{NC} UNKNOWN: {path_str}")

    # Print summary
    log_msg("")
    log_msg(f"{BLUE}=== Global Cleanup Summary ==={NC}")
    log_msg(f"Files reviewed: {CYAN}{stats['reviewed']}{NC}")
    log_msg(f"Files moved to /documentation/: {GREEN}{stats['moved']}{NC}")
    log_msg(f"Files deleted: {RED}{stats['deleted']}{NC}")
    log_msg(f"Files preserved: {YELLOW}{stats['preserved']}{NC}")
    log_msg(f"Invalid files: {RED}{stats['invalid']}{NC}")
    log_msg(f"Files skipped (vendor/dependencies): {CYAN}{stats['skipped']}{NC}")
    log_msg("")

    if stats["deleted"] > 0:
        log_msg(f"{YELLOW}⚠️  Backup created in: {BACKUP_DIR}{NC}")

    log_msg(f"{GREEN}✅ Global cleanup complete!{NC}")
    log_msg("")

    # Show documentation stats
    doc_count = len(list(DOCS_DIR.glob("*.md")))
    log_msg(f"{CYAN}Documentation files: {doc_count}{NC}")

if __name__ == "__main__":
    try:
        process_files()
    except Exception as e:
        print(f"{RED}Error: {e}{NC}")
        sys.exit(1)
