# API Reference

Complete reference for Wegweiser REST API endpoints.

## Base URL

```
https://app.wegweiser.tech/api
```

## Authentication

All API endpoints require authentication via session cookies or API tokens.

### Session Authentication
```bash
curl -b cookies.txt https://app.wegweiser.tech/api/devices
```

### API Token Authentication
```bash
curl -H "Authorization: Bearer YOUR_API_TOKEN" \
  https://app.wegweiser.tech/api/devices
```

## Endpoints

### Devices

#### List Devices
```
GET /api/devices
```

Query Parameters:
- `organization_id` - Filter by organization
- `group_id` - Filter by group
- `page` - Pagination (default: 1)
- `per_page` - Items per page (default: 20)

Response:
```json
{
  "devices": [
    {
      "id": "uuid",
      "name": "Device Name",
      "health_score": 85,
      "status": "online",
      "last_seen": "2025-10-19T10:30:00Z"
    }
  ],
  "total": 100,
  "page": 1
}
```

#### Get Device Details
```
GET /api/devices/{device_id}
```

Response:
```json
{
  "id": "uuid",
  "name": "Device Name",
  "health_score": 85,
  "status": "online",
  "organization_id": "uuid",
  "group_id": "uuid",
  "metadata": {},
  "last_analysis": "2025-10-19T10:30:00Z"
}
```

#### Delete Device
```
DELETE /api/devices/{device_id}
```

### Organizations

#### List Organizations
```
GET /api/organizations
```

#### Get Organization Details
```
GET /api/organizations/{org_id}
```

#### Create Organization
```
POST /api/organizations
```

Request Body:
```json
{
  "name": "Organization Name",
  "description": "Optional description"
}
```

### Groups

#### List Groups
```
GET /api/organizations/{org_id}/groups
```

#### Get Group Details
```
GET /api/organizations/{org_id}/groups/{group_id}
```

#### Create Group
```
POST /api/organizations/{org_id}/groups
```

Request Body:
```json
{
  "name": "Group Name",
  "description": "Optional description"
}
```

### Health Scores

#### Get Device Health Score
```
GET /api/devices/{device_id}/health
```

Response:
```json
{
  "device_id": "uuid",
  "score": 85,
  "timestamp": "2025-10-19T10:30:00Z",
  "components": {
    "security": 80,
    "system": 85,
    "drivers": 90,
    "performance": 85
  }
}
```

#### Get Health Score History
```
GET /api/devices/{device_id}/health/history
```

Query Parameters:
- `days` - Number of days to retrieve (default: 30)
- `interval` - Data point interval (default: daily)

### Chat

#### Send Message
```
POST /api/chat/{entity_type}/{entity_id}
```

Entity Types: `device`, `group`, `organization`, `tenant`

Request Body:
```json
{
  "message": "What is the health status of this device?"
}
```

Response:
```json
{
  "id": "message_id",
  "response": "AI-generated response",
  "timestamp": "2025-10-19T10:30:00Z"
}
```

#### Get Conversation History
```
GET /api/chat/{entity_type}/{entity_id}/history
```

Query Parameters:
- `page` - Pagination (default: 1)
- `per_page` - Items per page (default: 20)

### Analysis

#### Trigger Analysis
```
POST /api/devices/{device_id}/analyze
```

Request Body:
```json
{
  "analysis_type": "security"
}
```

#### Get Analysis Results
```
GET /api/devices/{device_id}/analysis/{analysis_id}
```

### Recommendations

#### Get Device Recommendations
```
GET /api/devices/{device_id}/recommendations
```

Query Parameters:
- `severity` - Filter by severity (critical, high, medium, low)
- `status` - Filter by status (open, resolved)

Response:
```json
{
  "recommendations": [
    {
      "id": "uuid",
      "title": "Recommendation Title",
      "description": "Detailed description",
      "severity": "high",
      "status": "open",
      "created_at": "2025-10-19T10:30:00Z"
    }
  ]
}
```

## Error Responses

### 400 Bad Request
```json
{
  "error": "Invalid request",
  "details": "Field 'name' is required"
}
```

### 401 Unauthorized
```json
{
  "error": "Unauthorized",
  "details": "Authentication required"
}
```

### 403 Forbidden
```json
{
  "error": "Forbidden",
  "details": "Insufficient permissions"
}
```

### 404 Not Found
```json
{
  "error": "Not found",
  "details": "Device not found"
}
```

### 500 Internal Server Error
```json
{
  "error": "Internal server error",
  "details": "An unexpected error occurred"
}
```

## Rate Limiting

API requests are rate limited:
- **Standard** - 100 requests per minute
- **Authenticated** - 1000 requests per minute
- **Premium** - Unlimited

Rate limit headers:
```
X-RateLimit-Limit: 1000
X-RateLimit-Remaining: 999
X-RateLimit-Reset: 1634654400
```

## Pagination

List endpoints support pagination:

Query Parameters:
- `page` - Page number (default: 1)
- `per_page` - Items per page (default: 20, max: 100)

Response:
```json
{
  "data": [...],
  "pagination": {
    "page": 1,
    "per_page": 20,
    "total": 100,
    "pages": 5
  }
}
```

## Webhooks

Configure webhooks for real-time notifications:

### Webhook Events
- `device.online` - Device came online
- `device.offline` - Device went offline
- `health.score.changed` - Health score changed
- `recommendation.created` - New recommendation
- `analysis.completed` - Analysis completed

### Webhook Payload
```json
{
  "event": "health.score.changed",
  "timestamp": "2025-10-19T10:30:00Z",
  "data": {
    "device_id": "uuid",
    "old_score": 80,
    "new_score": 85
  }
}
```

---

**Next:** Review [Testing Guide](./testing-guide.md) for API testing.

