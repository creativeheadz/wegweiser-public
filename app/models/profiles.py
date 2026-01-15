# Filepath: app/models/profiles.py
import uuid
from sqlalchemy.dialects.postgresql import UUID
from . import db

class Profiles(db.Model):
    __tablename__ = 'profiles'
    id = db.Column(db.Integer, primary_key=True)
    emailaddress = db.Column(db.String(100), nullable=False)
    account_id = db.Column(UUID(as_uuid=True), db.ForeignKey('accounts.useruuid'), nullable=False)
