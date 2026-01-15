# Filepath: app/models/health_score_history.py

from sqlalchemy import Column, Integer, Float, String, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.models import db
import uuid
from datetime import datetime

class HealthScoreHistory(db.Model):
    __tablename__ = 'health_score_history'

    id = Column(Integer, primary_key=True)
    entity_type = Column(String(20), nullable=False)
    entity_uuid = Column(UUID(as_uuid=True), nullable=False)
    health_score = Column(Float)
    timestamp = Column(DateTime, default=datetime.utcnow)

    def __init__(self, entity_type, entity_uuid, health_score, timestamp=None):
        self.entity_type = entity_type
        self.entity_uuid = entity_uuid
        self.health_score = health_score
        if timestamp:
            self.timestamp = timestamp

    def __repr__(self):
        return f"<HealthScoreHistory(id={self.id}, entity_type='{self.entity_type}', entity_uuid='{self.entity_uuid}', health_score={self.health_score}, timestamp='{self.timestamp}')>"

    @classmethod
    def get_history(cls, entity_type, entity_uuid, start_date=None, end_date=None):
        query = cls.query.filter_by(entity_type=entity_type, entity_uuid=entity_uuid)
        
        if start_date:
            query = query.filter(cls.timestamp >= start_date)
        if end_date:
            query = query.filter(cls.timestamp <= end_date)
        
        return query.order_by(cls.timestamp.asc()).all()

# Add indexes for better query performance
db.Index('idx_health_score_history_entity_uuid', HealthScoreHistory.entity_uuid)
db.Index('idx_health_score_history_timestamp', HealthScoreHistory.timestamp)