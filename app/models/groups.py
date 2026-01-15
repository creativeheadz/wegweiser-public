# Filepath: app/models/groups.py
import uuid
import time
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship, foreign  # Correct import for foreign
from sqlalchemy import and_, UniqueConstraint
from . import db

class Groups(db.Model):
    __tablename__ = 'groups'
    groupuuid = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    groupname = db.Column(db.String(255), nullable=True)
    orguuid = db.Column(UUID(as_uuid=True), db.ForeignKey('organisations.orguuid', ondelete="CASCADE"), nullable=False)
    tenantuuid = db.Column(UUID(as_uuid=True), db.ForeignKey('tenants.tenantuuid', ondelete="CASCADE"), nullable=False)
    created_at = db.Column(db.BigInteger, nullable=False, default=lambda: int(time.time()))
    health_score = db.Column(db.Float)
    location_type = db.Column(db.String(50), nullable=True)  # office, datacenter, warehouse
    profile_data = db.Column(JSONB, nullable=True)
    operating_hours = db.Column(JSONB, nullable=True)
    physical_security = db.Column(JSONB, nullable=True)
    network_topology = db.Column(JSONB, nullable=True)

    def update_profile(self, data):
        if self.profile_data is None:
            self.profile_data = {}
        self.profile_data.update(data)
        db.session.commit()

    # Relationship for messages with explicit primaryjoin
    messages = relationship('Messages', 
        primaryjoin="and_(Messages.entityuuid == foreign(Groups.groupuuid), Messages.entity_type == 'group')", 
        back_populates='group')

    organisation = relationship("Organisations", back_populates="groups")
    devices = relationship("Devices", backref='group', lazy=True)

    __table_args__ = (
        UniqueConstraint('groupname', 'orguuid', name='_groupname_orguuid_uc'),
    )

    def get_uuid(self):
        return self.groupuuid
