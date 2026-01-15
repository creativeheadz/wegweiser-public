import os
import shutil
import sys
from pathlib import Path

def clear_flask_sessions(base_path=None, force=False):
    """Delete all files within the flask_session directory."""
    # Find flask_session directory
    if base_path:
        flask_session_dir = Path(base_path) / 'flask_session'
    else:
        # Try to find it in the current directory or its parent
        current_dir = Path.cwd()
        flask_session_dir = current_dir / 'flask_session'
        
        if not flask_session_dir.exists():
            flask_session_dir = current_dir.parent / 'flask_session'
    
    # Check if directory exists
    if not flask_session_dir.exists() or not flask_session_dir.is_dir():
        print(f"Error: Flask session directory not found at {flask_session_dir}")
        return False
    
    # Get list of files to delete
    files = [f for f in flask_session_dir.iterdir() if f.is_file()]
    
    if not files:
        print(f"No files found in {flask_session_dir}")
        return True
    
    # Show files to be deleted
    print(f"Found {len(files)} files in {flask_session_dir}")
    for f in files:
        print(f"  - {f.name}")
    
    # Confirm deletion
    if not force:
        confirm = input("\nDelete these files? (y/n): ").lower().strip()
        if confirm != 'y':
            print("Operation cancelled.")
            return False
    
    # Delete files
    deleted_count = 0
    for f in files:
        try:
            f.unlink()
            deleted_count += 1
        except Exception as e:
            print(f"Error deleting {f.name}: {e}")
    
    print(f"Successfully deleted {deleted_count} of {len(files)} files.")
    return True

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Delete all files within the flask_session directory.')
    parser.add_argument('--path', help='Base path containing the flask_session directory')
    parser.add_argument('--force', '-f', action='store_true', help='Delete without confirmation')
    
    args = parser.parse_args()
    
    clear_flask_sessions(args.path, args.force)
