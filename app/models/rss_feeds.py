# Filepath: app/models/rss_feeds.py
from . import db
import uuid
from sqlalchemy.dialects.postgresql import UUID

class RSSFeed(db.Model):
    __tablename__ = 'rss_feeds'
    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    url = db.Column(db.String(255), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    user_id = db.Column(UUID(as_uuid=True), db.ForeignKey('accounts.useruuid'), nullable=False)