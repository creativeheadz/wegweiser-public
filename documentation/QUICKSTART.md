# Quick Start: Live Monitoring Tests

Get Wegweiser monitoring running in 5 minutes.

## 30-Second Setup (NTFY)

```bash
# 1. Set environment variables
export NTFY_URL="https://skald.oldforge.tech/WegweiserStatus"
export NTFY_TOKEN="tk_vlsvy25i0fqz885fek3r5nraykozg"

# 2. Run tests
/opt/wegweiser/dev_scripts/monitoring/run_live_tests.sh

# 3. Subscribe to alerts
# Visit: https://skald.oldforge.tech/WegweiserStatus
# Or use mobile app
```

Done! You're now monitoring Wegweiser.

---

## 5-Minute Setup (With Login Testing)

```bash
# 1. Set environment variables
export NTFY_URL="https://skald.oldforge.tech/WegweiserStatus"
export NTFY_TOKEN="tk_vlsvy25i0fqz885fek3r5nraykozg"
export TEST_USER_EMAIL="monitor@test.local"
export TEST_USER_PASSWORD="TestPassword123!"

# 2. Run tests with login simulation
/opt/wegweiser/dev_scripts/monitoring/run_live_tests.sh --with-login

# 3. Subscribe to alerts
# Visit: https://skald.oldforge.tech/WegweiserStatus
```

Now monitoring includes login flow testing.

---

## 10-Minute Setup (With MFA Testing)

```bash
# 1. Set environment variables
export NTFY_URL="https://skald.oldforge.tech/WegweiserStatus"
export NTFY_TOKEN="tk_vlsvy25i0fqz885fek3r5nraykozg"
export TEST_USER_EMAIL="monitor@test.local"
export TEST_USER_PASSWORD="TestPassword123!"

# 2. Run tests with MFA
/opt/wegweiser/dev_scripts/monitoring/run_live_tests.sh --with-login --with-mfa

# 3. Subscribe to alerts
# Visit: https://skald.oldforge.tech/WegweiserStatus
```

Now monitoring includes full MFA flow testing.

---

## Schedule with Tactical RMM

1. **Open Tactical RMM**
2. **Go to:** Clients → Your Client → Sites → Your Site
3. **Create Scheduled Task:**
   - Name: "Wegweiser Monitoring"
   - Script: `/opt/wegweiser/dev_scripts/monitoring/run_live_tests.sh --with-login`
   - Schedule: Every 5 minutes
   - Timeout: 60 seconds
   - Alert on failure: Yes

4. **Set environment variables in task:**
   ```
   NTFY_URL=https://skald.oldforge.tech/WegweiserStatus
   NTFY_TOKEN=tk_vlsvy25i0fqz885fek3r5nraykozg
   TEST_USER_EMAIL=monitor@test.local
   TEST_USER_PASSWORD=TestPassword123!
   ```

Done! Monitoring runs automatically every 5 minutes.

---

## Schedule with Cron

```bash
# Edit crontab
crontab -e

# Add this line (runs every 5 minutes)
*/5 * * * * /opt/wegweiser/dev_scripts/monitoring/run_live_tests.sh --with-login

# Or every 10 minutes
*/10 * * * * /opt/wegweiser/dev_scripts/monitoring/run_live_tests.sh --with-login
```

---

## What Gets Tested?

✅ **Health Check** - Is Wegweiser responding?
✅ **Login Flow** - Can users log in?
✅ **MFA TOTP** - Is MFA working?
✅ **AI Analysis** - Are AI endpoints responding?
✅ **Memory Store** - Is Redis/memory store healthy?
✅ **Database** - Is PostgreSQL connected?
✅ **Celery Queue** - Is task queue working?

---

## Alert Examples

### When Tests Pass
```
✓ All tests passed!
```

### When Tests Fail
```
🚨 Wegweiser Live Tests: 2/7 tests failed

❌ Login Flow
❌ Database Connection
```

---

## Verify It's Working

### Check logs
```bash
tail -f /opt/wegweiser/wlog/live_tests.log
```

### Run manually
```bash
/opt/wegweiser/dev_scripts/monitoring/run_live_tests.sh
```

### Test NTFY
```bash
curl -X POST https://skald.oldforge.tech/WegweiserStatus \
  -H "Title: Test" \
  -H "Authorization: Bearer tk_vlsvy25i0fqz885fek3r5nraykozg" \
  -d "If you see this, alerts are working!"
```

---

## Next Steps

1. **Subscribe to alerts:**
   - Visit https://skald.oldforge.tech/WegweiserStatus
   - Or download mobile app (iOS/Android) and add custom server

2. **Schedule monitoring:**
   - Via Tactical RMM (recommended)
   - Or via cron

3. **Add more integrations:**
   - See INTEGRATION_GUIDE.md for n8n, Zabbix, etc.

4. **Customize tests:**
   - Edit live_tests.py to add custom tests
   - Add your own health checks

---

## Troubleshooting

### Tests not running?
```bash
# Check if script is executable
ls -la /opt/wegweiser/dev_scripts/monitoring/run_live_tests.sh

# Check if venv exists
ls -la /opt/wegweiser/venv

# Check logs
tail -f /opt/wegweiser/wlog/live_tests.log
```

### Alerts not sending?
```bash
# Test NTFY connectivity
curl -X POST https://ntfy.sh/test -d "test"

# Check environment variable
echo $NTFY_URL

# Check logs for errors
grep -i "ntfy\|alert" /opt/wegweiser/wlog/live_tests.log
```

### Login tests failing?
```bash
# Check test user exists
psql -U wegweiser -d wegweiser -c "SELECT * FROM accounts WHERE companyemail='monitor@test.local'"

# Check database connection
psql -U wegweiser -d wegweiser -c "SELECT 1"
```

---

## Support

- **Documentation:** `/opt/wegweiser/dev_scripts/monitoring/README.md`
- **Integration Guide:** `/opt/wegweiser/dev_scripts/monitoring/INTEGRATION_GUIDE.md`
- **Logs:** `/opt/wegweiser/wlog/live_tests.log`

---

## Common Questions

**Q: How often should I run tests?**
A: Every 5-10 minutes is recommended for production.

**Q: Will tests affect production?**
A: No, tests use a dedicated test user and don't modify production data.

**Q: Can I use multiple alert channels?**
A: Yes! Set multiple environment variables and alerts go to all channels.

**Q: What if Wegweiser is down?**
A: Tests will fail and send alerts immediately.

**Q: Can I customize the tests?**
A: Yes, edit `live_tests.py` to add custom tests.

---

## You're All Set! 🎉

Your Wegweiser monitoring is now running. You'll receive alerts if anything breaks.

Happy monitoring!

