# Filepath: app/models/invite_codes.py
from . import db
import uuid
from datetime import datetime, timedelta

class InviteCodes(db.Model):
    __tablename__ = 'invite_codes'
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(32), unique=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    expires_at = db.Column(db.DateTime)
    is_used = db.Column(db.Boolean, default=False)
    used_by = db.Column(db.String(36))  # UUID of the user who used the code
    used_at = db.Column(db.DateTime)

    def __init__(self, code=None, expires_in_days=30):
        self.code = code or str(uuid.uuid4())
        self.expires_at = datetime.utcnow() + timedelta(days=expires_in_days)

    def use(self, user_uuid):
        if self.is_used:
            return False
        self.is_used = True
        self.used_by = str(user_uuid)
        self.used_at = datetime.utcnow()
        return True

    @staticmethod
    def is_valid(code):
        invite = InviteCodes.query.filter_by(code=code, is_used=False).first()
        if not invite:
            return False
        if invite.expires_at and invite.expires_at < datetime.utcnow():
            return False
        return True