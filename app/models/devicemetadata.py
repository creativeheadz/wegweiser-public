# Filepath: app/models/devicemetadata.py
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy import Text
import uuid
import time
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.schema import UniqueConstraint
from sqlalchemy.orm import relationship
from . import db


class DeviceMetadata(db.Model):
    __tablename__ = 'devicemetadata'
    
    metadatauuid = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    deviceuuid = db.Column(UUID(as_uuid=True), db.ForeignKey('devices.deviceuuid', ondelete="CASCADE"), nullable=False)
    metalogos_type = db.Column(db.String(50), nullable=False)  # e.g., 'msinfo32', 'event_logs', 'windows_updates'
    metalogos = db.Column(JSONB, nullable=False)
    ai_analysis = db.Column(Text, nullable=True)
    created_at = db.Column(db.BigInteger, nullable=False, default=lambda: int(time.time()))
    analyzed_at = db.Column(db.BigInteger, nullable=True)
    processing_status = db.Column(db.String(20), nullable=False, default='pending')
    # New fields for health score calculation (AVT - 28072024)
    score = db.Column(db.Integer, nullable=True)
    weight = db.Column(Text, nullable=True, default = '1.0')

    device = relationship('Devices', backref='metadata', lazy=True)

    def __repr__(self):
        return f'<DeviceMetadata {self.metadatauuid}: {self.deviceuuid} - {self.metalogos_type}>'
