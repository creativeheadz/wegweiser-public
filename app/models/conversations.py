# Filepath: app/models/conversations.py
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from . import db
import time
import uuid

NO_DEVICE_UUID = '00000000-0000-0000-0000-000000000000'  # Nil UUID for non-device conversations

class Conversations(db.Model):
    __tablename__ = 'conversations'
    conversationuuid = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenantuuid = db.Column(UUID(as_uuid=True), db.ForeignKey('tenants.tenantuuid', ondelete="CASCADE"), nullable=False)
    deviceuuid = db.Column(UUID(as_uuid=True), db.ForeignKey('devices.deviceuuid', ondelete="CASCADE"), nullable=True)  # Make this nullable
    entityuuid = db.Column(UUID(as_uuid=True), nullable=False)
    entity_type = db.Column(db.String(20), nullable=False)  # 'device', 'group', 'organisation', or 'tenant'
    started_at = db.Column(db.BigInteger, nullable=False, default=lambda: int(time.time()))
    last_updated = db.Column(db.BigInteger, nullable=False, default=lambda: int(time.time()), onupdate=lambda: int(time.time()))

    tenant = relationship('Tenants', back_populates='conversations')
    messages = relationship('Messages', back_populates='conversation', order_by='Messages.created_at', cascade="all, delete-orphan")
    device = relationship('Devices', back_populates='conversations')  # Back reference to Devices

    @property
    def is_device_conversation(self):
        return str(self.deviceuuid) != NO_DEVICE_UUID

    def __repr__(self):
        return f'<Conversation {self.conversationuuid}: {self.entity_type} {self.entityuuid}>'

    @classmethod
    def create_non_device_conversation(cls, tenantuuid, entityuuid, entity_type):
        return cls(
            tenantuuid=tenantuuid,
            deviceuuid=None,
            entityuuid=entityuuid,
            entity_type=entity_type
        )

    @classmethod
    def create_device_conversation(cls, tenantuuid, deviceuuid):
        """Create a new conversation for a device"""
        return cls(
            tenantuuid=tenantuuid,
            deviceuuid=deviceuuid,
            entityuuid=deviceuuid,
            entity_type='device'
        )

    @classmethod
    def get_or_create_conversation(cls, tenantuuid, entityuuid, entity_type):
        """Get existing conversation or create new one"""
        conversation = cls.query.filter_by(
            tenantuuid=tenantuuid,
            entityuuid=entityuuid,
            entity_type=entity_type
        ).order_by(cls.last_updated.desc()).first()

        if not conversation:
            if entity_type == 'device':
                conversation = cls.create_device_conversation(tenantuuid, entityuuid)
            else:
                conversation = cls.create_non_device_conversation(tenantuuid, entityuuid, entity_type)
            db.session.add(conversation)
            db.session.commit()

        return conversation

    def get_recent_messages(self, limit=10):
        """Get recent messages for this conversation"""
        # Use sequence_id for guaranteed chronological order
        all_messages = Messages.query.filter_by(
            conversationuuid=self.conversationuuid,
            message_type='chat'
        ).order_by(Messages.sequence_id.asc()).all()

        # Return the most recent messages
        return all_messages[-limit:] if len(all_messages) > limit else all_messages

    def get_last_exchange(self):
        """Get the last user-AI message exchange"""
        recent = self.get_recent_messages(2)
        if len(recent) >= 2:
            return {
                'user_message': recent[1].content if recent[1].useruuid else None,
                'ai_message': recent[0].content if not recent[0].useruuid else None
            }
        return None