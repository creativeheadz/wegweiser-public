# Filepath: app/models/accounts.py
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.ext.mutable import MutableDict
from . import db
import uuid
import time

class Accounts(db.Model):
    __tablename__ = 'accounts'
    useruuid = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    firstname = db.Column(db.String(50), nullable=False)
    lastname = db.Column(db.String(50), nullable=False)
    companyname = db.Column(db.String(100), nullable=False)
    companyemail = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(100), nullable=False)
    tenantuuid = db.Column(UUID(as_uuid=True), db.ForeignKey('tenants.tenantuuid'), nullable=True)
    role_id = db.Column(UUID(as_uuid=True), db.ForeignKey('roles.roleuuid'), nullable=False)
    position = db.Column(db.String(100), nullable=True)  # New field for job position
    created_at = db.Column(db.BigInteger, nullable=False, default=lambda: int(time.time()))
    theme = db.Column(db.String(50), nullable=True, default='light-theme') 
    date_of_birth = db.Column(db.Date, nullable=True)
    country = db.Column(db.String(50), nullable=True)
    city = db.Column(db.String(50), nullable=True)
    state = db.Column(db.String(50), nullable=True)
    zip = db.Column(db.String(20), nullable=True)
    address = db.Column(db.Text, nullable=True)
    phone = db.Column(db.String(20), nullable=True)
    profile_picture = db.Column(db.String(200), nullable=True)
    email_verified = db.Column(db.Boolean, default=False, nullable=False)
    
    # IP tracking for security auditing
    registration_ip = db.Column(db.String(45), nullable=True, index=True)  # Supports IPv4 and IPv6
    last_login_ip = db.Column(db.String(45), nullable=True, index=True)
    last_login_at = db.Column(db.BigInteger, nullable=True)

    # Per-user UI preferences (JSONB). Example:
    # {"devices_layout": "card"}
    user_preferences = db.Column(MutableDict.as_mutable(JSONB), nullable=True, default=dict)

    role = relationship('Roles', back_populates='accounts')
    organisations = relationship('UserXOrganisation', back_populates='user', overlaps="org_associations")
    org_associations = relationship('Organisations', secondary='userxorganisations', back_populates='user_associations', overlaps="organisations")



    def __repr__(self):
        return f'<Account {self.firstname} {self.lastname}>'
