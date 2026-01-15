# Wegweiser Log Management

## Overview

This document describes the log management strategy for Wegweiser, including what gets logged, where logs are stored, and how they are cleaned up.

## Log Locations

### Application Logs
- **Location**: `/opt/wegweiser/wlog/`
- **Files**:
  - `wegweiser.log` - Main application log (errors, warnings, info)
  - `gunicorn_error.log` - Gunicorn error log (if enabled)
  - Other application-specific logs

### System Logs
- **Location**: `/var/log/wegweiser/`
- **Files**:
  - `device_backups/` - Device backup JSON files
  - `tenant_backups/` - Tenant backup JSON files
  - Historical gunicorn logs (now disabled)

### Payload Data
- **Location**: `/opt/wegweiser/payloads/`
- **Directories**:
  - `queue/` - Incoming payloads waiting to be processed
  - `sucessfulImport/` - Successfully processed payloads (kept for 3 days)
  - `invalid/` - Invalid payloads (kept for 7 days)
  - `ophanedCollectors/` - Orphaned collector data (kept for 7 days)
  - `noDeviceUuid/` - Payloads without device UUID

## What Gets Logged

### Gunicorn Access Logs
**Status**: DISABLED (as of 2025-11-08)

Previously, gunicorn was logging every HTTP request, including high-frequency metrics API calls (every 2 seconds). This resulted in:
- 2.3GB `gunicorn_access.log` file
- Disk space exhaustion
- Redis write failures

**Configuration**: `gunicorn.conf.py` line 17: `accesslog = None`

### Application Logs
Controlled by `app/utilities/app_logging_helper.py` and configurable via the admin panel:
- **ERROR**: Always logged (critical failures, exceptions)
- **WARNING**: Always logged (Redis failures, IP blocks, degraded operations)
- **INFO**: Configurable (general operations, successful actions)
- **DEBUG**: Configurable (detailed debugging information)

### What Caused the Disk Space Issue

1. **Gunicorn Access Logs** (2.3GB): High-frequency metrics polling every 2 seconds
2. **Compressed System Logs** (100MB+): Old `.gz` files in `/var/log`
3. **Old Payloads** (224MB): Successfully imported payloads kept indefinitely

## Log Rotation Strategy

### Logrotate Configuration
- **File**: `/etc/logrotate.d/wegweiser`
- **Rotation**: Daily
- **Retention**: 7 days
- **Compression**: Yes (delayed by 1 day)
- **Action**: Reload Wegweiser service after rotation

### Automatic Cleanup
- **Service**: `wegweiser-log-cleanup.service`
- **Timer**: `wegweiser-log-cleanup.timer`
- **Schedule**: Daily at 2:00 AM UTC
- **Script**: `/opt/wegweiser/scripts/cleanup_logs.sh`

### Cleanup Rules
| Location | Pattern | Retention |
|----------|---------|-----------|
| `/opt/wegweiser/wlog/` | `*.log.*`, `*.gz` | 7 days |
| `/var/log/wegweiser/` | `*.log.*`, `*.gz` | 7 days |
| Device backups | `*.json` | 7 days |
| Tenant backups | `*.json` | 7 days |
| Successful imports | `*` | 3 days |
| Invalid payloads | `*` | 7 days |
| Orphaned collectors | `*` | 7 days |
| Large log files | `*.log` > 100MB | Truncated to last 1000 lines |

## Manual Operations

### Run Cleanup Manually
```bash
sudo /opt/wegweiser/scripts/cleanup_logs.sh
```

### Force Logrotate
```bash
sudo logrotate -f /etc/logrotate.d/wegweiser
```

### Check Timer Status
```bash
systemctl status wegweiser-log-cleanup.timer
systemctl list-timers wegweiser-log-cleanup.timer
```

### View Cleanup Logs
```bash
journalctl -u wegweiser-log-cleanup.service
```

### Check Disk Usage
```bash
df -h /
du -sh /opt/wegweiser/wlog /var/log/wegweiser /opt/wegweiser/payloads
```

## Monitoring Recommendations

### Disk Space Alerts
Set up monitoring to alert when:
- Root filesystem usage > 85%
- `/opt/wegweiser/wlog/` > 500MB
- `/var/log/wegweiser/` > 500MB
- `/opt/wegweiser/payloads/` > 1GB

### Log File Size Alerts
Monitor individual log files:
- Any `.log` file > 100MB should trigger investigation
- Rapid growth (>100MB/day) indicates a problem

### Redis Health
Monitor Redis for:
- `MISCONF` errors (disk space issues)
- Write failures
- RDB snapshot failures

## Troubleshooting

### Disk Full Error
1. Check disk usage: `df -h /`
2. Find large files: `du -sh /var/log/* /opt/wegweiser/* | sort -hr | head -20`
3. Run manual cleanup: `sudo /opt/wegweiser/scripts/cleanup_logs.sh`
4. Delete old compressed logs: `sudo find /var/log -name "*.gz" -mtime +7 -delete`

### Redis Write Failures
If you see `MISCONF Redis is configured to save RDB snapshots` errors:
1. Check disk space (Redis needs space for RDB snapshots)
2. Free up space using cleanup script
3. Restart Redis: `sudo systemctl restart redis-server`
4. Restart Wegweiser: `sudo systemctl restart wegweiser`

### Application Not Starting
1. Check disk space: `df -h /`
2. Check logs: `tail -100 /opt/wegweiser/wlog/wegweiser.log`
3. Check service status: `sudo systemctl status wegweiser`
4. If disk full, run cleanup and restart services

## Best Practices

1. **Never disable error logging** - Always keep ERROR and WARNING levels enabled
2. **Monitor disk space proactively** - Don't wait for 100% usage
3. **Review logs regularly** - Check for unusual patterns or errors
4. **Test log rotation** - Verify logrotate works correctly after changes
5. **Keep cleanup scripts updated** - Adjust retention periods based on disk capacity
6. **Document changes** - Update this file when modifying log management

## Recent Changes

### 2025-11-08: Disk Space Crisis Resolution
- **Issue**: Disk 100% full, Redis and PostgreSQL failing
- **Root Cause**: 2.3GB gunicorn access log from high-frequency metrics polling
- **Actions Taken**:
  1. Disabled gunicorn access logging (`accesslog = None`)
  2. Deleted old gunicorn logs (freed 2.5GB)
  3. Cleaned up old compressed logs (freed 23MB)
  4. Cleaned up old payloads (freed 200MB)
  5. Implemented automated log rotation and cleanup
  6. Created systemd timer for daily cleanup at 2 AM
- **Result**: Disk usage reduced from 100% to 88%, services restored

