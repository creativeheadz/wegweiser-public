# Filepath: app/models/wegcoin_transaction.py
# app/models/wegcoin_transaction.py

from . import db
import uuid
import time
from sqlalchemy.dialects.postgresql import UUID

class WegcoinTransaction(db.Model):
    __tablename__ = 'wegcoin_transactions'

    transaction_id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenantuuid = db.Column(UUID(as_uuid=True), db.ForeignKey('tenants.tenantuuid'), nullable=False)
    amount = db.Column(db.Integer, nullable=False)  # Positive for additions, negative for deductions
    transaction_type = db.Column(db.String(50), nullable=False)  # e.g., 'purchase', 'usage', 'expiry', 'adjustment'
    description = db.Column(db.String(255))
    created_at = db.Column(db.BigInteger, nullable=False, default=lambda: int(time.time()))

    # Relationship to Tenant
    tenant = db.relationship('Tenants', back_populates='wegcoin_transactions')

    def __repr__(self):
        return f'<WegcoinTransaction {self.transaction_id}: {self.amount} for {self.tenantuuid}>'