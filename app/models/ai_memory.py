# Filepath: app/models/ai_memory.py
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from . import db
import time
import uuid

class AIMemory(db.Model):
    __tablename__ = 'ai_memories'
    memoryuuid = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    entity_uuid = db.Column(UUID(as_uuid=True), nullable=False)
    entity_type = db.Column(db.String(20), nullable=False)  # 'device', 'group', 'organisation', or 'tenant'
    tenantuuid = db.Column(UUID(as_uuid=True), db.ForeignKey('tenants.tenantuuid'), nullable=False)
    content = db.Column(db.Text)
    created_at = db.Column(db.BigInteger, nullable=False, default=lambda: int(time.time()))
    last_accessed = db.Column(db.BigInteger)
    importance_score = db.Column(db.Float)

    tenant = relationship('Tenants', back_populates='ai_memories')

    def __repr__(self):
        return f'<AIMemory {self.memoryuuid}: {self.entity_type} {self.entity_uuid}>'

# Utility functions for datetime conversion
from datetime import datetime

def unix_to_datetime(unix_time):
    return datetime.utcfromtimestamp(unix_time)

def datetime_to_unix(dt):
    return int(dt.timestamp())