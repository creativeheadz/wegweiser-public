# Filepath: app/models/userxorganisation.py
from . import db
from .accounts import Accounts
from .organisations import Organisations
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

class UserXOrganisation(db.Model):
    __tablename__ = 'userxorganisations'
    id = db.Column(db.Integer, primary_key=True)
    useruuid = db.Column(UUID(as_uuid=True), db.ForeignKey('accounts.useruuid'), nullable=False)
    orguuid = db.Column(UUID(as_uuid=True), db.ForeignKey('organisations.orguuid'), nullable=False)

    user = relationship('Accounts', back_populates='organisations', overlaps="org_associations,user_associations")
    organisation = relationship('Organisations', back_populates='users', overlaps="org_associations,user_associations")

    def __repr__(self):
        return f'<UserXOrganisation {self.useruuid} - {self.orguuid}>'