# Filepath: tools/delete_all_cycles.py
# delete_all_cycles.py

from flask import current_app
from app import db
from app.models import AnalysisCycle
from app.utilities.app_logging_helper import log_with_route
import logging

def delete_all_cycles():
    with current_app.app_context():
        try:
            num_deleted = AnalysisCycle.query.delete()
            db.session.commit()
            log_with_route(logging.INFO, f"Deleted {num_deleted} analysis cycles")
            print(f"Successfully deleted {num_deleted} analysis cycles")
        except Exception as e:
            db.session.rollback()
            log_with_route(logging.ERROR, f"Error deleting analysis cycles: {str(e)}")
            print(f"Error deleting analysis cycles: {str(e)}")

if __name__ == "__main__":
    delete_all_cycles()