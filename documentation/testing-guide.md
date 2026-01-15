# Testing Guide

Comprehensive guide for writing and running tests in Wegweiser.

## Test Structure

```
tests/
├── conftest.py              # Pytest fixtures and configuration
├── pytest.ini               # Pytest configuration
├── test_api_endpoints.py    # API endpoint tests
├── test_csrf_fix.py         # CSRF protection tests
├── test_formatter.py        # Formatter tests
├── test_logging_config.py   # Logging tests
├── test_nats_integration.py # NATS integration tests
├── test_registration_bonus.py
├── test_session_fallback.py # Session fallback tests
├── test_socketio_import.py  # SocketIO tests
└── unit/                    # Unit tests by module
```

## Running Tests

### Run All Tests
```bash
pytest
```

### Run Specific Test File
```bash
pytest tests/test_api_endpoints.py
```

### Run Specific Test
```bash
pytest tests/test_api_endpoints.py::test_get_devices
```

### Run with Coverage
```bash
pytest --cov=app tests/
pytest --cov=app --cov-report=html tests/
```

### Run with Verbose Output
```bash
pytest -v
pytest -vv  # Extra verbose
```

### Run with Markers
```bash
pytest -m "unit"
pytest -m "integration"
pytest -m "not slow"
```

## Writing Tests

### Basic Test Structure
```python
import pytest
from app import create_app, db

@pytest.fixture
def app():
    app = create_app('testing')
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()

@pytest.fixture
def client(app):
    return app.test_client()

def test_get_devices(client):
    response = client.get('/api/devices')
    assert response.status_code == 200
```

### Using Fixtures
```python
@pytest.fixture
def user(app):
    user = User(username='testuser', email='test@example.com')
    db.session.add(user)
    db.session.commit()
    return user

def test_user_creation(user):
    assert user.username == 'testuser'
```

### Testing Database Operations
```python
def test_create_device(app):
    with app.app_context():
        device = Device(name='Test Device')
        db.session.add(device)
        db.session.commit()
        
        retrieved = Device.query.filter_by(name='Test Device').first()
        assert retrieved is not None
```

### Testing API Endpoints
```python
def test_get_device(client, user):
    response = client.get(f'/api/devices/{device_id}')
    assert response.status_code == 200
    data = response.get_json()
    assert data['name'] == 'Test Device'
```

### Testing Authentication
```python
def test_protected_endpoint_requires_auth(client):
    response = client.get('/api/devices')
    assert response.status_code == 401

def test_protected_endpoint_with_auth(client, user):
    with client:
        client.post('/login', data={
            'username': user.username,
            'password': 'password'
        })
        response = client.get('/api/devices')
        assert response.status_code == 200
```

### Testing Error Handling
```python
def test_invalid_device_id(client):
    response = client.get('/api/devices/invalid-id')
    assert response.status_code == 404
    data = response.get_json()
    assert 'error' in data
```

## Test Categories

### Unit Tests
Test individual functions and classes in isolation.

```python
def test_health_score_calculation():
    scores = [80, 85, 90, 75]
    result = calculate_average_health(scores)
    assert result == 82.5
```

### Integration Tests
Test interactions between components.

```python
def test_device_health_score_aggregation(app):
    # Create devices and groups
    # Verify health scores aggregate correctly
    pass
```

### API Tests
Test REST API endpoints.

```python
def test_api_device_list(client):
    response = client.get('/api/devices')
    assert response.status_code == 200
```

### Database Tests
Test database operations and migrations.

```python
def test_database_migration(app):
    # Verify migration applied correctly
    pass
```

## Fixtures

### Common Fixtures (conftest.py)
```python
@pytest.fixture
def app():
    """Create application for testing"""
    
@pytest.fixture
def client(app):
    """Create test client"""
    
@pytest.fixture
def runner(app):
    """Create CLI runner"""
    
@pytest.fixture
def user(app):
    """Create test user"""
    
@pytest.fixture
def organization(app, user):
    """Create test organization"""
    
@pytest.fixture
def device(app, organization):
    """Create test device"""
```

## Mocking

### Mock External Services
```python
from unittest.mock import patch, MagicMock

@patch('app.utilities.ai_provider.analyze')
def test_analysis_with_mock(mock_analyze):
    mock_analyze.return_value = {'score': 85}
    result = analyze_device(device_id)
    assert result['score'] == 85
```

### Mock Database
```python
@patch('app.models.Device.query')
def test_with_mock_db(mock_query):
    mock_query.filter_by.return_value.first.return_value = device
    result = get_device(device_id)
    assert result.name == 'Test Device'
```

## Test Coverage

### Generate Coverage Report
```bash
pytest --cov=app --cov-report=html tests/
```

### View Coverage Report
```bash
open htmlcov/index.html
```

### Coverage Targets
- **Overall** - Aim for 80%+ coverage
- **Critical paths** - 100% coverage
- **Utilities** - 90%+ coverage
- **Models** - 85%+ coverage

## Continuous Integration

### GitHub Actions
Tests run automatically on:
- Push to main branch
- Pull requests
- Scheduled daily runs

### Test Requirements
- All tests must pass
- Coverage must not decrease
- No new warnings

## Best Practices

### Do's
- ✅ Write tests for new features
- ✅ Test edge cases and error conditions
- ✅ Use descriptive test names
- ✅ Keep tests focused and isolated
- ✅ Use fixtures for setup/teardown
- ✅ Mock external dependencies

### Don'ts
- ❌ Don't test implementation details
- ❌ Don't create interdependent tests
- ❌ Don't use real external services
- ❌ Don't hardcode test data
- ❌ Don't skip failing tests
- ❌ Don't commit with failing tests

## Debugging Tests

### Run with Print Statements
```bash
pytest -s tests/test_file.py
```

### Run with Debugger
```bash
pytest --pdb tests/test_file.py
```

### Run Single Test with Verbose Output
```bash
pytest -vv -s tests/test_file.py::test_name
```

## Performance Testing

### Measure Test Execution Time
```bash
pytest --durations=10 tests/
```

### Profile Slow Tests
```bash
pytest --profile tests/
```

---

**Next:** Review [API Reference](./api-reference.md) for endpoint documentation.

