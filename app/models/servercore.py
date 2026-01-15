# Filepath: app/models/servercore.py
import uuid
import time
from sqlalchemy.dialects.postgresql import UUID
from . import db

class ServerCore(db.Model):
	__tablename__ = 'servercore'
	serveruuid          = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False)
	server_version      = db.Column(db.String(50), nullable=True)
	collector_version   = db.Column(db.String(50), nullable=True)
	serveraddress       = db.Column(db.String(255), nullable=True)
	port                = db.Column(db.Integer, nullable=True)
	servername          = db.Column(db.String(100), nullable=True)
	created_at          = db.Column(db.BigInteger, nullable=True, default=lambda: int(time.time()))
	collector_hash_py   = db.Column(db.String(255), nullable=True)
	collector_hash_win  = db.Column(db.String(255), nullable=True)
	server_public_key   = db.Column(db.String(1024), nullable=True)
	agent_version       = db.Column(db.String(50), nullable=True)
	agent_hash_py       = db.Column(db.String(255), nullable=True)
	agent_hash_win      = db.Column(db.String(255), nullable=True)
	# Persistent NATS Agent versioning (v3.0.0+)
	persistent_agent_version = db.Column(db.String(50), nullable=True)
	persistent_agent_hash_py = db.Column(db.String(255), nullable=True)
	persistent_agent_hash_linux = db.Column(db.String(255), nullable=True)
	persistent_agent_hash_macos = db.Column(db.String(255), nullable=True)

def insert_initial_values():
    initial_data = ServerCore(
        serveruuid			= uuid.uuid4(),
        server_version		= '1.0.0',
        collector_version	= '1',
        serveraddress		= '127.0.0.1',
        port				= 8000,
        servername			=' Default Server',
        created_at			= int(time.time()),
		agent_version		= '0'
    )
    db.session.add(initial_data)
    db.session.commit()

def create_table_and_insert_initial_values():
    db.create_all()
    if not db.session.query(ServerCore).count():
        insert_initial_values()
