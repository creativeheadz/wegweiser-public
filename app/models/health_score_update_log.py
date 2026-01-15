# Filepath: app/models/health_score_update_log.py
from sqlalchemy import Column, Integer, DateTime, Text
from datetime import datetime
from . import db

class HealthScoreUpdateLog(db.Model):
    __tablename__ = 'health_score_update_log'

    id = Column(Integer, primary_key=True)
    update_time = Column(DateTime, default=datetime.utcnow)
    description = Column(Text, nullable=True)

    def __repr__(self):
        description = self.description if self.description is not None else ""
        return f"<HealthScoreUpdateLog(id={self.id}, update_time={self.update_time}, description='{description}')>"
