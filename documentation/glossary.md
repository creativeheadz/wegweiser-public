# Glossary

Key terms and definitions used throughout Wegweiser.

## A

**Agent**
Lightweight software deployed on endpoints (Windows, Linux, macOS) that collects system data and sends it to Wegweiser for analysis.

**Analyzer**
A component that processes specific types of system data and produces health scores. Examples: SecurityAnalyzer, DriverAnalyzer, PerformanceAnalyzer.

**Azure Key Vault**
Microsoft Azure service for securely storing and managing secrets, API keys, and credentials.

## B

**Baseline**
Historical average or expected value used for comparison in anomaly detection.

**Billing**
System for tracking and charging Wegcoins for analysis operations.

## C

**Celery**
Distributed task queue used for background processing and scheduled analysis tasks.

**Chat**
AI-powered conversational interface available at every hierarchical level for asking questions about system health and getting recommendations.

**Context**
Historical data and information about an entity used to provide more accurate AI analysis and recommendations.

## D

**Device**
Individual machine being monitored (computer, server, workstation).

**Device Metadata**
Raw data collected from devices including event logs, system information, performance metrics.

## E

**Entity**
Any object in the hierarchy: Device, Group, Organization, or Tenant.

**Event Log**
Windows Security Event Log containing security, system, and application events.

## G

**Group**
Collection of devices within an organization, used for organizing and managing related machines.

**Gunicorn**
Python WSGI HTTP Server used for running Flask application in production.

## H

**Health Score**
Numerical value (1-100) representing the overall health of a device, group, organization, or tenant.

**Hierarchical**
Organized in levels: Tenant → Organization → Group → Device.

## I

**IP Blocker**
Security feature that blocks suspicious IP addresses based on failed login attempts and other indicators.

## J

**JetStream**
NATS feature providing message persistence and replay capabilities.

## K

**Keyvault**
See Azure Key Vault.

## M

**MSP**
Managed Service Provider - the service provider managing multiple client organizations.

**Multi-Tenancy**
Architecture supporting multiple independent tenants (MSPs) with strict data isolation.

## N

**NATS**
Messaging system used for agent communication with tenant-based subject isolation.

**Node-RED**
Previous agent communication system (replaced by NATS).

## O

**Organization**
Client of an MSP, representing a business or entity being managed.

**ORM**
Object-Relational Mapping - SQLAlchemy ORM used for database operations.

## P

**PostgreSQL**
Relational database used for storing all Wegweiser data.

**Payload**
Data sent from agents to the server (event logs, system info, etc.).

## R

**RBAC**
Role-Based Access Control - permission system based on user roles.

**Recommendation**
AI-generated suggestion for improving system health or addressing issues.

**Redis**
In-memory data store used for caching and session management.

**RMM**
Remote Monitoring and Management - existing tools that Wegweiser integrates with.

## S

**Score**
See Health Score.

**Security Event**
Event in Windows Security Event Log indicating security-related activity.

**Session**
User login session managed by Flask-Session with Redis backend.

**SQLAlchemy**
Python ORM library used for database operations.

**Subject**
NATS messaging topic following pattern: `tenant.{uuid}.device.{uuid}.{type}`.

## T

**Task**
Background job processed by Celery, typically an analysis operation.

**Tenant**
Top-level entity representing an MSP (Managed Service Provider).

**Trend**
Historical pattern in health scores or metrics over time.

## U

**UI**
User Interface - web application for viewing devices and interacting with Wegweiser.

## V

**Visualization**
Charts, graphs, and dashboards displaying health scores and metrics.

## W

**Wegcoin**
Virtual currency used for billing analysis operations.

**Wegweiser**
German word meaning "signpost" or "guide" - the name of this platform.

**WebSocket**
Protocol for real-time bidirectional communication (used in persistent agent).

## X

**XDR**
Extended Detection and Response - advanced security monitoring and response.

## Z

**Zero-Trust**
Security model assuming no implicit trust, requiring verification for all access.

---

## Related Documentation

- [Architecture Overview](./architecture-overview.md)
- [Getting Started](./getting-started.md)
- [Developer Guide](./developer-guide.md)

---

**Last Updated:** 2025-10-19

