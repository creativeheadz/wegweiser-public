# Documentation Structure

This file describes the organization and structure of Wegweiser documentation.

## Directory Layout

```
documentation/
├── INDEX.md                          # Main documentation index
├── STRUCTURE.md                      # This file
│
├── Getting Started
├── getting-started.md                # First steps for users and developers
├── installation-setup.md             # Installation and configuration
│
├── Architecture & Design
├── architecture-overview.md          # System architecture and components
├── database-schema.md                # Database models and relationships
├── multi-tenancy.md                  # Multi-tenant architecture
│
├── Core Features
├── core-analysis-framework.md        # Analysis system documentation
├── core-multi-entity-chat.md         # AI chat system
├── core-health-scoring.md            # Health scoring system
│
├── Data Processing
├── data-eventlog-processing.md       # Windows event log analysis
├── data-msinfo-processing.md         # System information analysis
├── nats-dataflow.md                  # Data flow through NATS
│
├── Agent & Integration
├── agent-development.md              # Agent development guide
├── nats-integration.md               # NATS integration overview
├── nats-architecture.md              # NATS technical architecture
│
├── Security
├── security-overview.md              # Security architecture
├── security-auth.md                  # Authentication and authorization
├── security-ip-blocker.md            # IP blocking and rate limiting
│
├── Infrastructure
├── infrastructure-logging.md         # Logging system
├── infrastructure-celery.md          # Celery task queue
├── infrastructure-redis.md           # Redis configuration
│
├── User Interface
├── ui-overview.md                    # UI architecture
├── ui-guided-tour.md                 # Guided tour system
├── ui-dictionary-component.md        # UI components
│
├── Features
├── features-device-deletion.md       # Device deletion process
├── features-tenant-deletion.md       # Tenant deletion process
│
├── Developer Guide
├── developer-guide.md                # Development setup and workflow
├── api-reference.md                  # REST API endpoints
├── testing-guide.md                  # Testing and QA
│
├── Reference
├── reference-msp-tools.md            # MSP tools and platforms
├── glossary.md                       # Key terms and definitions
│
└── archive/                          # Historical documentation
    ├── README.md                     # Archive index
    ├── DESIGN_*.md                   # Design phase documents
    ├── PHASE_*.md                    # Phase completion markers
    ├── SIDEBAR_*.md                  # UI design iterations
    ├── ROUTES_MISSING_ROLE_CHECKING.md
    ├── SECURITY_ASSESSMENT_REPORT.md
    └── ... (other historical docs)
```

## Naming Conventions

### File Naming
- **Format**: `kebab-case.md`
- **Prefix**: Category prefix for organization
  - `core-` - Core features
  - `data-` - Data processing
  - `security-` - Security features
  - `infrastructure-` - Infrastructure
  - `ui-` - User interface
  - `features-` - Feature documentation
  - `reference-` - Reference materials

### Examples
- ✅ `core-analysis-framework.md`
- ✅ `data-eventlog-processing.md`
- ✅ `security-ip-blocker.md`
- ❌ `Analysis_Framework_Documentation.md`
- ❌ `eventlog processing.md`

## Content Organization

### Each Document Should Include

1. **Title** - Clear, descriptive heading
2. **Overview** - Brief introduction
3. **Key Concepts** - Main ideas and terminology
4. **Implementation Details** - How it works
5. **Configuration** - Setup and customization
6. **Examples** - Code samples or use cases
7. **Related Documentation** - Links to related docs
8. **Next Steps** - Suggested reading

### Document Template

```markdown
# Document Title

Brief introduction and purpose.

## Overview

What this feature/component does.

## Key Concepts

Important ideas and terminology.

## Implementation

How it's implemented in the codebase.

## Configuration

Setup and customization options.

## Examples

Code samples and use cases.

## Related Documentation

- [Link](./path.md)
- [Link](./path.md)

---

**Next:** [Next Document](./next.md)
```

## Navigation

### Quick Links by Role

**End Users**
- [Getting Started](./getting-started.md)
- [Core Features](./core-analysis-framework.md)
- [UI Overview](./ui-overview.md)

**Developers**
- [Developer Guide](./developer-guide.md)
- [Architecture Overview](./architecture-overview.md)
- [API Reference](./api-reference.md)

**DevOps/Infrastructure**
- [Installation & Setup](./installation-setup.md)
- [Infrastructure - Logging](./infrastructure-logging.md)
- [Infrastructure - Celery](./infrastructure-celery.md)

**Security Team**
- [Security Overview](./security-overview.md)
- [Security - Authentication](./security-auth.md)
- [Security - IP Blocker](./security-ip-blocker.md)

**Agent Developers**
- [Agent Development](./agent-development.md)
- [NATS Integration](./nats-integration.md)
- [NATS Architecture](./nats-architecture.md)

## Maintenance

### Keeping Documentation Current

1. **Update on Code Changes**
   - When adding features, update relevant docs
   - When changing APIs, update API reference
   - When modifying architecture, update architecture docs

2. **Review Cycle**
   - Monthly review of core documentation
   - Quarterly comprehensive review
   - Annual major restructuring if needed

3. **Version Control**
   - Documentation changes tracked in git
   - Archive old versions in `/archive`
   - Link to related code commits when relevant

### Adding New Documentation

1. Choose appropriate category
2. Use consistent naming convention
3. Follow document template
4. Add to INDEX.md
5. Link from related documents
6. Update STRUCTURE.md if adding new category

## Search & Discovery

### Using Documentation

- **INDEX.md** - Start here for overview
- **Search** - Use Ctrl+F to search within docs
- **Links** - Follow related documentation links
- **Glossary** - Look up unfamiliar terms

### Contributing

- Found outdated information? Update it
- Missing documentation? Create it
- Unclear explanation? Improve it
- Broken links? Fix them

## Last Updated

2025-10-19

---

**Start Here:** [Documentation Index](./INDEX.md)
