# Filepath: app/tasks/__init__.py
from app.tasks.base.scheduler import AnalysisScheduler, process_pending_analyses
from ..extensions import celery

# Export what other modules need
__all__ = ['AnalysisScheduler', 'process_pending_analyses']

# Register the execute task
celery.task(name="app.tasks.process_pending_analyses")(process_pending_analyses)