# Ops hardening: run directories, permissions, and monitoring

This folder contains battle-tested patterns to keep Celery and related services stable without relying on ad-hoc manual fixes on /var or /run paths.

## 1) Prefer systemd-managed runtime dirs

Use systemd to create and own runtime directories at service start. This avoids permission drift across reboots.

Create a drop-in for `wegweiser-celery.service`:

Path: `/etc/systemd/system/wegweiser-celery.service.d/override.conf`

```
[Service]
# Create /run/celery at start, owned by the service User/Group
RuntimeDirectory=celery
RuntimeDirectoryMode=0750
# Optional: create a private state dir under /var/lib (persist across reboots)
# StateDirectory=wegweiser
# StateDirectoryMode=0750

# Ensure PID/log paths use RuntimeDirectory and app-local logs
Environment=CELERYD_PID_FILE=/run/celery/%n.pid
Environment=CELERYD_LOG_FILE=/opt/wegweiser/wlog/celery-%n.log

# Stronger restarts
Restart=on-failure
RestartSec=3s
StartLimitIntervalSec=120
StartLimitBurst=10
```

Then reload and restart:

```
sudo systemctl daemon-reload
sudo systemctl restart wegweiser-celery.service
sudo systemctl status wegweiser-celery.service
```

Notes:
- systemd creates `/run/celery` with ownership set to the service User/Group automatically.
- The wrapper script now falls back to `/opt/wegweiser/run/celery` if `/run/celery` isn’t writable, so you have two safety nets.

## 2) Boot-time guarantees with tmpfiles.d (optional)

For services that aren’t managed by systemd `RuntimeDirectory`, use tmpfiles.d to create runtime dirs at boot.

Path: `/etc/tmpfiles.d/celery.conf`
```
d /run/celery 0750 wegweiser www-data - -
```
Apply immediately:
```
sudo systemd-tmpfiles --create /etc/tmpfiles.d/celery.conf
```

## 3) Monitoring: queue health and auto-remediation

Use the included diagnostic to alert if the backlog grows.

- Script: `dev_scripts/diagnostics/monitor_pending.py`
- Behavior: exits non-zero if pending exceeds a threshold (default 50). Designed for systemd timers or cron.

Example systemd timer units (copy to `/etc/systemd/system/`):

`monitor-pending.service`
```
[Unit]
Description=Check Wegweiser pending queue and alert on threshold

[Service]
Type=oneshot
User=wegweiser
WorkingDirectory=/opt/wegweiser
ExecStart=/opt/wegweiser/venv/bin/python3.12 /opt/wegweiser/dev_scripts/diagnostics/monitor_pending.py --threshold 50
```

`monitor-pending.timer`
```
[Unit]
Description=Run pending queue monitor every minute

[Timer]
OnBootSec=30s
OnUnitActiveSec=60s
Unit=monitor-pending.service

[Install]
WantedBy=timers.target
```

Enable and start:
```
sudo systemctl daemon-reload
sudo systemctl enable --now monitor-pending.timer
sudo systemctl list-timers | grep monitor-pending
```

On failure (pending > threshold), the service will exit non-zero and show up in `systemctl --failed`; you can tie this to your existing alerting.

## 4) Optional: stale "processing" sweeper

Consider a periodic task that reverts `processing` items older than N hours back to `pending`. Implement as a Celery beat task or a small script + timer similar to the monitor above.

## 5) Logging

Prefer journald for service logs plus app-local log files under `/opt/wegweiser/wlog/`. A logrotate config already exists in `logrotate_wegweiser`.

## Summary
- Use `RuntimeDirectory` for ephemeral `/run/*` paths.
- Provide a tmpfiles.d rule as a fallback.
- Monitor backlog with a systemd timer calling our monitor script.
- Wrapper script falls back to app-local run dir to avoid hard reliance on `/var/run`.
