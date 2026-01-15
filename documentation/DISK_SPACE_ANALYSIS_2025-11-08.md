# Comprehensive Disk Space Analysis - 2025-11-08

## Executive Summary

**Total Disk Usage**: 26GB / 29GB (89% full, 3.5GB free)

**Critical Finding**: The server is still critically low on disk space despite recent cleanup. Major space consumers have been identified across multiple locations, with **device event logs** and **git repository** being the largest offenders.

## Top-Level Directory Breakdown

| Directory | Size | % of Total | Status |
|-----------|------|------------|--------|
| `/opt` | 7.8GB | 27% | **CRITICAL** |
| `/home` | 7.3GB | 25% | **CRITICAL** |
| `/usr` | 5.1GB | 18% | Normal (system) |
| `/var` | 4.3GB | 15% | **WARNING** |
| `/snap` | 1.9GB | 7% | Normal (system) |
| `/root` | 645MB | 2% | Normal |
| `/boot` | 510MB | 2% | Normal |

## Critical Space Consumers (Detailed Analysis)

### 1. `/opt/wegweiser` - 7.6GB (26% of total disk)

#### 1.1 Device Event Logs - **4.1GB** ⚠️ HIGHEST PRIORITY
**Location**: `/opt/wegweiser/deviceFiles/`
- **112 device directories** containing event logs and system information
- **326 total files** (JSON and TXT formats)
- **190 files older than 30 days** (potential for cleanup)

**Largest Individual Files**:
- `afebc936-1627-485c-9667-e0e4ecdb4528/events-Security.json` - **713MB** (Sep 28)
- `510a188e-ca5b-48cc-8fe7-173f14fa8928/events-Security.json` - **238MB** (date varies)
- `7c8d1b73-11fa-462e-8111-63e5fc88ac3f/events-Security.json` - **170MB** (Oct 20)

**File Type Breakdown**:
- **48 Security event logs** (events-Security.json) - Average 20-30MB each, some up to 713MB
- **Application event logs** (events-Application.json) - 20-75MB each
- **System event logs** (events-System.json) - 20-53MB each
- **MSInfo files** (msinfo.txt) - 7-30MB each
- **5 dummy.txt files** - 30MB each (150MB total - test files?)
- **1 journal.json** - 57MB

**Recommendation**: 
- Delete dummy.txt files immediately (150MB)
- Implement retention policy for event logs (suggest 30-60 days)
- Archive or compress old event logs
- **Potential savings: 2-3GB**

#### 1.2 Git Repository - **2.2GB** ⚠️ HIGH PRIORITY
**Location**: `/opt/wegweiser/.git/`

**Git Pack Files**:
- `pack-e0d91cda249ce570ff50aa778983e68e844bdd62.pack` - **984MB**
- `pack-aa1c845219fdfdd8f7da3a2b36f1990638aab593.pack` - **387MB**
- `pack-44e672d1c0ca1c6232174dfb360215a296d03ede.pack` - **272MB**
- `pack-6dc992053d3cb2596e066603afbabaa8fa63c062.pack` - **68MB**

**Issue**: Git repository contains large binary files or extensive history

**Recommendation**:
- Run `git gc --aggressive --prune=now` to optimize
- Consider using Git LFS for large binary files
- Review git history for accidentally committed large files
- Consider shallow clone for production server
- **Potential savings: 500MB-1GB**

#### 1.3 Python Virtual Environment - **473MB**
**Location**: `/opt/wegweiser/venv/`
**Status**: Normal for Python application with dependencies

#### 1.4 Downloads Directory - **395MB**
**Location**: `/opt/wegweiser/downloads/`
**Recommendation**: Review contents, may contain old installers or temporary files

#### 1.5 Application Code - **225MB**
**Location**: `/opt/wegweiser/app/`
**Status**: Normal

#### 1.6 Loki Scanner - **154MB**
**Location**: `/opt/wegweiser/Loki/`
**Status**: Normal (security scanning tool)

#### 1.7 Installer Files - **122MB**
**Location**: `/opt/wegweiser/installerFiles/`
**Status**: Normal (agent installers)

### 2. `/home/andrei` - 7.3GB (25% of total disk)

#### 2.1 VSCode Server - **3.6GB** ⚠️ HIGH PRIORITY
**Location**: `/home/andrei/.vscode-server/`

**Breakdown**:
- `data/` - **1.3GB** (workspace storage, caches, checkpoints)
- `extensions/` - **1.2GB** (installed extensions)
- `cli/servers/` - **1.1GB** (5 different server versions, ~220MB each)
- Multiple code versions - **120MB** (5 versions × 24MB)

**Issue**: Multiple VSCode server versions installed, large workspace caches

**Recommendation**:
- Clean up old VSCode server versions (keep latest only)
- Clear workspace storage caches
- Remove unused extensions
- **Potential savings: 1-2GB**

#### 2.2 Node Version Manager - **1.1GB**
**Location**: `/home/andrei/.nvm/`
**Contains**: Node.js v22.21.1 installation
**Status**: Normal if Node.js is required

#### 2.3 Old Wegweiser Backup - **984MB** ⚠️ IMMEDIATE ACTION
**Location**: `/home/andrei/wegweiser_old_20251010_192545.tar.gz`
**Date**: October 10, 2025
**Recommendation**: Move to external storage or delete if no longer needed
**Potential savings: 984MB**

#### 2.4 NPM Cache - **387MB**
**Location**: `/home/andrei/.npm/`
**Recommendation**: Run `npm cache clean --force`
**Potential savings: 200-300MB**

#### 2.5 Cursor Server - **370MB**
**Location**: `/home/andrei/.cursor-server/`
**Status**: Normal if Cursor IDE is in use

#### 2.6 Unknown File - **112MB** ⚠️
**Location**: `/home/andrei/zi3fm04N`
**Type**: Unknown binary file
**Date**: October 10, 2025
**Recommendation**: Investigate and delete if not needed

#### 2.7 Test Agent - **80MB**
**Location**: `/home/andrei/test_agent/`
**Recommendation**: Delete if testing is complete

### 3. `/var` - 4.3GB (15% of total disk)

#### 3.1 PostgreSQL Database - **2.3GB**
**Location**: `/var/lib/postgresql/`

**Large Database Files** (>100MB each):
- `base/16385/402512` - Database table file
- `base/16385/18779` - Database table file
- `base/16385/20614` - Database table file
- `base/16385/20619` - Database table file
- `base/16385/18207` - Database table file

**Status**: Normal for production database
**Recommendation**: 
- Review database for old/unused data
- Consider archiving old records
- Run `VACUUM FULL` to reclaim space

#### 3.2 Snap Packages - **1.1GB**
**Location**: `/var/lib/snapd/`
**Status**: Normal (system packages)
**Recommendation**: Run `snap list --all` and remove old revisions

#### 3.3 System Logs - **317MB**
**Location**: `/var/log/`

**Breakdown**:
- `journal/` - **104MB** (systemd journal)
- `azure/` - **14MB** (Azure agent logs)
- `wegweiser/` - **12MB** (application logs)
- Other system logs - **187MB**

**Status**: Acceptable after recent cleanup
**Recommendation**: Monitor journal size, consider reducing retention

## Summary of Recommendations by Priority

### IMMEDIATE ACTION (Can be done now)
1. ✅ **Delete dummy.txt files** - Saves 150MB
2. ✅ **Delete old wegweiser backup** - Saves 984MB
3. ✅ **Delete unknown file (zi3fm04N)** - Saves 112MB
4. ✅ **Delete test_agent directory** - Saves 80MB
5. ✅ **Clean NPM cache** - Saves 200-300MB
**Total Immediate Savings: ~1.5GB**

### HIGH PRIORITY (Requires planning)
6. ⚠️ **Implement device file retention policy** - Saves 2-3GB
7. ⚠️ **Clean up old VSCode server versions** - Saves 1-2GB
8. ⚠️ **Optimize Git repository** - Saves 500MB-1GB
**Total High Priority Savings: 4-6GB**

### MEDIUM PRIORITY (Ongoing maintenance)
9. Review and clean downloads directory
10. Archive old PostgreSQL data
11. Remove old snap package revisions
12. Monitor and limit systemd journal size

## Projected Disk Usage After Cleanup

| Action | Current | After Cleanup | Free Space |
|--------|---------|---------------|------------|
| Current State | 26GB / 29GB | - | 3.5GB (89%) |
| After Immediate Actions | - | 24.5GB / 29GB | 5GB (84%) |
| After High Priority Actions | - | 19-21GB / 29GB | 8-10GB (66-72%) |

## Recommended Retention Policies

### Device Event Logs
- **Security logs**: 60 days
- **Application logs**: 30 days
- **System logs**: 30 days
- **MSInfo files**: 90 days (smaller, useful for reference)
- **Dummy/test files**: Delete immediately

### Application Logs
- **Active logs**: 7 days (already configured)
- **Compressed logs**: 30 days
- **Payloads**: 3-7 days (already configured)

### Development Files
- **VSCode server versions**: Keep latest 2 versions only
- **NPM cache**: Clean monthly
- **Test directories**: Clean after testing complete

## Cleanup Scripts Created

### 1. Comprehensive Cleanup Script
**File**: `/opt/wegweiser/scripts/cleanup_disk_space.sh`
**Purpose**: Performs all immediate and high-priority cleanup actions
**Actions**:
- Deletes dummy.txt test files
- Removes old backups and unknown files
- Cleans NPM cache
- Removes old device event logs (>60 days)
- Cleans old VSCode server versions
- Removes old snap package revisions

**Usage**:
```bash
sudo /opt/wegweiser/scripts/cleanup_disk_space.sh
```

### 2. Device Files Retention Script
**File**: `/opt/wegweiser/scripts/cleanup_device_files.sh`
**Purpose**: Manages device file retention policies
**Retention Policies**:
- Security logs: 60 days
- Application logs: 30 days
- System logs: 30 days
- Journal files: 30 days
- MSInfo files: 90 days
- Services files: 90 days
- Dummy files: Immediate deletion

**Usage**:
```bash
# Dry run (preview only)
sudo /opt/wegweiser/scripts/cleanup_device_files.sh --dry-run

# Actual cleanup
sudo /opt/wegweiser/scripts/cleanup_device_files.sh
```

### 3. Automated Log Cleanup (Already Configured)
**File**: `/opt/wegweiser/scripts/cleanup_logs.sh`
**Schedule**: Daily at 2:00 AM via systemd timer
**Purpose**: Cleans application logs and payloads

## File Count Analysis

### Device Files Directory
- **Total device directories**: 112
- **Total files**: 326
- **Files older than 30 days**: 190 (58% of total)
- **Security event logs**: 48 files
- **Dummy test files**: 5 files (150MB)

### Largest Individual Files
1. `events-Security.json` (afebc936...) - **713MB**
2. `events-Security.json` (510a188e...) - **238MB**
3. `events-Security.json` (7c8d1b73...) - **170MB**
4. `events-Security.json` (59e617d6...) - **96MB**
5. `events-Application.json` (510a188e...) - **74MB**

## Git Repository Analysis

### Pack Files (Total: 1.7GB)
The git repository contains 4 pack files totaling 1.7GB, suggesting:
- Large binary files may have been committed
- Extensive commit history
- Possible need for Git LFS

### Recommended Git Cleanup
```bash
# Check for large files in git history
git rev-list --objects --all | \
  git cat-file --batch-check='%(objecttype) %(objectname) %(objectsize) %(rest)' | \
  sed -n 's/^blob //p' | \
  sort --numeric-sort --key=2 | \
  tail -20

# Optimize repository
git gc --aggressive --prune=now

# Consider using Git LFS for large files
git lfs migrate import --include="*.exe,*.msi,*.zip,*.tar.gz"
```

## Monitoring and Alerts

### Critical Thresholds
- **Disk usage > 85%**: Immediate action required
- **Disk usage > 75%**: Warning, plan cleanup
- **Device files > 5GB**: Review retention policies
- **Git repo > 3GB**: Investigate and optimize
- **VSCode server > 4GB**: Clean old versions

### Recommended Monitoring Commands
```bash
# Daily disk check
df -h / | grep -E "/dev/root"

# Check largest directories
du -sh /opt/wegweiser/deviceFiles /opt/wegweiser/.git /home/andrei/.vscode-server

# Count old device files
find /opt/wegweiser/deviceFiles -name "events-*.json" -mtime +60 | wc -l

# Check git repository size
du -sh /opt/wegweiser/.git
```

## Next Steps

1. **Run comprehensive cleanup script** to free immediate space
2. **Review device file retention** and adjust policies if needed
3. **Optimize git repository** to reduce .git directory size
4. **Set up monitoring alerts** for disk space thresholds
5. **Schedule regular reviews** of disk usage (weekly/monthly)
6. **Consider disk expansion** if usage remains high after cleanup

## Conclusion

The server has **multiple large space consumers** that can be addressed:
- **Device event logs** (4.1GB) - Largest offender, needs retention policy
- **Git repository** (2.2GB) - Needs optimization
- **VSCode server** (3.6GB) - Multiple versions, needs cleanup
- **Old backups** (1GB+) - Can be removed immediately

**Estimated total recoverable space: 5-8GB** (bringing usage down to 60-70%)

With proper retention policies and regular cleanup, the server should maintain healthy disk space levels.

