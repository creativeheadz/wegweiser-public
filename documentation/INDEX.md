# Wegweiser Documentation Index

Welcome to the Wegweiser knowledge base. This is your comprehensive guide to understanding, developing, and deploying Wegweiser.

## 📖 Documentation Structure

### Getting Started
- **[Getting Started Guide](./getting-started.md)** - First steps for new users and developers
- **[Quick Start Guide](../QUICKSTART.md)** - 5-minute quick start for all deployment modes
- **[Installation & Setup](./installation-setup.md)** - Environment configuration and deployment
- **[Setup Guide](../SETUP_GUIDE.md)** - Comprehensive installation guide for all scenarios
- **[Installation Wizard](../install.sh)** - Interactive installation with guided setup
- **[Setup Verification](../verify-setup.sh)** - Verify your installation after setup

### Architecture & Design
- **[Architecture Overview](./architecture-overview.md)** - System design, components, and data flow
- **[Database Schema](./database-schema.md)** - Data models and relationships
- **[Multi-Tenancy Design](./multi-tenancy.md)** - Tenant isolation and data segregation

### Core Features
- **[Analysis Framework](./core-analysis-framework.md)** - How system analysis works
- **[Multi-Entity Chat System](./core-multi-entity-chat.md)** - AI chat at every level
- **[Health Scoring System](./core-health-scoring.md)** - Hierarchical health calculations

### Data Processing
- **[Event Log Processing](./data-eventlog-processing.md)** - Windows event log analysis
- **[MSInfo Processing](./data-msinfo-processing.md)** - System information analysis
- **[NATS Data Flow](./nats-dataflow.md)** - Agent communication and data pipeline

### Agent & Integration
- **[NATS Integration](./nats-integration.md)** - Agent communication architecture
- **[NATS Architecture](./nats-architecture.md)** - Technical NATS implementation
- **[Agent Development](./agent-development.md)** - Building and deploying agents

### Security
- **[Security Overview](./security-overview.md)** - Security architecture and best practices
- **[Cryptographic Key Rotation](./security-key-rotation.md)** - Zero-downtime key rotation system
- **[IP Blocker](./security-ip-blocker.md)** - IP blocking and rate limiting
- **[Authentication & Authorization](./security-auth.md)** - User management and permissions

### Infrastructure & Deployment
- **[Logging System](./infrastructure-logging.md)** - Application logging and monitoring
- **[Celery Tasks](./infrastructure-celery.md)** - Background job processing
- **[Redis Configuration](./infrastructure-redis.md)** - Caching and session management
- **[Portability Improvements](../PORTABILITY_IMPROVEMENTS.md)** - Multiple deployment modes and secret backends
- **[Secret Management](../app/utilities/secret_manager.py)** - Flexible secret storage (Azure KV, OpenBao, local .env)
- **[Configuration Validator](../app/utilities/config_validator.py)** - Pre-deployment validation
- **[Environment Configuration](../.env.example)** - Complete configuration reference
- **[OpenBao Setup](../config/secrets.openbao.example)** - Self-hosted secrets management guide

### User Interface
- **[UI Overview](./ui-overview.md)** - User interface architecture
- **[Guided Tour System](./ui-guided-tour.md)** - User onboarding tours
- **[UI Components](./ui-dictionary-component.md)** - Reusable UI components

### Features
- **[Device Deletion](./features-device-deletion.md)** - Device removal process
- **[Tenant Deletion](./features-tenant-deletion.md)** - Tenant cleanup process

### Developer Guide
- **[Developer Guide](./developer-guide.md)** - Development setup and workflow
- **[API Reference](./api-reference.md)** - REST API endpoints
- **[Testing Guide](./testing-guide.md)** - Writing and running tests

### Reference
- **[MSP Tools Reference](./reference-msp-tools.md)** - Curated list of MSP tools and platforms
- **[Glossary](./glossary.md)** - Key terms and definitions
- **[Implementation Checklist](../IMPLEMENTATION_CHECKLIST.md)** - Feature implementation status and testing
- **[Bug Fixes](../FIX_LOG.md)** - Recent bug fixes and resolutions

### Archive
- **[Archive](./archive/)** - Historical documentation and design iterations

---

## 🎯 Quick Navigation by Role

### 👤 End Users
1. Start with [Getting Started Guide](./getting-started.md)
2. Learn about [Core Features](./core-analysis-framework.md)
3. Explore [Multi-Entity Chat System](./core-multi-entity-chat.md)

### 👨‍💻 Developers
1. Read [Developer Guide](./developer-guide.md)
2. Understand [Architecture Overview](./architecture-overview.md)
3. Review [API Reference](./api-reference.md)
4. Check [Testing Guide](./testing-guide.md)

### 🏗️ DevOps/Infrastructure
1. Start with [Quick Start Guide](../QUICKSTART.md) for immediate deployment
2. Use [Installation Wizard](../install.sh) for guided setup
3. Review [Comprehensive Setup Guide](../SETUP_GUIDE.md) for all scenarios
4. Understand [Portability Improvements](../PORTABILITY_IMPROVEMENTS.md) for deployment options
5. Configure [Infrastructure - Logging](./infrastructure-logging.md)
6. Setup [Infrastructure - Redis](./infrastructure-redis.md)
7. Configure [Infrastructure - Celery](./infrastructure-celery.md)
8. For self-hosted: Follow [OpenBao Setup Guide](../config/secrets.openbao.example)

### 🔒 Security Team
1. Read [Security Overview](./security-overview.md)
2. Understand [Cryptographic Key Rotation](./security-key-rotation.md)
3. Review [Security - Authentication](./security-auth.md)
4. Configure [Security - IP Blocker](./security-ip-blocker.md)

### 🤖 Agent Developers
1. Start with [Agent Development](./agent-development.md)
2. Understand [NATS Integration](./nats-integration.md)
3. Review [NATS Architecture](./nats-architecture.md)
4. Study [NATS Data Flow](./nats-dataflow.md)

---

## 📚 Key Concepts

### Hierarchical Structure
Wegweiser uses a four-level hierarchy:
- **Tenant** = MSP (Managed Service Provider)
- **Organization** = MSP's client
- **Group** = Collection of devices within an organization
- **Device** = Individual machine being monitored

### Health Scoring
- Individual analyses produce scores (1-100)
- Device scores aggregate from multiple analyses
- Scores cascade up: Device → Group → Organization → Tenant

### Multi-Tenancy
- Strict data isolation between tenants
- Tenant-based access control
- Subject-based permissions in NATS

### AI Integration
- Multiple AI providers supported (Azure OpenAI, OpenAI, Claude, Ollama)
- Context-aware analysis at each hierarchy level
- Conversation memory and tracking

---

## 🔄 Documentation Maintenance

This documentation is maintained to reflect the current state of the codebase. If you find outdated information:

1. Check the [Archive](./archive/) for historical context
2. Review recent code changes
3. Submit updates or corrections

**Last Updated:** 2025-10-24 - Portability enhancements, flexible secret management, and installation wizard added

---

## 📞 Need Help?

- 📧 Check the [FAQ](./faq.md) for common questions
- 🐛 Report issues on GitHub
- 💬 Join our community discussions

