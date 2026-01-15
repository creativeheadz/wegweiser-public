#!/usr/bin/env python3
"""
Simple script to run the chat message ordering migration.
This will add sequence_id column and purge existing chat data.
"""

import subprocess
import sys
import os

def main():
    """Run the migration script"""
    
    print("🚀 Running Chat Message Ordering Migration")
    print("=" * 50)
    print()
    print("This migration will:")
    print("✅ Add sequence_id column for reliable message ordering")
    print("🗑️  Purge existing chat messages (as requested)")
    print("📊 Create database index for performance")
    print()
    
    # Confirm with user
    response = input("Do you want to proceed? (y/N): ").strip().lower()
    if response not in ['y', 'yes']:
        print("Migration cancelled.")
        return
    
    print("\nRunning migration...")
    
    try:
        # Run the migration script
        result = subprocess.run([
            sys.executable, 
            "migrations/add_sequence_id_and_purge_chat.py"
        ], capture_output=True, text=True, cwd=os.getcwd())
        
        # Print output
        if result.stdout:
            print(result.stdout)
        
        if result.stderr:
            print("STDERR:", result.stderr)
        
        if result.returncode == 0:
            print("\n🎉 Migration completed successfully!")
            print("\nNext steps:")
            print("1. Restart your Flask application")
            print("2. Test the chat interface")
            print("3. Verify messages appear in correct order")
        else:
            print(f"\n❌ Migration failed with return code {result.returncode}")
            return False
            
    except Exception as e:
        print(f"\n❌ Error running migration: {e}")
        return False
    
    return True

if __name__ == "__main__":
    success = main()
    if not success:
        sys.exit(1)
