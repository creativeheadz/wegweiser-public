# Filepath: app/models/organisations.py
import uuid
import time
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from sqlalchemy import and_
from sqlalchemy.orm import foreign
from . import db

class Organisations(db.Model):
    __tablename__ = 'organisations'
    orguuid = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    orgname = db.Column(db.String(100), nullable=False)
    tenantuuid = db.Column(UUID(as_uuid=True), db.ForeignKey('tenants.tenantuuid', ondelete="CASCADE"), nullable=True)
    created_at = db.Column(db.BigInteger, nullable=False, default=lambda: int(time.time()))
    health_score = db.Column(db.Float)  
    industry = db.Column(db.String(100), nullable=True)
    company_size = db.Column(db.String(50), nullable=True)
    website_url = db.Column(db.String(255), nullable=True)
    profile_data = db.Column(JSONB, nullable=True)  # Structured customer info
    business_hours = db.Column(JSONB, nullable=True)
    compliance_requirements = db.Column(JSONB, nullable=True)
    critical_systems = db.Column(JSONB, nullable=True)
    
    def update_profile(self, data):
        if self.profile_data is None:
            self.profile_data = {}
        self.profile_data.update(data)
        db.session.commit()

    def get_profile_data(self, key, default=None):
        return self.profile_data.get(key, default) if self.profile_data else default
    
    # Relationship for messages with explicit primaryjoin
    messages = relationship('Messages', 
        primaryjoin="and_(Messages.entityuuid == foreign(Organisations.orguuid), Messages.entity_type == 'organisation')", 
        back_populates='organisation')

    groups = relationship("Groups", back_populates="organisation", cascade="all, delete-orphan", passive_deletes=True)
    users = relationship('UserXOrganisation', back_populates='organisation', overlaps="org_associations,user_associations")
    user_associations = relationship('Accounts', secondary='userxorganisations', back_populates='org_associations', overlaps="users,organisations")

    def get_uuid(self):
        return self.orguuid


    def __repr__(self):
        return f'<Organisation {self.orgname}>'
