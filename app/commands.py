# Filepath: app/commands.py
# app/commands.py

from flask import Flask
from flask.cli import with_appcontext
import click
import time
import uuid
from app.models import db, ServerCore, Roles

@click.command(name='populate_servercore')
@with_appcontext
def populate_servercore():
    if not ServerCore.query.first():
        initial_entry = ServerCore(
            serveruuid=str(uuid.uuid4()),
            server_version='1.0.0',
            collector_version='1.0.0',
            serveraddress='127.0.0.1',
            port=8000,
            servername='Inserted by commands.py',
            created_at=int(time.time())
        )
        db.session.add(initial_entry)
        db.session.commit()
        print("Initial ServerCore entry created.")
    else:
        print("ServerCore entry already exists.")

@click.command(name='create_roles')
@with_appcontext
def create_roles():
    roles = ['user', 'master', 'admin']
    for rolename in roles:
        if not Roles.query.filter_by(rolename=rolename).first():
            new_role = Roles(rolename=rolename)
            db.session.add(new_role)
    db.session.commit()
    print("Roles created successfully.")

def init_commands(app: Flask):
    app.cli.add_command(populate_servercore)
    app.cli.add_command(create_roles)
