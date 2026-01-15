# Developer Guide

This guide provides comprehensive information for developers working on Wegweiser.

## Development Philosophy

**RMM Enhancement, Not Replacement**
- Build features that complement existing RMM tools
- Focus on intelligence and insights, not basic monitoring
- Maintain RMM-agnostic approach

**MSP-First Design**
- Every feature should solve real MSP pain points
- Consider the client onboarding workflow
- Think hierarchically (device → group → org → tenant)

**AI as Core Differentiator**
- Leverage AI for system insights, not just chat responses
- Build context-aware analysis capabilities
- Focus on bridging the knowledge gap for MSPs

**Reliability Over Features**
- Agents must be low-profile and reliable
- Graceful degradation when connections fail
- Comprehensive error handling and logging

## Development Setup

### Environment Setup
```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
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
# Run all tests
pytest

# Run specific test file
pytest tests/test_specific.py

# Run with coverage
pytest --cov=app tests/
```

## Architecture Guidelines

### Business Logic Priority
- **Health Scoring** - All analyses must contribute to hierarchical health scoring
- **Context Awareness** - Chat responses should leverage hierarchical context
- **MSP Workflow** - Consider the MSP's client onboarding and management workflow
- **Data Aggregation** - Ensure proper data flow from device → group → org → tenant

### Database
- Use Flask-Migrate for all schema changes
- Always test migrations in development first
- Use the `safe_db_session` context manager for complex operations
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

## Project Structure

```
app/
├── __init__.py              # Application factory
├── models/                  # Database models
├── routes/                  # API endpoints (blueprints)
├── tasks/                   # Background analysis tasks
├── utilities/               # Helper functions
├── templates/               # HTML templates
├── static/                  # CSS, JavaScript, assets
├── handlers/                # Message handlers
├── forms/                   # WTForms definitions
├── config/                  # Configuration
└── extensions.py            # Flask extensions
```

## Key Files and Locations

- **Application entry point** - `wsgi.py`
- **Main app factory** - `app/__init__.py`
- **Database models** - `app/models/`
- **Routes/blueprints** - `app/routes/`
- **Background tasks** - `app/tasks/` (critical for health scoring)
- **Utilities** - `app/utilities/`
- **Static assets** - `app/static/`
- **Templates** - `app/templates/`
- **Configuration** - `gunicorn.conf.py`
- **Database migrations** - `migrations/`
- **Tests** - `tests/`
- **Agent scripts** - `agent/`, `downloads/`

## External Dependencies

- **Database** - PostgreSQL with connection pooling
- **Cache/Sessions** - Redis for session storage and caching
- **Task Queue** - Celery with Redis broker
- **Secrets** - Azure Key Vault for all sensitive configuration
- **AI Services** - Azure OpenAI, OpenAI, Anthropic Claude, Ollama
- **Email** - SMTP configuration via Azure Key Vault
- **Monitoring** - Custom logging with optional remote logging

## Common Development Tasks

### Adding a New Route
1. Create blueprint in `app/routes/`
2. Register in `app/__init__.py`
3. Add role checking decorators
4. Write tests in `tests/`

### Adding a New Analysis Task
1. Create analyzer in `app/tasks/`
2. Inherit from `BaseAnalyzer`
3. Define configuration in `definition.py`
4. Create prompt template
5. Register in task scheduler

### Adding a Database Model
1. Create model in `app/models/`
2. Create migration: `flask db migrate -m "Add new model"`
3. Review migration file
4. Apply: `flask db upgrade`

### Writing Tests
1. Create test file in `tests/`
2. Use pytest fixtures from `conftest.py`
3. Follow existing test patterns
4. Run: `pytest tests/test_file.py`

## Code Standards

- Follow PEP 8 for Python code
- Use type hints where possible
- Write docstrings for functions and classes
- Keep functions focused and testable
- Use meaningful variable names

## Debugging

### Enable Debug Logging
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

### Database Debugging
```bash
# Connect to PostgreSQL
psql -U wegweiser -d wegweiser_db

# View recent logs
tail -f /opt/wegweiser/wlog/wegweiser.log
```

### Celery Debugging
```bash
# Monitor tasks
celery -A app.celery events

# Inspect active tasks
celery -A app.celery inspect active
```

## Performance Considerations

- Use database indexes for frequently queried fields
- Implement caching for expensive operations
- Batch process large datasets
- Monitor Celery task queue depth
- Profile code before optimizing

---

**Next:** Review [Architecture Overview](./architecture-overview.md) for system design details.

