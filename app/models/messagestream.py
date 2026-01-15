# Filepath: app/models/messagestream.py
# app/models/messagestream.py
import uuid
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy import and_
from sqlalchemy.orm import foreign  # This is the correct import for foreign()
from sqlalchemy.orm import relationship
from . import db
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID
import time

class MessageStream(db.Model):
    __tablename__ = 'messagestream'

    # Primary key
    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # UUID of the tenant
    tenantuuid = db.Column(UUID(as_uuid=True), nullable=True)

    # Stream JSONB column to store messages from Skald
    stream = db.Column(JSONB, nullable=True)

    def __repr__(self):
        return f'<MessageStream {self.id}: Tenant {self.tenantuuid}>'
