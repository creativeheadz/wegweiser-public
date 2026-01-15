# Filepath: app/models/messages.py
import uuid
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy import and_
from sqlalchemy.orm import foreign  # This is the correct import for foreign()
from sqlalchemy.orm import relationship
from . import db
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID
import time  # Add time to handle default timestamp

class Messages(db.Model):
    __tablename__ = 'messages'
    messageuuid = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    conversationuuid = db.Column(UUID(as_uuid=True), db.ForeignKey('conversations.conversationuuid'), nullable=False)
    useruuid = db.Column(UUID(as_uuid=True), nullable=True)
    tenantuuid = db.Column(UUID(as_uuid=True), db.ForeignKey('tenants.tenantuuid', ondelete="CASCADE"), nullable=False)
    entityuuid = db.Column(UUID(as_uuid=True), nullable=False)
    entity_type = db.Column(db.String(50), nullable=False)  # 'device', 'group', 'organisation', 'tenant'
    title = db.Column(db.String(120), nullable=False)
    content = db.Column(db.Text, nullable=False)
    is_read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.BigInteger, nullable=False, default=lambda: int(time.time()))
    message_type = db.Column(db.String(20), nullable=False, default='chat')
    stream = db.Column(JSONB, nullable=True)  # New jsonb column for storing stream data
    sequence_id = db.Column(db.BigInteger, nullable=False, unique=True, server_default=db.text("nextval('messages_sequence_id_seq')"))  # Auto-incrementing sequence for reliable ordering


    # Relationships based on the entity_type
    tenant = relationship('Tenants', back_populates='messages')
    conversation = relationship('Conversations', back_populates='messages')

    # Define relationships to each entity type manually using foreign() for explicit joins
    device_related_messages = relationship('Devices',
        primaryjoin="and_(Messages.entityuuid == foreign(Devices.deviceuuid), Messages.entity_type == 'device')",
        back_populates="messages")  # Changed back_populates to reflect updated name in Devices model

    group = relationship('Groups',
        primaryjoin="and_(Messages.entityuuid == foreign(Groups.groupuuid), Messages.entity_type == 'group')",
        back_populates="messages")

    organisation = relationship('Organisations',
        primaryjoin="and_(Messages.entityuuid == foreign(Organisations.orguuid), Messages.entity_type == 'organisation')",
        back_populates="messages")

    tenant_ref = relationship('Tenants',
        primaryjoin="and_(Messages.entityuuid == foreign(Tenants.tenantuuid), Messages.entity_type == 'tenant')",
        back_populates="messages")

    def __repr__(self):
        return f'<Message {self.messageuuid}: {self.title}>'
