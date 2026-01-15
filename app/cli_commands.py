# Filepath: app/cli_commands.py
"""
Flask CLI commands for the application.
"""

import click
from flask.cli import with_appcontext
from app.models import db
from app.utilities.migrate_quickstart_tour import run_migration


@click.command()
@with_appcontext
def init_tours():
    """Initialize the guided tour system with database tables and sample data."""
    click.echo('Initializing guided tour system...')
    
    try:
        # Create tables if they don't exist
        click.echo('Creating database tables...')
        db.create_all()
        
        # Run the tour migration
        click.echo('Migrating tour data...')
        success = run_migration()
        
        if success:
            click.echo('✅ Tour system initialized successfully!')
            click.echo('\nNext steps:')
            click.echo('1. Visit /admin/tours to manage guided tours')
            click.echo('2. Visit /quickstart to test the new tour system')
        else:
            click.echo('❌ Migration failed. Check the logs for details.')
            
    except Exception as e:
        click.echo(f'❌ Migration failed with error: {str(e)}')
        raise


def init_app(app):
    """Register CLI commands with the Flask app."""
    app.cli.add_command(init_tours)
