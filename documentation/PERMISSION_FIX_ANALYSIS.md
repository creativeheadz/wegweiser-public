# Permission Issue Root Cause Analysis & Prevention System

**Date**: November 9, 2025
**Issue**: Payload delivery failing due to Permission Denied errors

## Root Cause Identified

### The Problem
The `/opt/wegweiser/payloads/queue` directory had incorrect ownership (`root:root` instead of `wegweiser:www-data`), causing payload uploads to fail with:
```
[Errno 13] Permission denied: '/opt/wegweiser/payloads/queue/...'
```

### Why This Happens

1. **Directory Creation in Code**: The `checkDir()` function in `/opt/wegweiser/app/routes/payload.py` uses `os.makedirs()` which:
   - Creates directories with default permissions based on umask
   - Does NOT set explicit ownership
   - If called by a process running as root (or via sudo), creates directories as `root:root`

2. **Gunicorn Running as Root**: Some gunicorn worker processes are running as root:
   ```
   root  11611  /opt/wegweiser/venv/bin/python3.12 /opt/wegweiser/venv/bin/gunicorn
   ```
   When these processes create directories via `checkDir()`, they become owned by root.

3. **Inconsistent Process Ownership**: Mix of root and wegweiser users running gunicorn workers leads to unpredictable permission states.

## Immediate Fixes Applied

### 1. Fixed Current Permission Issue
```bash
sudo chown -R wegweiser:www-data /opt/wegweiser/payloads/queue
sudo chmod 775 /opt/wegweiser/payloads/queue
```

### 2. Fixed `checkDir()` Function
Modified `/opt/wegweiser/app/routes/payload.py` to:
- Set explicit mode `0o775` when creating directories
- Explicitly set ownership to `wegweiser:www-data` after creation
- Log warnings if ownership cannot be set

**Before**:
```python
def checkDir(dirToCheck):
    if os.path.isdir(dirToCheck):
        pass
    else:
        try:
            os.makedirs(dirToCheck)  # ← No mode, no ownership set
```

**After**:
```python
def checkDir(dirToCheck):
    if os.path.isdir(dirToCheck):
        pass
    else:
        try:
            os.makedirs(dirToCheck, mode=0o775, exist_ok=True)
            # Set proper ownership
            uid = pwd.getpwnam('wegweiser').pw_uid
            gid = grp.getgrnam('www-data').gr_gid
            os.chown(dirToCheck, uid, gid)
```

## Prevention System Implemented

### 1. Automated Permission Monitoring
**Script**: `/opt/wegweiser/scripts/check_permissions.sh`
- Checks all critical directories every 5 minutes
- Auto-corrects any permission issues
- Sends alerts when fixes are needed
- Logs all actions to `/var/log/wegweiser/permission_check.log`

**Monitored Directories**:
- `/opt/wegweiser/payloads/*` (queue, invalid, noDeviceUuid, etc.)
- `/opt/wegweiser/deviceFiles`
- `/opt/wegweiser/logs`
- `/opt/wegweiser/wlog`
- `/opt/wegweiser/data/*`
- `/opt/wegweiser/downloads`
- `/opt/wegweiser/tmp`
- `/opt/wegweiser/flask_session`
- `/opt/wegweiser/backups`
- `/opt/wegweiser/snippets`

### 2. Systemd Timer for Continuous Monitoring
**Service**: `/etc/systemd/system/wegweiser-permission-check.service`
**Timer**: `/etc/systemd/system/wegweiser-permission-check.timer`

- Runs every 5 minutes
- Auto-starts on boot (after 1 minute delay)
- Logs to systemd journal and custom log file

**Status Check**:
```bash
sudo systemctl status wegweiser-permission-check.timer
```

**Manual Run**:
```bash
sudo /opt/wegweiser/scripts/check_permissions.sh
```

### 3. Alert Configuration
To receive email alerts when permissions are corrected, set:
```bash
export WEGWEISER_ALERT_EMAIL="your-email@domain.com"
```

Or add to the systemd service file:
```ini
Environment=WEGWEISER_ALERT_EMAIL=your-email@domain.com
```

## Recommendations

### 2. Fix Gunicorn User Configuration ✅ **FIXED**
**Issue Found**: There were TWO gunicorn instances running:
1. Old instance started with `sudo` (Nov 03) - running as **root** ❌
2. Proper systemd service (Nov 08) - running as **wegweiser** ✅

**Action Taken**: 
- Killed the old root gunicorn processes (PIDs: 11609, 11611, 167540, 167569, 167686, 167913)
- Restarted proper systemd service
- Verified all processes now run as `wegweiser` user

**Verification**:
```bash
ps aux | grep gunicorn | grep -v grep
# All processes should show 'wegweis+' in first column

# Should return nothing (no root processes)
ps aux | grep -E "wegweiser|gunicorn" | grep root
```

**Prevention**: Never start gunicorn manually with `sudo`. Always use:
```bash
sudo systemctl start wegweiser
sudo systemctl restart wegweiser
```

### 2. Review All `mkdir`/`makedirs` Calls
Search for other locations in the codebase that might have similar issues:
```bash
grep -r "os.makedirs\|os.mkdir" /opt/wegweiser/app/ --include="*.py"
```

Consider creating a centralized utility function:
```python
def ensure_directory(path, mode=0o775, owner='wegweiser', group='www-data'):
    """Create directory with proper permissions and ownership"""
    os.makedirs(path, mode=mode, exist_ok=True)
    uid = pwd.getpwnam(owner).pw_uid
    gid = grp.getgrnam(group).gr_gid
    os.chown(path, uid, gid)
```

### 3. Add to Deployment Checklist
- Verify all gunicorn workers run as correct user
- Run permission check script after any deployment
- Monitor systemd timer for alerts

## Testing

1. **Verify Fix Works**:
   ```bash
   # Simulate the issue
   sudo mkdir /opt/wegweiser/payloads/test_queue
   sudo ls -la /opt/wegweiser/payloads/ | grep test_queue
   # Should show root:root
   
   # Run permission check
   sudo /opt/wegweiser/scripts/check_permissions.sh
   # Should auto-fix it
   ```

2. **Check Timer Operation**:
   ```bash
   sudo systemctl list-timers | grep wegweiser-permission
   sudo journalctl -u wegweiser-permission-check.service -f
   ```

3. **Verify Payload Upload**:
   - Test a device payload upload
   - Check `/opt/wegweiser/wlog/wegweiser.log` for success
   - Verify files land in queue directory

## Files Modified/Created

### Modified:
- `/opt/wegweiser/app/routes/payload.py` - Fixed `checkDir()` function

### Created:
- `/opt/wegweiser/scripts/check_permissions.sh` - Permission monitoring script
- `/opt/wegweiser/config/systemd/wegweiser-permission-check.service` - Systemd service
- `/opt/wegweiser/config/systemd/wegweiser-permission-check.timer` - Systemd timer
- `/etc/systemd/system/wegweiser-permission-check.service` - Installed service
- `/etc/systemd/system/wegweiser-permission-check.timer` - Installed timer

## Quick Health Check Commands

```bash
# Check permissions are correct
sudo /opt/wegweiser/scripts/check_permissions.sh

# Check gunicorn is running as correct user
/opt/wegweiser/scripts/check_gunicorn_user.sh

# View permission monitor logs
sudo tail -f /var/log/wegweiser/permission_check.log

# Check monitoring timer status
sudo systemctl status wegweiser-permission-check.timer

# Test write access to queue directory
touch /opt/wegweiser/payloads/queue/test_$(date +%s).tmp && rm /opt/wegweiser/payloads/queue/test_*.tmp && echo "✓ Write OK"

# Monitor for new payload uploads
sudo tail -f /opt/wegweiser/wlog/wegweiser.log | grep -E "payload|sendfile|sendaudit"

# Check for any permission errors in logs
sudo grep -i "permission denied" /opt/wegweiser/wlog/wegweiser.log | tail -5
```

## What Changed (For Reference)

**Before:**
- `/opt/wegweiser/payloads/queue` owned by `root:root` with `755` permissions
- Old gunicorn processes (started with `sudo`) running as root
- No monitoring or auto-correction
- Payload uploads failing with Permission Denied errors

**After:**
- `/opt/wegweiser/payloads/queue` owned by `wegweiser:www-data` with `775` permissions  
- All gunicorn processes running as `wegweiser` user via systemd
- Automated monitoring every 5 minutes with auto-correction
- Code fixed to explicitly set ownership on directory creation
- Health check scripts for manual verification
- Payload uploads working normally

## Summary

**Problem**: Directories created as `root:root` instead of `wegweiser:www-data`, breaking payload delivery

**Root Causes Identified**:
1. ❌ Old gunicorn instance running as root (started manually with `sudo` on Nov 3)
2. ❌ `checkDir()` function using `os.makedirs()` without explicit ownership
3. ❌ No monitoring/alerting for permission issues

**Solutions Implemented**: 
1. ✅ Killed rogue root gunicorn processes
2. ✅ Fixed `checkDir()` to set explicit ownership when creating directories
3. ✅ Created automated monitoring script that runs every 5 minutes
4. ✅ Added systemd timer for continuous monitoring with auto-correction
5. ✅ Created health check scripts for manual verification
6. ✅ Added logging and alerting capabilities

**Status**: ✅ **FULLY FIXED AND MONITORED**
- All permissions corrected
- Code fixed to prevent recurrence
- Automated monitoring active every 5 minutes
- Will auto-correct and alert if issues reoccur
- Health check scripts available for manual verification
