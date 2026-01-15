# Filepath: app/models/email_verification.py
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from . import db
import uuid
import time
from datetime import datetime, timedelta

class EmailVerification(db.Model):
    __tablename__ = 'email_verifications'
    
    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_uuid = db.Column(UUID(as_uuid=True), db.ForeignKey('accounts.useruuid'), nullable=False)
    token = db.Column(db.String(255), unique=True, nullable=False)
    email = db.Column(db.String(100), nullable=False)
    created_at = db.Column(db.BigInteger, nullable=False, default=lambda: int(time.time()))
    expires_at = db.Column(db.BigInteger, nullable=False)
    verified_at = db.Column(db.BigInteger, nullable=True)
    is_used = db.Column(db.Boolean, default=False, nullable=False)
    
    # Relationship to user
    user = relationship('Accounts', backref='email_verifications')
    
    def __init__(self, user_uuid, token, email, expires_in_hours=24):
        self.user_uuid = user_uuid
        self.token = token
        self.email = email
        self.created_at = int(time.time())
        self.expires_at = int(time.time()) + (expires_in_hours * 3600)  # Convert hours to seconds
        
    def is_expired(self):
        """Check if the verification token has expired"""
        return int(time.time()) > self.expires_at
        
    def is_valid(self):
        """Check if the token is valid (not expired and not used)"""
        return not self.is_expired() and not self.is_used
        
    def mark_as_used(self):
        """Mark the token as used and set verification time"""
        self.is_used = True
        self.verified_at = int(time.time())
        
    def __repr__(self):
        return f'<EmailVerification {self.email} - {self.token[:8]}...>'
