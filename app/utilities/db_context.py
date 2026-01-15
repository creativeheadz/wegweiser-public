# Filepath: app/utilities/db_context.py
from contextlib import contextmanager
from app.models import db
from app.utilities.app_logging_helper import log_with_route
import logging

@contextmanager
def session_scope():
    """Provide a transactional scope around a series of operations."""
    try:
        yield db.session
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        log_with_route(logging.ERROR, f"Database error: {str(e)}")
        raise
    finally:
        db.session.remove()