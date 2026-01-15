# Integration Guide: Live Monitoring Tests

Complete setup guides for each alert integration.

## NTFY (Recommended for Most Users)

### Why NTFY?
- ✅ No server setup required
- ✅ Free tier available
- ✅ Mobile app support (iOS/Android)
- ✅ Simple webhook format
- ✅ Instant notifications

### Setup Steps

1. **Set environment variables:**
```bash
export NTFY_URL="https://skald.oldforge.tech/WegweiserStatus"
export NTFY_TOKEN="tk_vlsvy25i0fqz885fek3r5nraykozg"
```

2. **Subscribe to alerts:**
   - Visit: https://skald.oldforge.tech/WegweiserStatus
   - Or use mobile app: Add custom server https://skald.oldforge.tech

3. **Test it:**
```bash
curl -X POST https://skald.oldforge.tech/WegweiserStatus \
  -H "Title: Test Alert" \
  -H "Authorization: Bearer tk_vlsvy25i0fqz885fek3r5nraykozg" \
  -d "This is a test notification"
```

4. **Run monitoring:**
```bash
/opt/wegweiser/dev_scripts/monitoring/run_live_tests.sh
```

### Customization

Change topic name:
```bash
export NTFY_URL="https://ntfy.sh/my-company-wegweiser"
```

Use self-hosted NTFY:
```bash
export NTFY_URL="https://ntfy.mycompany.com/wegweiser-alerts"
```

---

## n8n (Advanced Workflows)

### Why n8n?
- ✅ Complex workflow automation
- ✅ Multi-channel notifications (Slack, Teams, Email, etc.)
- ✅ Data logging and analytics
- ✅ Conditional logic and filtering
- ✅ Integration with 400+ services

### Setup Steps

1. **Create n8n webhook trigger:**
   - Open n8n UI
   - Create new workflow
   - Add "Webhook" trigger node
   - Set method to POST
   - Copy webhook URL

2. **Add notification nodes:**
   - Add "Slack" node (or Teams, Email, etc.)
   - Configure with your credentials
   - Map test results to message format

3. **Set environment variable:**
```bash
export N8N_WEBHOOK_URL="https://n8n.example.com/webhook/wegweiser-monitoring"
```

4. **Example n8n workflow:**

```
Webhook (POST)
    ↓
Filter by severity
    ├→ CRITICAL → Slack + Email + PagerDuty
    ├→ WARNING → Slack + Database
    └→ INFO → Database only
    ↓
Log to database
    ↓
Generate daily report
```

5. **Test it:**
```bash
curl -X POST https://n8n.example.com/webhook/wegweiser-monitoring \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Test Alert",
    "message": "This is a test",
    "severity": "warning"
  }'
```

### Example n8n Nodes

**Slack Notification:**
```json
{
  "channel": "#alerts",
  "text": "{{ $json.title }}",
  "attachments": [{
    "color": "danger",
    "text": "{{ $json.message }}"
  }]
}
```

**Email Notification:**
```json
{
  "to": "admin@example.com",
  "subject": "Wegweiser Alert: {{ $json.title }}",
  "html": "<h2>{{ $json.title }}</h2><p>{{ $json.message }}</p>"
}
```

---

## Zabbix (Enterprise Monitoring)

### Why Zabbix?
- ✅ Enterprise-grade monitoring
- ✅ Advanced dashboards and graphs
- ✅ Historical data and trends
- ✅ Escalation policies
- ✅ Integration with existing infrastructure

### Setup Steps

1. **Create Zabbix API token:**
   - Login to Zabbix UI
   - Go to Administration → API tokens
   - Create new token with permissions
   - Copy token value

2. **Create Zabbix host:**
   - Go to Configuration → Hosts
   - Create new host named "Wegweiser"
   - Add to appropriate host group
   - Save

3. **Set environment variables:**
```bash
export ZABBIX_URL="http://zabbix.local/api_jsonrpc.php"
export ZABBIX_API_TOKEN="your-api-token-here"
export ZABBIX_HOST_NAME="Wegweiser"
```

4. **Create custom items (optional):**
   - Go to Configuration → Hosts → Wegweiser → Items
   - Create items for each test type
   - Set data type to "Numeric (unsigned)"

5. **Create triggers (optional):**
   - Go to Configuration → Hosts → Wegweiser → Triggers
   - Create trigger: "Test failed"
   - Expression: `{Wegweiser:test_status.last()} = 0`

6. **Test it:**
```bash
curl -X POST http://zabbix.local/api_jsonrpc.php \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "method": "event.create",
    "params": {
      "source": 0,
      "object": 0,
      "objectid": 0,
      "clock": '$(date +%s)',
      "value": 1,
      "severity": 5
    },
    "auth": "your-api-token",
    "id": 1
  }'
```

### Zabbix Dashboard

Create dashboard with:
- Test pass/fail rate (gauge)
- Response times (graph)
- MFA success rate (pie chart)
- Database connectivity (status)
- Celery queue health (status)

---

## Tactical RMM (RMM-Native Alerts)

### Why Tactical RMM?
- ✅ Native RMM integration
- ✅ Centralized alert management
- ✅ Escalation policies
- ✅ Client/site organization
- ✅ Existing infrastructure

### Setup Steps

1. **Get API credentials:**
   - Login to Tactical RMM
   - Go to Settings → API
   - Create new API key
   - Copy API URL and key

2. **Get client and site IDs:**
   - Go to Clients
   - Note client ID
   - Go to Sites
   - Note site ID

3. **Set environment variables:**
```bash
export TACTICAL_RMM_URL="https://rmm.example.com/api"
export TACTICAL_RMM_API_KEY="your-api-key"
export TACTICAL_RMM_CLIENT_ID="1"
export TACTICAL_RMM_SITE_ID="1"
```

4. **Create scheduled task in Tactical RMM:**
   - Go to Clients → Your Client → Sites → Your Site
   - Create new scheduled task
   - Script: `/opt/wegweiser/dev_scripts/monitoring/run_live_tests.sh`
   - Schedule: Every 5 minutes
   - Timeout: 60 seconds
   - Alert on failure: Yes

5. **Test it:**
```bash
curl -X POST https://rmm.example.com/api/alerts/ \
  -H "Authorization: Token your-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "client": 1,
    "site": 1,
    "alert_type": "custom",
    "severity": "critical",
    "title": "Test Alert",
    "description": "This is a test"
  }'
```

---

## Multi-Channel Setup (Recommended)

Combine multiple integrations for redundancy:

```bash
# NTFY for quick notifications
export NTFY_URL="https://skald.oldforge.tech/WegweiserStatus"
export NTFY_TOKEN="tk_vlsvy25i0fqz885fek3r5nraykozg"

# n8n for complex workflows
export N8N_WEBHOOK_URL="https://n8n.example.com/webhook/wegweiser"

# Zabbix for historical data
export ZABBIX_URL="http://zabbix.local/api_jsonrpc.php"
export ZABBIX_API_TOKEN="token"

# Tactical RMM for native integration
export TACTICAL_RMM_URL="https://rmm.example.com/api"
export TACTICAL_RMM_API_KEY="key"
export TACTICAL_RMM_CLIENT_ID="1"
export TACTICAL_RMM_SITE_ID="1"
```

All alerts will be sent to all configured channels.

---

## Troubleshooting

### NTFY Not Receiving Alerts
```bash
# Test connectivity
curl -X POST https://ntfy.sh/test -d "test message"

# Check if topic is accessible with token
curl -H "Authorization: Bearer tk_vlsvy25i0fqz885fek3r5nraykozg" \
  https://skald.oldforge.tech/WegweiserStatus/json
```

### n8n Webhook Not Triggering
```bash
# Check webhook URL is correct
# Verify webhook is active in n8n UI
# Check n8n logs for errors
# Test with curl
```

### Zabbix API Errors
```bash
# Verify API token is valid
# Check host exists
# Verify API URL is correct
# Check Zabbix logs
```

### Tactical RMM Connection Issues
```bash
# Verify API key is valid
# Check client/site IDs exist
# Verify API URL is accessible
# Check firewall rules
```

---

## Best Practices

1. **Use NTFY for quick start** - Get monitoring running in 5 minutes
2. **Add n8n for workflows** - Complex notifications and logging
3. **Add Zabbix for history** - Long-term trends and analysis
4. **Add Tactical RMM** - Native RMM integration
5. **Test all integrations** - Verify alerts are working
6. **Monitor the monitors** - Set up alerts for monitoring failures
7. **Document your setup** - Keep runbooks for troubleshooting

