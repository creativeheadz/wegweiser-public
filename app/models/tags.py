# Filepath: app/models/tags.py
import uuid
import time
from sqlalchemy.dialects.postgresql import UUID
from . import db

class Tags(db.Model):
    __tablename__ = 'tags'
    taguuid = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenantuuid = db.Column(UUID(as_uuid=True), db.ForeignKey('tenants.tenantuuid'), nullable=False)
    tagvalue = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.Integer, nullable=False, default=lambda: int(time.time()))

    __table_args__ = (
        db.UniqueConstraint('tenantuuid', 'tagvalue', name='_tenantuuid_tagvalue_uc'),
    )


class TagsXDevices(db.Model):
    __tablename__ = 'tagsxdevices'
    taguuid = db.Column(UUID(as_uuid=True), db.ForeignKey('tags.taguuid', ondelete="CASCADE"), primary_key=True, nullable=False)
    deviceuuid = db.Column(UUID(as_uuid=True), db.ForeignKey('devices.deviceuuid', ondelete="CASCADE"), primary_key=True, nullable=False)
    created_at = db.Column(db.Integer, nullable=False, default=lambda: int(time.time()))



class TagsXAccounts(db.Model):
    __tablename__ = 'tagsxaccounts'
    taguuid = db.Column(UUID(as_uuid=True), db.ForeignKey('tags.taguuid'), primary_key=True, nullable=False)
    accountuuid = db.Column(UUID(as_uuid=True), db.ForeignKey('accounts.useruuid'), primary_key=True, nullable=False)
    created_at = db.Column(db.Integer, nullable=False, default=lambda: int(time.time()))


class TagsXOrgs(db.Model):
    __tablename__ = 'tagsxorgs'
    taguuid = db.Column(UUID(as_uuid=True), db.ForeignKey('tags.taguuid'), primary_key=True, nullable=False)
    orguuid = db.Column(UUID(as_uuid=True), db.ForeignKey('organisations.orguuid'), primary_key=True, nullable=False)
    created_at = db.Column(db.Integer, nullable=False, default=lambda: int(time.time()))


class TagsXGroups(db.Model):
    __tablename__ = 'tagsxgroups'
    taguuid = db.Column(UUID(as_uuid=True), db.ForeignKey('tags.taguuid'), primary_key=True, nullable=False)
    groupuuid = db.Column(UUID(as_uuid=True), db.ForeignKey('groups.groupuuid'), primary_key=True, nullable=False)
    created_at = db.Column(db.Integer, nullable=False, default=lambda: int(time.time()))


class TagsXTenants(db.Model):
    __tablename__ = 'tagsxtenants'
    taguuid = db.Column(UUID(as_uuid=True), db.ForeignKey('tags.taguuid'), primary_key=True, nullable=False)
    tenantuuid = db.Column(UUID(as_uuid=True), db.ForeignKey('tenants.tenantuuid'), primary_key=True, nullable=False)
    created_at = db.Column(db.Integer, nullable=False, default=lambda: int(time.time()))

