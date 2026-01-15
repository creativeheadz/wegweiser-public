# Filepath: app/models/device_audit_json_test.py
"""
POC Model: Device Audit JSON Test
Stores the entire audit payload in a single JSONB column for performance comparison.
"""
import uuid
import time
from sqlalchemy.dialects.postgresql import UUID, JSONB
from app.models import db


class DeviceAuditJsonTest(db.Model):
    """
    Test table for POC: Store entire audit payload in JSONB column.
    This allows dynamic rendering without schema changes.
    """
    __tablename__ = 'device_audit_json_test'
    
    deviceuuid = db.Column(
        UUID(as_uuid=True), 
        db.ForeignKey('devices.deviceuuid', ondelete="CASCADE"), 
        primary_key=True
    )
    
    # Store the entire audit payload as JSONB
    audit_data = db.Column(JSONB, nullable=False)
    
    # Metadata fields
    last_update = db.Column(db.Integer, nullable=False, default=lambda: int(time.time()))
    last_json_timestamp = db.Column(db.Integer, nullable=True)
    
    # Extracted key fields for quick filtering (optional optimization)
    device_name = db.Column(db.String(255), nullable=True)
    platform = db.Column(db.String(255), nullable=True)
    cpu_name = db.Column(db.String(255), nullable=True)
    total_memory = db.Column(db.BigInteger, nullable=True)
    
    # Indexes for performance
    __table_args__ = (
        db.Index('idx_device_audit_json_test_last_update', 'last_update'),
        db.Index('idx_device_audit_json_test_platform', 'platform'),
    )
    
    def to_dict(self):
        """Convert model to dictionary for JSON serialization"""
        return {
            'deviceuuid': str(self.deviceuuid),
            'audit_data': self.audit_data,
            'last_update': self.last_update,
            'last_json_timestamp': self.last_json_timestamp,
            'device_name': self.device_name,
            'platform': self.platform,
            'cpu_name': self.cpu_name,
            'total_memory': self.total_memory
        }
    
    @property
    def info(self):
        """Property for template access"""
        return {
            'deviceuuid': str(self.deviceuuid),
            'last_update': self.last_update,
            'device_name': self.device_name,
            'platform': self.platform,
            'audit_data': self.audit_data
        }

