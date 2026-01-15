# Filepath: app/models/roles.py
import uuid
import time
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from . import db

class Roles(db.Model):
    __tablename__ = 'roles'
    roleuuid = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    rolename = db.Column(db.String(50), unique=True, nullable=False)
    created_at = db.Column(db.BigInteger, nullable=False, default=lambda: int(time.time()))

    accounts = relationship('Accounts', back_populates='role')

def insert_initial_roles():
    roles = ['user', 'master', 'admin']
    for rolename in roles:
        if not Roles.query.filter_by(rolename=rolename).first():
            new_role = Roles(
                roleuuid=uuid.uuid4(),
                rolename=rolename,
                created_at=int(time.time())
            )
            db.session.add(new_role)
    db.session.commit()

def create_roles_table_and_insert_initial_values():
    db.create_all()
    if not db.session.query(Roles).count():
        insert_initial_roles()

class AccountsXRoles(db.Model):
    __tablename__ = 'accountsxroles'
    roleuuid = db.Column(UUID(as_uuid=True), db.ForeignKey('roles.roleuuid'), primary_key=True, nullable=False)
    accountuuid = db.Column(UUID(as_uuid=True), db.ForeignKey('accounts.useruuid'), primary_key=True, nullable=False)
    created_at = db.Column(db.Integer, nullable=False, default=lambda: int(time.time()))
