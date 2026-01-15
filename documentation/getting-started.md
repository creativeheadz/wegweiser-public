# Getting Started with Wegweiser

Welcome to Wegweiser! This guide will help you get up and running quickly.

## For End Users

### Step 1: Register
1. Visit [https://app.wegweiser.tech/register](https://app.wegweiser.tech/register)
2. Create your account
3. Receive 250 FREE Wegcoins for evaluation

### Step 2: Deploy the Agent
1. Navigate to your organization settings
2. Download the appropriate agent for your platform:
   - Windows (PowerShell installer)
   - Linux (Bash script)
   - macOS (Bash script)
3. Deploy through your existing RMM or manually on test machines

### Step 3: Start Analyzing
1. Wait for initial data collection (typically 5-10 minutes)
2. View device health scores in your dashboard
3. Use the AI chat to ask questions about your devices
4. Review recommendations and insights

### Step 4: Explore Features
- **Device Dashboard** - View health scores and metrics
- **AI Chat** - Ask questions at device, group, or organization level
- **Health Insights** - Get AI-powered recommendations
- **Event Analysis** - Deep dive into security and system events

## For Developers

### Prerequisites
- Python 3.9+
- PostgreSQL 12+
- Redis 6+
- Git

### Quick Setup

1. **Clone the repository**
   ```bash
   git clone https://github.com/creativeheadz/wegweiser.git
   cd wegweiser
   ```

2. **Create virtual environment**
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment**
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

5. **Initialize database**
   ```bash
   export FLASK_APP=wsgi.py
   flask db upgrade
   flask create_roles
   ```

6. **Start development server**
   ```bash
   python wsgi.py
   ```

7. **Start Celery worker** (in another terminal)
   ```bash
   celery -A app.celery worker --loglevel=info
   ```

8. **Start Celery beat** (in another terminal)
   ```bash
   celery -A app.celery beat --loglevel=info
   ```

Access the application at `http://localhost:5000`

### Running Tests
```bash
pytest
pytest tests/test_specific.py  # Run specific test
pytest --cov=app tests/        # With coverage
```

## Key Concepts

### Hierarchical Structure
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
```

### Health Scoring
Each device receives a health score (1-100) based on:
- Security events analysis
- System stability
- Driver health
- Performance metrics
- And more...

Scores aggregate up the hierarchy for organization and tenant-level insights.

### AI Chat
Available at every level:
- **Device level** - Specific machine insights
- **Group level** - Aggregate group health
- **Organization level** - Client-wide analysis
- **Tenant level** - MSP-wide analytics

## Next Steps

- Read the [Architecture Overview](./architecture-overview.md) to understand the system
- Check the [Developer Guide](./developer-guide.md) for detailed development info
- Review [API Reference](./api-reference.md) for available endpoints
- Explore [Core Features](./core-analysis-framework.md) documentation

## Troubleshooting

### Agent not connecting?
- Check network connectivity
- Verify agent credentials
- Review logs in `/opt/wegweiser/wlog/`

### Database errors?
- Ensure PostgreSQL is running
- Check database credentials in `.env`
- Run migrations: `flask db upgrade`

### Celery tasks not running?
- Verify Redis is running
- Check Celery worker logs
- Ensure beat scheduler is running

## Support

- 📚 Check [Documentation Index](./INDEX.md) for detailed guides
- 🐛 Report issues on GitHub
- 💬 Join community discussions
- 📧 Contact support team

---

**Ready to dive deeper?** → [Architecture Overview](./architecture-overview.md)

