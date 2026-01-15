# Filepath: app/models/agent_update.py
from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from datetime import datetime
from . import db


class AgentUpdateHistory(db.Model):
    """Track history of agent updates across all devices"""
    __tablename__ = 'agent_update_history'

    id = Column(Integer, primary_key=True)
    deviceuuid = Column(UUID(as_uuid=True), ForeignKey('devices.deviceuuid'), nullable=False, index=True)
    update_version = Column(String(20), nullable=False)
    previous_version = Column(String(20), nullable=True)
    apply_mode = Column(String(20), nullable=False)  # 'immediate' or 'scheduled_reboot'
    target_component = Column(String(20), nullable=False, default='both')  # 'nats_agent', 'agent', or 'both'
    status = Column(String(20), nullable=False, default='pending')  # 'pending', 'staged', 'success', 'failed', 'rolled_back'
    initiated_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    completed_at = Column(DateTime, nullable=True)
    error_message = Column(Text, nullable=True)

    def __repr__(self):
        return f"<AgentUpdateHistory(id={self.id}, device={self.deviceuuid}, version={self.update_version}, status='{self.status}')>"

    def to_dict(self):
        """Convert model to dictionary"""
        return {
            'id': self.id,
            'deviceuuid': self.deviceuuid,
            'update_version': self.update_version,
            'previous_version': self.previous_version,
            'apply_mode': self.apply_mode,
            'target_component': self.target_component,
            'status': self.status,
            'initiated_at': self.initiated_at.isoformat() if self.initiated_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'error_message': self.error_message
        }
