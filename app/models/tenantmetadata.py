# Filepath: app/models/tenantmetadata.py
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy import Text
import uuid
import time
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.schema import UniqueConstraint
from sqlalchemy.orm import relationship
from . import db

class TenantMetadata(db.Model):
    __tablename__ = 'tenantmetadata'
    
    metadatauuid = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenantuuid = db.Column(UUID(as_uuid=True), db.ForeignKey('tenants.tenantuuid', ondelete="CASCADE"), nullable=False)
    metalogos_type = db.Column(db.String(50), nullable=False)  # e.g., 'ai_recommendations', 'ai_suggestions', 'health_analysis'
    metalogos = db.Column(JSONB, nullable=False)
    ai_analysis = db.Column(Text, nullable=True)
    created_at = db.Column(db.BigInteger, nullable=False, default=lambda: int(time.time()))
    analyzed_at = db.Column(db.BigInteger, nullable=True)
    processing_status = db.Column(db.String(20), nullable=False, default='pending')
    score = db.Column(db.Integer, nullable=True)
    weight = db.Column(Text, nullable=True, default='1.0')

    tenant = relationship('Tenants', backref='metadata', lazy=True)

    def __repr__(self):
        return f'<TenantMetadata {self.metadatauuid}: {self.tenantuuid} - {self.metalogos_type}>'