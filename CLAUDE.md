# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

**📚 For comprehensive documentation, see [Documentation Index](./documentation/INDEX.md)**

## Mission Statement

Wegweiser is an AI-powered intelligence layer for MSPs (Managed Service Providers) that addresses two critical bottlenecks:
1. **Client Onboarding Hell** - where larger customers hide critical issues beneath the surface
2. **The Knowledge Gap** - where nobody can know everything about every hardware type or event log

**Core Value Proposition**: Transform how MSPs onboard, understand and manage their clients' systems with AI-powered insights that go beyond traditional RMM capabilities. Wegweiser is RMM-agnostic and designed to enhance existing RMM solutions, not replace them.

## Development Commands

### Environment Setup
```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies (create requirements.txt from imports)
pip install flask flask-sqlalchemy flask-migrate flask-session flask-bcrypt flask-principal flask-mail flask-wtf
pip install psycopg2-binary redis celery python-dotenv authlib azure-identity azure-keyvault-secrets
pip install markdown markupsafe gunicorn pytest
```

### Database Operations
```bash
# Set Flask app
export FLASK_APP=wsgi.py

# Initialize database
flask db init

# Create migration
flask db migrate -m "Migration message"

# Apply migrations
flask db upgrade

# Custom commands
flask populate_servercore
flask create_roles
```

### Running the Application
```bash
# Development server
python wsgi.py

# Production server with Gunicorn
gunicorn --config gunicorn.conf.py wsgi:app

# Start Celery worker
celery -A app.celery worker --loglevel=info

# Start Celery beat scheduler
celery -A app.celery beat --loglevel=info
```

### Testing
```bash
# Run tests
pytest

# Run specific test file
pytest tests/test_specific.py

# Run with coverage
pytest --cov=app tests/
```

## Architecture Overview

### Core Business Logic

**Hierarchical Health Scoring System**:
- Individual task analyses produce health scores (1-100)
- Device health scores aggregate from multiple task analyses
- Group health scores aggregate from device scores
- Organization health scores aggregate from group scores
- Tenant health scores aggregate from organization scores
- **Tenant = MSP** (the service provider managing multiple client organizations)

**Agent Architecture**:
- **Primary Agents**: Low-profile scheduled tasks (Windows) / cronjobs (Linux/Mac)
- **Persistent Agents**: WebSocket-based real-time connection (early stage, heartbeat only)
- **Data Flow**: Endpoint collection → preprocessing → comprehensive summaries → webapp processing
- **Future Roadmap**: MCP servers with osquery integration for real-time chat queries

**Multi-Level Chat System**:
- Context-aware chat available at every hierarchical level
- Machine-level: Query specific device data and health metrics
- Group-level: Aggregate insights across device groups
- Organization-level: Client-wide system insights
- Tenant-level: MSP-wide analytics and management

### Technical Architecture

**Flask Application Factory** (`app/__init__.py`):
- Azure Key Vault integration for secret management
- Redis-based session storage with filesystem fallback
- Celery task queue for AI analysis processing
- Role-based access control with Flask-Principal
- IP blocking system for security
- Security headers middleware

**Database Models** (`app/models/`):
- SQLAlchemy ORM with PostgreSQL backend
- Multi-tenant architecture with strict tenant isolation
- Comprehensive device, user, and organization models
- AI conversation and memory tracking
- Health score and metrics tracking

**Route Structure** (`app/routes/`):
- Modular blueprint architecture (auto-registered)
- Admin panel (`admin/`)
- AI chat system (`ai/`) - core differentiator
- Device management (`devices/`)
- Organization management (`organisations/`)
- Authentication (`auth/`, `login/`)
- Tenant management (`tenant/`)

**Background Tasks** (`app/tasks/`):
- **Critical Component**: Domain-specific analyzers (hardware, auth, network, etc.)
- Each task produces individual health scores
- AI-powered analysis framework
- Scheduled health score updates and aggregation
- Billing and usage tracking

**Security Features**:
- Azure Key Vault for all secrets
- IP blocking with LMDB/Redis backends
- Session security with Redis
- CSRF protection
- Security headers middleware
- Role-based permissions system

### Key Architecture Patterns

**MSP-Centric Multi-Tenancy**:
- Tenant = MSP (service provider)
- Organizations = MSP's clients
- Strict data isolation between tenants
- Hierarchical access control and data aggregation

**AI-Powered Analysis Pipeline**:
- Multiple AI providers (Azure OpenAI, OpenAI, Anthropic Claude, Ollama)
- Task-based analysis system for different system components
- Conversation memory and context tracking
- Real-time chat with hierarchical context awareness

**RMM-Agnostic Data Collection**:
- Cross-platform agent support (Windows, Linux, macOS)
- Endpoint preprocessing to reduce bandwidth
- Comprehensive system metadata collection
- Fallback mechanisms for reliability

## Development Guidelines

### Business Logic Priority
- **Health Scoring**: All analyses must contribute to the hierarchical health scoring system
- **Context Awareness**: Chat responses should leverage hierarchical context appropriately
- **MSP Workflow**: Consider the MSP's client onboarding and management workflow
- **Data Aggregation**: Ensure proper data flow from device → group → org → tenant levels

### Database
- Use Flask-Migrate for all schema changes
- Always test migrations in development first
- Use the safe_db_session context manager for complex operations
- Maintain strict tenant isolation in all queries

### AI Integration
- AI providers are configured via Azure Key Vault
- Use the existing chat framework for AI interactions
- Memory and context are automatically tracked per conversation level
- Support multiple AI models for different analysis types

### Agent Development
- Prioritize low-profile, reliable operation
- Handle network failures gracefully (fallback to scheduled tasks)
- Preprocess data at endpoint when possible
- Support all major operating systems

### Security & Multi-Tenancy
- Never commit secrets to the repository
- Use Azure Key Vault for all sensitive configuration
- Ensure strict tenant data isolation
- Test IP blocking functionality carefully

### Background Tasks
- Use Celery for all background processing
- Each task should produce a meaningful health score
- Tasks are organized by analysis domain
- Monitor task queue health in production

## Key Files and Locations

- **Application entry point**: `wsgi.py`
- **Main app factory**: `app/__init__.py`
- **Database models**: `app/models/`
- **Routes/blueprints**: `app/routes/`
- **Background tasks**: `app/tasks/` (critical for health scoring)
- **Utilities**: `app/utilities/`
- **Static assets**: `app/static/`
- **Templates**: `app/templates/`
- **Configuration**: `gunicorn.conf.py`
- **Database migrations**: `migrations/`
- **Tests**: `tests/`
- **Agent scripts**: `agent/`, `downloads/`
- **Deployment setup**: `app/setup.sh`

## External Dependencies

- **Database**: PostgreSQL with connection pooling
- **Cache/Sessions**: Redis for session storage and caching
- **Task Queue**: Celery with Redis broker
- **Secrets**: Azure Key Vault for all sensitive configuration
- **AI Services**: Azure OpenAI, OpenAI, Anthropic Claude, Ollama
- **Email**: SMTP configuration via Azure Key Vault
- **Monitoring**: Custom logging with optional remote logging

## Development Philosophy

**RMM Enhancement, Not Replacement**:
- Build features that complement existing RMM tools
- Focus on intelligence and insights, not basic monitoring
- Maintain RMM-agnostic approach

**MSP-First Design**:
- Every feature should solve real MSP pain points
- Consider the client onboarding workflow
- Think hierarchically (device → group → org → tenant)

**AI as Core Differentiator**:
- Leverage AI for system insights, not just chat responses
- Build context-aware analysis capabilities
- Focus on bridging the knowledge gap for MSPs

**Reliability Over Features**:
- Agents must be low-profile and reliable
- Graceful degradation when connections fail
- Comprehensive error handling and logging

## Automated Workflows & Commands

### /md_cleanup_into_documentation
**Purpose**: Automatically organize markdown files in the project root

**Usage**:
```
/md_cleanup_into_documentation
```

**What it does**:
1. Validates all `.md` files in the project root
2. Moves important documentation to `/documentation/` (setup guides, architecture, references, design docs)
3. Deletes obsolete files (status reports, implementation checklists, historical summaries)
4. Preserves project configuration (CLAUDE.md)
5. Creates backup in `.backup/md_cleanup_{timestamp}/`
6. Logs all actions to `wlog/md_cleanup.log`

**Decision Criteria**:
- **MOVE**: README, SETUP, GUIDE, QUICKSTART, ARCHITECTURE, PORTABILITY, DESIGN, MECHANISM, FIX_LOG
- **DELETE**: READY, COMPLETE, CHECKLIST, SUMMARY, IMPLEMENTATION checklists, superseded guides
- **PRESERVE**: CLAUDE.md (project config)

**Files Involved**:
- Command: `.claude/commands/md_cleanup_into_documentation.md`
- Script: `scripts/md_cleanup.sh`

This command is safe - it always creates backups before any deletion.

### /md_cleanup_global
**Purpose**: Scan entire project and clean up stray markdown files across all directories

**Usage**:
```
/md_cleanup_global
```

**What it does**:
1. Scans entire project for `.md` files (excluding vendor directories)
2. Validates markdown files for content and structure
3. Moves important documentation to `/documentation/`
4. Deletes obsolete files (status reports, checklists, phase completion docs)
5. Preserves project configuration (CLAUDE.md)
6. Creates backup in `.backup/md_cleanup_{timestamp}/`
7. Skips vendor/dependency directories (venv, node_modules, .git, installerFiles, loki)

**Decision Criteria**:
Same as `/md_cleanup_into_documentation`, but applied globally across all project directories

**Smart Features**:
- Pattern-based classification (README, SETUP, GUIDE, DESIGN, etc. → MOVE)
- Obsolete pattern detection (READY, COMPLETE, SUMMARY, PHASE_, etc. → DELETE)
- Location-specific rules (monitoring guides deleted from dev_scripts/monitoring/)
- Archive detection (automatically removes historical docs from documentation/archive/)

**Files Involved**:
- Command: `.claude/commands/md_cleanup_global.md`
- Script: `scripts/md_cleanup_global.py`

**Use Cases**:
- After major refactoring when many temp docs were created
- Periodic cleanup of stray documentation
- Before releases to ensure clean project structure
- After merging feature branches with documentation