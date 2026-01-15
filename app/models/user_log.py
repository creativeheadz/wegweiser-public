# Filepath: app/models/user_log.py
import time
from sqlalchemy.dialects.postgresql import UUID
from . import db

class UserLog(db.Model):
    __tablename__ = 'userlogs'
    log_id = db.Column(db.Integer, primary_key=True)
    tenantuuid = db.Column(UUID(as_uuid=True), nullable=False)
    created_at = db.Column(db.Integer, nullable=False, default=lambda: int(time.time()))

