# Security Overview

Wegweiser implements comprehensive security measures to protect MSP and client data.

## Security Architecture

### Multi-Tenancy & Data Isolation
- **Tenant Isolation** - Strict separation between MSPs
- **Row-Level Security** - Database queries filtered by tenant
- **Subject-Based Permissions** - NATS messaging with tenant-specific subjects
- **Query Filtering** - All database queries include tenant context

### Authentication & Authorization
- **Session Management** - Flask-Session with Redis backend
- **Role-Based Access Control (RBAC)** - Fine-grained permissions
- **Login Required** - All protected routes require authentication
- **Role Checking** - Decorators enforce role requirements

### Data Protection
- **Azure Key Vault** - All secrets stored securely
- **No Hardcoded Secrets** - Configuration via environment or Key Vault
- **Encrypted Connections** - HTTPS/TLS for all communications
- **Database Credentials** - Managed through Key Vault

## Security Features

### IP Blocking
See [IP Blocker Documentation](./security-ip-blocker.md) for details on:
- Rate limiting
- Suspicious activity detection
- Automatic IP blocking
- Whitelist/blacklist management

### CSRF Protection
- CSRF tokens on all forms
- Token validation on POST/PUT/DELETE
- Exempt endpoints for API calls (with proper authentication)

### Security Headers
- Content-Security-Policy
- X-Frame-Options
- X-Content-Type-Options
- Strict-Transport-Security

### Agent Communication
- NATS authentication with tenant credentials
- Subject-based access control
- Message signing and validation
- Secure credential distribution
- Cryptographic key rotation with zero downtime

## Authentication & Authorization

### User Roles
- **Admin** - Full system access
- **Manager** - Organization/group management
- **Technician** - Device viewing and analysis
- **Viewer** - Read-only access

### Permission Model
- Tenant-level permissions
- Organization-level permissions
- Group-level permissions
- Device-level permissions

### Session Security
- Secure session cookies
- Session timeout
- Redis-backed sessions
- Fallback to filesystem if Redis unavailable

## Compliance & Best Practices

### Data Handling
- Minimal data collection
- Data retention policies
- Secure deletion procedures
- Audit logging

### API Security
- Authentication required for all endpoints
- Rate limiting on sensitive endpoints
- Input validation and sanitization
- Output encoding

### Deployment Security
- Secrets in Azure Key Vault
- Environment-specific configuration
- Secure defaults
- Regular security updates

## Threat Model

### Protected Against
- Unauthorized data access
- Cross-tenant data leakage
- Privilege escalation
- CSRF attacks
- SQL injection
- XSS attacks
- Brute force attacks

### Monitoring
- Failed login attempts
- Suspicious IP activity
- Unusual data access patterns
- API rate limit violations

## Security Audit

For detailed security analysis, see:
- [ROUTES_MISSING_ROLE_CHECKING.md](./archive/routes-missing-role-checking.md) - Security audit findings
- [SECURITY_ASSESSMENT_REPORT.md](./archive/security-assessment-report.md) - Comprehensive assessment

## Incident Response

### Reporting Security Issues
- Do not create public issues for security vulnerabilities
- Email security team with details
- Include reproduction steps
- Allow time for patch development

### Response Process
1. Acknowledge receipt
2. Investigate and assess severity
3. Develop and test fix
4. Release security patch
5. Notify affected users

## Security Checklist

### Development
- [ ] No secrets in code
- [ ] Input validation on all endpoints
- [ ] Output encoding for XSS prevention
- [ ] SQL injection prevention (use ORM)
- [ ] CSRF tokens on forms
- [ ] Role checking on protected routes

### Deployment
- [ ] Secrets in Azure Key Vault
- [ ] HTTPS/TLS enabled
- [ ] Security headers configured
- [ ] Database backups encrypted
- [ ] Logs secured and monitored
- [ ] Regular security updates

### Operations
- [ ] Monitor failed login attempts
- [ ] Review access logs regularly
- [ ] Update IP blocklist
- [ ] Rotate credentials periodically
- [ ] Test disaster recovery
- [ ] Conduct security audits

## Related Documentation

- [Cryptographic Key Rotation](./security-key-rotation.md)
- [Authentication & Authorization](./security-auth.md)
- [IP Blocker](./security-ip-blocker.md)
- [NATS Integration](./nats-integration.md)

---

**Next:** Review [IP Blocker Documentation](./security-ip-blocker.md) for rate limiting details.

