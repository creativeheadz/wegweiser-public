#!/usr/bin/env python3
"""
Migration script to set up the guided tour system.
Run this script to create the database tables and populate initial tour data.
"""

import sys
import os

# Add the app directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

from app import create_app
from app.models import db
from app.utilities.migrate_quickstart_tour import run_migration

def main():
    """Main migration function."""
    print("Starting guided tour system migration...")
    
    # Create Flask app
    app = create_app()
    
    with app.app_context():
        try:
            # Create tables if they don't exist
            print("Creating database tables...")
            db.create_all()
            
            # Run the tour migration
            print("Migrating tour data...")
            success = run_migration()
            
            if success:
                print("✅ Migration completed successfully!")
                print("\nNext steps:")
                print("1. Start your Flask application")
                print("2. Log in as an admin user")
                print("3. Visit /admin/tours to manage guided tours")
                print("4. Visit /quickstart to test the new tour system")
            else:
                print("❌ Migration failed. Check the logs for details.")
                return 1
                
        except Exception as e:
            print(f"❌ Migration failed with error: {str(e)}")
            return 1
    
    return 0

if __name__ == '__main__':
    exit(main())
