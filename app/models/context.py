# Filepath: app/models/context.py
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from . import db
import time
import uuid

class Context(db.Model):
    __tablename__ = 'contexts'
    contextuuid = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_uuid = db.Column(UUID(as_uuid=True), db.ForeignKey('tenants.tenantuuid'), nullable=False)
    context_type = db.Column(db.String(50), nullable=False)
    context_data = db.Column(JSONB)
    created_at = db.Column(db.BigInteger, nullable=False, default=lambda: int(time.time()))
    updated_at = db.Column(db.BigInteger, nullable=False, default=lambda: int(time.time()), onupdate=lambda: int(time.time()))

    tenant = relationship('Tenants', back_populates='contexts')
    

# Utility functions for datetime conversion
from datetime import datetime

def unix_to_datetime(unix_time):
    return datetime.utcfromtimestamp(unix_time)

def datetime_to_unix(dt):
    return int(dt.timestamp())