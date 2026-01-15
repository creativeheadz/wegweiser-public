# Filepath: app/models/mfa.py
import time
from sqlalchemy.dialects.postgresql import UUID
from . import db

class MFA(db.Model):
    __tablename__ = 'mfa'
    id = db.Column(db.Integer, primary_key=True)
    useruuid = db.Column(UUID(as_uuid=True), db.ForeignKey('accounts.useruuid'), nullable=False)
    secret = db.Column(db.String(100), nullable=False)
    created_at = db.Column(db.BigInteger, nullable=False, default=lambda: int(time.time()))
