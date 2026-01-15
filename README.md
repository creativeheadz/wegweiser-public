## Wegweiser

Wegweiser is an AI‑powered intelligence layer for Managed Service Providers (MSPs). It sits on top of your existing RMM tooling to:

- Analyze devices, groups, organizations, and tenants
- Produce hierarchical health scores and actionable insights
- Provide context‑aware AI chat at every level (device → group → org → tenant)
- Help close the knowledge gap for complex environments and new customer onboarding

This repository contains the core Wegweiser web application, background analysis pipeline, and supporting utilities.

---

## Table of Contents

- [Overview](#overview)
- [Key Features](#key-features)
- [Architecture](#architecture)
- [Data Model & Hierarchy](#data-model--hierarchy)
- [Analysis & Health Scoring](#analysis--health-scoring)
- [AI Chat & Knowledge Layer](#ai-chat--knowledge-layer)
- [Security & Multi‑Tenancy](#security--multi-tenancy)
- [Getting Started](#getting-started)
- [Agents & Data Collection](#agents--data-collection)
- [Development & Testing](#development--testing)
- [Further Documentation](#further-documentation)

---

## Overview

Traditional RMM tools collect metrics but rarely explain what they mean for the business or where to start. Wegweiser focuses on two MSP problems:

1. **Client Onboarding Hell** – uncovering hidden issues across a new client’s environment.
2. **The Knowledge Gap** – nobody can know every hardware type, event log, or edge case.

Wegweiser ingests system and event data from agents, runs it through an AI‑powered analysis pipeline, and surfaces:

- Health scores from device level up to the MSP tenant
- Contextual explanations and remediation suggestions
- A multi‑level chat interface that understands your MSP hierarchy

---

## Key Features

- **Hierarchical Health Scoring**
  - Device health scores built from multiple domain‑specific analyzers (hardware, network, security, etc.)
  - Aggregation from Device → Group → Organisation (client) → Tenant (MSP)
  - Historical tracking of health changes and update logs

- **Multi‑Entity AI Chat**
  - Chat "at" any level: device, group, organisation, tenant
  - Conversation and memory models keep context across interactions
  - Can reference collected device metadata, event logs, and analysis results

- **RMM‑Agnostic Data Collection**
  - Agents as scheduled tasks (Windows) or cronjobs (Linux/macOS)
  - OSQuery and other sources via NATS integration
  - Endpoint preprocessing to reduce bandwidth and normalize data

- **Guided Onboarding & UI**
  - Guided tours and quick‑start flows for tenants
  - Device, group, organisation, and tenant management pages
  - Message centre, support ticket integration, and notifications

- **Multi‑Tenant SaaS**
  - Tenant = MSP
  - Organisations = MSP customers
  - Strict tenant isolation in the data model and access controls

- **Production‑Ready Infrastructure**
  - Flask app with application factory pattern
  - PostgreSQL with SQLAlchemy and Flask‑Migrate
  - Redis for sessions and Celery for background processing
  - Azure Key Vault‑backed secrets with flexible fallbacks
  - Strong security posture: CSRF, security headers, IP blocking, role‑based access

---

## Architecture

- **Web Application**
  - Entry point: `wsgi.py` (creates the Flask app via `create_app()`)
  - App factory: `app/__init__.py` configures DB, sessions, Celery, logging, security headers, CSRF, email, AI providers
  - Registers all blueprints dynamically from `app/routes/`

- **Database Layer**
  - SQLAlchemy models in `app/models/`
  - Core entities: tenants, organisations, groups, devices and metadata; accounts, roles, MFA; AI memory, conversations, context; health score history and logs

- **Routes / Blueprints**
  - Modular structure in `app/routes/`, including:
    - `admin/` – admin tools and snippet management
    - `ai/` – AI chat, entity‑specific AI, health analysis integration
    - `agents/` – agent API endpoints
    - `devices/` – device list, details, registration, restore, tagging, widgets, event logs
    - `groups/`, `organisations/` – hierarchy management
    - `tenant/` – tenant profile, quick start, CSV import, account management
    - `login/`, `auth/` – login, Azure AD OAuth, MFA, registration, email verification
    - `nats/`, `osquery/` – agent communication and OSQuery APIs
    - `messagecentre/`, `support/` – message centre and support ticket integration

- **Background Tasks**
  - Domain‑specific analyzer packages under `app/tasks/` (hardware, network, security, system, programs, logs, macOS, organisations, tenant, suggestions)
  - Shared base definitions in `app/tasks/base/` for analyzer interfaces, scheduling, and billing
  - Utilities like `sys_function_generate_healthscores.py` and `sys_function_process_payloads.py` orchestrate health score generation and payload processing

- **Utilities & Helpers**
  - `app/utilities/` provides logging helpers, IP blocker, session manager, secret manager, NATS manager, OSQuery helpers, guided tours, notifications, webhook sender
  - Chat & AI utilities (LangChain helpers, knowledge graph, memory store) live under `app/utilities/chat/`
  - Device data providers in `app/utilities/device_data_providers/` aggregate and normalize endpoint data

---

## Data Model & Hierarchy

Wegweiser is built around an MSP‑centric hierarchy:

- **Tenant** – the MSP (service provider)
- **Organisation** – a client of the MSP
- **Group** – a collection of devices within an organisation
- **Device** – an individual endpoint

Models in `app/models/` enforce:

- Strict tenant isolation
- Relationships between users and organisations (e.g. `userxorganisation`)
- Dedicated metadata tables (`devicemetadata`, `groupmetadata`, `orgmetadata`, `tenantmetadata`) for extended attributes

---

## Analysis & Health Scoring

- Agents send structured data (hardware, software, logs, OS info, security audits)
- Celery tasks in `app/tasks/` run analyzers across domains such as hardware, storage, network, system, software, security, crashes, logs, Lynis audits, macOS‑specific components
- Each analyzer produces a normalized health score (1–100) plus narrative summaries and recommendations
- Scores aggregate: Device → Group → Organisation → Tenant, with history stored for trend analysis

---

## AI Chat & Knowledge Layer

- Multi‑entity chat in `app/routes/ai/` and `app/utilities/chat/` lets you chat at device, group, organisation or tenant level
- Conversations, memory, and context are stored in models like `conversations`, `ai_memory`, and `context`
- Provider‑agnostic helpers support Azure OpenAI and other providers; knowledge graph and retrieval agents augment responses with environment‑specific data

---

## Security & Multi‑Tenancy

- **Secrets & Configuration** via Azure Key Vault (`get_secret()` in `app/__init__.py`) with environment fallbacks and additional backends via `secret_manager`
- **Session Security** with Redis‑backed or filesystem sessions, signed secure cookies, and custom session tracking
- **IP Blocking & Abuse Prevention** using LMDB/Redis (`ip_blocker`) integrated into error handlers
- **Web Security** via CSRF protection and strict security headers (CSP, HSTS, X‑Frame‑Options, X‑Content‑Type‑Options, X‑XSS‑Protection, Referrer‑Policy)
- **Authentication & Authorization** with local login, MFA, Azure AD OAuth, and role‑based access via Flask‑Principal

---

## Getting Started

High‑level steps (see detailed docs for variants):

1. **Create and activate a virtualenv**
   - `python3 -m venv venv && source venv/bin/activate`
2. **Install dependencies** (see docs or `requirements` tooling if provided)
3. **Configure environment** using `.env.example` as a baseline and wiring secrets via Azure Key Vault or another backend
4. **Initialize the database**:
   - `export FLASK_APP=wsgi.py`
   - `flask db init` (first time), then `flask db migrate` and `flask db upgrade`
   - Run custom commands like `flask populate_servercore` and `flask create_roles`
5. **Run the app**:
   - Development: `python wsgi.py`
   - Production: `gunicorn --config gunicorn.conf.py wsgi:app`
6. **Start background workers**:
   - `celery -A app.celery worker --loglevel=info`
   - `celery -A app.celery beat --loglevel=info`

---

## Agents & Data Collection

- Agents (Windows scheduled tasks, Linux/macOS cronjobs) and OSQuery integrations collect endpoint data
- NATS‑based communication is handled under `app/routes/nats/` with helpers in `app/utilities/nats_manager.py`
- Device data includes inventory, storage, network, OS and security logs, and audit information, feeding into analyzers and device metadata tables

---

## Development & Testing

- Standard Python/Flask development workflow: feature branches, migrations via Flask‑Migrate, and Celery for background tasks
- Tests run with `pytest`; see `documentation/testing-guide.md` for details and patterns

---

## Further Documentation

This README is a high‑level overview. For deeper details, see:

- `documentation/INDEX.md` – documentation index and navigation
- `documentation/getting-started.md` – onboarding for new users and developers
- `documentation/architecture-overview.md` – detailed architecture
- `documentation/database-schema.md` – schema and relationships
- `documentation/core-analysis-framework.md` – analysis pipeline internals
- `documentation/core-multi-entity-chat.md` – multi‑entity chat design
- `documentation/security-overview.md` – security architecture
- `documentation/infrastructure-redis.md`, `infrastructure-celery.md`, `infrastructure-logging.md` – infrastructure details
- `documentation/developer-guide.md` – development workflow and conventions

