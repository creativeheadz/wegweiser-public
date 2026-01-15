# Filepath: app/models/orgmetadata.py
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship
from . import db
import uuid
import time

class OrganizationMetadata(db.Model):
    __tablename__ = 'orgmetadata'
    
    metadatauuid = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    orguuid = db.Column(UUID(as_uuid=True), db.ForeignKey('organisations.orguuid', ondelete="CASCADE"), nullable=False)
    metalogos_type = db.Column(db.String(50), nullable=False)  # e.g., 'site-analysis', 'compliance-status', 'resource-usage'
    metalogos = db.Column(JSONB, nullable=False)
    ai_analysis = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.BigInteger, nullable=False, default=lambda: int(time.time()))
    analyzed_at = db.Column(db.BigInteger, nullable=True)
    processing_status = db.Column(db.String(20), nullable=False, default='pending')
    score = db.Column(db.Integer, nullable=True)
    weight = db.Column(db.Text, nullable=True, default='1.0')

    organisation = relationship('Organisations', backref='metadata', lazy=True)

    def __repr__(self):
        return f'<OrganizationMetadata {self.metadatauuid}: {self.orguuid} - {self.metalogos_type}>'