import os
import sys
import pytest
from flask import Flask
from flask.testing import FlaskClient

# Add the parent directory to the path so we can import the app
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app
from app.models import db as _db

@pytest.fixture(scope='session')
def app():
    """Create and configure a Flask app for testing."""
    # Create a test configuration
    app = create_app()
    
    # Use an in-memory SQLite database for testing
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    app.config['TESTING'] = True
    app.config['WTF_CSRF_ENABLED'] = False
    
    # Create the app context
    with app.app_context():
        yield app

@pytest.fixture(scope='session')
def client(app):
    """A test client for the app."""
    return app.test_client()

@pytest.fixture(scope='session')
def db(app):
    """Create and configure a database for testing."""
    with app.app_context():
        _db.create_all()
        yield _db
        _db.drop_all()

@pytest.fixture(scope='function')
def session(db):
    """Create a new database session for a test."""
    connection = db.engine.connect()
    transaction = connection.begin()
    
    # Create a session bound to the connection
    session = db.create_scoped_session(
        options=dict(bind=connection, binds={})
    )
    
    # Make the session the current session
    db.session = session
    
    yield session
    
    # Rollback the transaction and close the connection
    transaction.rollback()
    connection.close()
    session.remove()

@pytest.fixture
def logged_in_client(client):
    """A test client that is logged in."""
    with client.session_transaction() as session:
        session['user_id'] = '00000000-0000-0000-0000-000000000001'  # Mock user ID
        session['userfirstname'] = 'Test User'
        session['tenant_uuid'] = '00000000-0000-0000-0000-000000000002'  # Mock tenant ID
    return client
