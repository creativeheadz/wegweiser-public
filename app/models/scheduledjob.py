# Filepath: app/models/scheduledjob.py
from . import db

class ScheduledJob(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    job_name = db.Column(db.String(128), nullable=False)
    last_run = db.Column(db.DateTime, nullable=False)
    status = db.Column(db.String(64), nullable=False)
    result = db.Column(db.Text)