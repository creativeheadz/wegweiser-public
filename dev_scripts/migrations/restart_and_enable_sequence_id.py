#!/usr/bin/env python3
"""
Script to restart the application and enable sequence_id functionality.
This should be run after the Flask application has been restarted.
"""

import os
import sys

def update_model_file():
    """Update the Messages model to include sequence_id"""
    
    model_file = "app/models/messages.py"
    
    # Read the current file
    with open(model_file, 'r') as f:
        content = f.read()
    
    # Replace the commented line with the active sequence_id column
    old_line = "    # sequence_id = db.Column(db.BigInteger, nullable=False, autoincrement=True, unique=True)  # Auto-incrementing sequence for reliable ordering - temporarily commented out for restart"
    new_line = "    sequence_id = db.Column(db.BigInteger, nullable=False, autoincrement=True, unique=True)  # Auto-incrementing sequence for reliable ordering"
    
    if old_line in content:
        content = content.replace(old_line, new_line)
        
        # Write back to file
        with open(model_file, 'w') as f:
            f.write(content)
        
        print("✅ Updated Messages model to include sequence_id")
        return True
    else:
        print("❌ Could not find commented sequence_id line in model file")
        return False

def update_chat_routes():
    """Update chat routes to use sequence_id ordering"""
    
    routes_file = "app/routes/ai/chat_routes.py"
    
    # Read the current file
    with open(routes_file, 'r') as f:
        content = f.read()
    
    # Update the enhanced chat history
    old_text1 = "        # Get the most recent 15 messages, ordered chronologically (temporarily using created_at until restart)\n        # This ensures proper conversation flow in the UI\n        messages = Messages.query.filter_by(\n            entityuuid=entity_uuid,\n            entity_type=entity_type,\n            message_type='chat'\n        ).order_by(\n            Messages.created_at.asc()\n        ).all()"
    
    new_text1 = "        # Get the most recent 15 messages, ordered by sequence_id for guaranteed chronological order\n        # This ensures proper conversation flow regardless of timestamp precision\n        messages = Messages.query.filter_by(\n            entityuuid=entity_uuid,\n            entity_type=entity_type,\n            message_type='chat'\n        ).order_by(\n            Messages.sequence_id.asc()\n        ).all()"
    
    # Update the paginated history
    old_text2 = "        # Get messages for current page, ordered by creation time (temporarily until restart)\n        messages = Messages.query.filter_by(\n            entityuuid=entity_uuid,\n            entity_type=entity_type,\n            message_type='chat'\n        ).order_by(\n            Messages.created_at.asc()\n        ).offset(offset).limit(PAGE_SIZE).all()"
    
    new_text2 = "        # Get messages for current page, ordered by sequence_id for guaranteed chronological order\n        messages = Messages.query.filter_by(\n            entityuuid=entity_uuid,\n            entity_type=entity_type,\n            message_type='chat'\n        ).order_by(\n            Messages.sequence_id.asc()\n        ).offset(offset).limit(PAGE_SIZE).all()"
    
    updated = False
    
    if old_text1 in content:
        content = content.replace(old_text1, new_text1)
        updated = True
    
    if old_text2 in content:
        content = content.replace(old_text2, new_text2)
        updated = True
    
    if updated:
        # Write back to file
        with open(routes_file, 'w') as f:
            f.write(content)
        
        print("✅ Updated chat routes to use sequence_id ordering")
        return True
    else:
        print("❌ Could not find temporary ordering code in routes file")
        return False

def main():
    """Main function to update files for sequence_id functionality"""
    
    print("🔄 Enabling sequence_id functionality after restart...")
    print("=" * 50)
    
    success = True
    
    # Update model file
    if not update_model_file():
        success = False
    
    # Update routes file
    if not update_chat_routes():
        success = False
    
    if success:
        print("\n🎉 Successfully enabled sequence_id functionality!")
        print("\nThe chat interface should now have perfect message ordering.")
        print("New messages will be ordered by auto-incrementing sequence_id.")
    else:
        print("\n❌ Some updates failed. Please check the files manually.")
        return False
    
    return True

if __name__ == "__main__":
    success = main()
    if not success:
        sys.exit(1)
