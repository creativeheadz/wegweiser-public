# Filepath: app/models/groupmetadata.py
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy import Text
import uuid
import time
from sqlalchemy.orm import relationship
from . import db

class GroupMetadata(db.Model):
    __tablename__ = 'groupmetadata'
    
    metadatauuid = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    groupuuid = db.Column(UUID(as_uuid=True), db.ForeignKey('groups.groupuuid', ondelete="CASCADE"), nullable=False)
    metalogos_type = db.Column(db.String(50), nullable=False)  # e.g., 'group-device-patterns', 'group-health-analysis', 'group-performance-metrics'
    metalogos = db.Column(JSONB, nullable=False)
    ai_analysis = db.Column(Text, nullable=True)
    created_at = db.Column(db.BigInteger, nullable=False, default=lambda: int(time.time()))
    analyzed_at = db.Column(db.BigInteger, nullable=True)
    processing_status = db.Column(db.String(20), nullable=False, default='pending')
    score = db.Column(db.Integer, nullable=True)
    weight = db.Column(Text, nullable=True, default='1.0')
    device_count = db.Column(db.Integer, nullable=True)  # Number of devices included in this analysis
    source_devices = db.Column(JSONB, nullable=True)  # List of device UUIDs that contributed to this analysis

    group = relationship('Groups', backref='metadata', lazy=True)

    def __repr__(self):
        return f'<GroupMetadata {self.metadatauuid}: {self.groupuuid} - {self.metalogos_type}>'