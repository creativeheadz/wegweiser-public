# Architecture Overview

Wegweiser is built on a modular, scalable architecture designed for MSP workflows and multi-tenant operations.

## System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Endpoint Agents                          │
│  (Windows/Linux/macOS - Low-profile scheduled tasks)        │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│                   NATS Messaging                            │
│  (Tenant-isolated subject-based communication)              │
└────────────────────┬────────────────────────────────────────┘
                     │
        ┌────────────┴────────────┐
        ▼                         ▼
┌──────────────────┐    ┌──────────────────┐
│  Flask Web App   │    │  Celery Workers  │
│  (REST API)      │    │  (Analysis Tasks)│
└────────┬─────────┘    └────────┬─────────┘
         │                       │
         └───────────┬───────────┘
                     ▼
        ┌────────────────────────┐
        │   PostgreSQL Database  │
        │  (Multi-tenant data)   │
        └────────────────────────┘
                     │
        ┌────────────┴────────────┐
        ▼                         ▼
    ┌────────┐            ┌──────────────┐
    │ Redis  │            │ Azure Key    │
    │(Cache) │            │ Vault(Secrets)
    └────────┘            └──────────────┘
```

## Core Components

### 1. Endpoint Agents
- **Windows** - PowerShell-based scheduled tasks
- **Linux/macOS** - Bash-based cron jobs
- **Persistent Agent** - NATS-based real-time connection (early stage)
- **Data Collection** - System info, event logs, performance metrics
- **Preprocessing** - Reduce bandwidth with local analysis

### 2. NATS Messaging
- **Tenant Isolation** - Subject-based permissions
- **Subject Pattern** - `tenant.{uuid}.device.{uuid}.{message_type}`
- **JetStream** - Message persistence and replay
- **Reliability** - Guaranteed delivery with fallback to scheduled tasks

### 3. Flask Web Application
- **Application Factory** - `app/__init__.py`
- **Blueprints** - Modular route organization
- **Authentication** - Session-based with role checking
- **Multi-Tenancy** - Strict data isolation per tenant
- **Security** - CSRF protection, IP blocking, security headers

### 4. Celery Task Queue
- **Background Processing** - Analysis and health scoring
- **Scheduled Tasks** - Periodic analysis runs
- **Task Types** - Domain-specific analyzers (security, hardware, etc.)
- **Health Scoring** - Individual scores aggregate hierarchically

### 5. PostgreSQL Database
- **Multi-Tenant Schema** - Tenant-based data isolation
- **Models** - Devices, organizations, users, conversations, health scores
- **Relationships** - Hierarchical structure (Tenant → Org → Group → Device)
- **Migrations** - Flask-Migrate for schema management

### 6. Redis
- **Session Storage** - Flask session backend
- **Caching** - Expensive query results
- **Celery Broker** - Task queue management
- **Fallback** - Filesystem fallback if Redis unavailable

### 7. Azure Key Vault
- **Secrets Management** - API keys, database credentials
- **Configuration** - AI provider settings, SMTP credentials
- **Security** - No secrets in code or environment files

## Hierarchical Structure

```
Tenant (MSP)
├── Organization (Client)
│   ├── Group (Device Collection)
│   │   ├── Device 1
│   │   ├── Device 2
│   │   └── Device 3
│   └── Group 2
│       └── Device 4
└── Organization 2
    └── Group 3
        └── Device 5
```

### Data Flow
1. **Device Level** - Individual device health score (1-100)
2. **Group Level** - Average of device scores in group
3. **Organization Level** - Average of group scores
4. **Tenant Level** - Average of organization scores

## Health Scoring System

### Individual Analysis
Each analyzer produces a health score (1-100):
- Security Events Analyzer
- System Events Analyzer
- Driver Analysis
- Performance Analysis
- And more...

### Aggregation
```
Device Health = Average(All Analyzer Scores)
Group Health = Average(All Device Scores)
Org Health = Average(All Group Scores)
Tenant Health = Average(All Org Scores)
```

### Recommendations
- AI-generated based on analysis results
- Prioritized by severity
- Cascade up the hierarchy

## Multi-Entity Chat System

### Architecture
- **Frontend** - Unified chat component (JavaScript)
- **Backend** - AI blueprint with entity-specific routes
- **Context** - Hierarchical context awareness
- **Memory** - Conversation history per entity
- **AI Providers** - Multiple provider support

### Levels
- **Device** - Specific machine insights
- **Group** - Aggregate group analysis
- **Organization** - Client-wide insights
- **Tenant** - MSP-wide analytics

## Data Processing Pipeline

```
Agent Collection
    ↓
NATS Transport
    ↓
Flask Ingestion
    ↓
Database Storage
    ↓
Celery Analysis
    ↓
AI Processing
    ↓
Health Score Calculation
    ↓
Recommendation Generation
    ↓
UI Display & Chat
```

## Security Architecture

### Multi-Tenancy
- Tenant-based row-level security
- Subject-based NATS permissions
- Strict query filtering

### Authentication
- Session-based with Flask-Session
- Role-based access control (RBAC)
- IP blocking for suspicious activity

### Data Protection
- Azure Key Vault for secrets
- CSRF protection on all forms
- Security headers middleware
- Encrypted connections

## Scalability Considerations

### Horizontal Scaling
- Stateless Flask instances behind load balancer
- Multiple Celery workers
- PostgreSQL connection pooling
- Redis cluster support

### Performance
- Database indexes on frequently queried fields
- Caching layer for expensive operations
- Batch processing for large datasets
- Asynchronous task processing

## Integration Points

### RMM Integration
- Agent deployment through existing RMM
- Webhook support for event notifications
- API access for custom integrations

### AI Providers
- Azure OpenAI
- OpenAI
- Anthropic Claude
- Ollama (on-premises)

### External Services
- SMTP for email notifications
- Azure Key Vault for secrets
- NATS for agent communication

---

**Next:** Review [Database Schema](./database-schema.md) for data model details.

