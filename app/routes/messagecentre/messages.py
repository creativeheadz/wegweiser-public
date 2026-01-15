# Filepath: app/routes/messagecentre/messages.py
# Filepath: app/routes/messages.py
from flask import Blueprint, request, jsonify, session, current_app
from app.models import db, Messages, Devices, Groups
from sqlalchemy.exc import IntegrityError
from sqlalchemy import or_
import uuid
import json
import time
import requests
import traceback
from app.utilities.app_utilities_check_api_key import check_api_key  # Import the helper function
from app.utilities.app_access_login_required import login_required
from app.models import MessageStream  # Import the MessageStream model
from app import csrf



messages_bp = Blueprint('messages_bp', __name__)


import requests
import json
import time
from flask import current_app, jsonify

""" 
@messages_bp.route('/update_stream', methods=['GET'])
@login_required
def update_stream():
    tenant_uuid = session.get('tenant_uuid')
    
    if not tenant_uuid:
        return jsonify({"error": "Unauthorized access", "tenant_uuid": tenant_uuid}), 403

    skald_url = f"https://skald.oldforge.tech/Tenant-{tenant_uuid}/json"
    auth = ('john', '9Palo)pad')  # Authentication credentials

    try:
        # Fetch the stream from Skald
        params = {'poll': 'true'}
        resp = requests.get(skald_url, auth=auth, params=params, stream=True)
        
        if resp.status_code != 200:
            return jsonify({"error": "Failed to fetch stream"}), resp.status_code

        # Process the stream
        stream_data = []
        for line in resp.iter_lines():
            if line:
                message = json.loads(line.decode('utf-8'))  # Parse JSON object
                stream_data.append(message)

        # Check if there's an existing stream entry for this tenant
        stream_entry = MessageStream.query.filter_by(tenantuuid=tenant_uuid).first()

        if not stream_entry:
            # Create a new stream entry if it doesn't exist
            stream_entry = MessageStream(
                tenantuuid=tenant_uuid,
                stream=stream_data
            )
            db.session.add(stream_entry)
        else:
            # Update the existing stream
            stream_entry.stream = stream_data
        
        # Commit the changes to the database
        db.session.commit()

        return jsonify({"status": "Stream updated", "stream": stream_data})

    except Exception as e:
        current_app.logger.error(f"Error updating stream: {str(e)}")
        return jsonify({"error": "An internal error occurred"}), 500 """


""" @messages_bp.route('/messagestream', methods=['GET'])
@login_required
def get_messagestream():
    tenant_uuid = session.get('tenant_uuid')

    if not tenant_uuid:
        return jsonify({"error": "Unauthorized access", "tenant_uuid": tenant_uuid}), 403

    # Step 1: Trigger the internal logic for updating the stream
    skald_url = f"https://chat.wegweiser.tech/Tenant-{tenant_uuid}/json"
    auth = ('john', '9Palo)pad')  # Authentication credentials

    try:
        # Fetch the stream from Skald
        params = {'poll': 'true'}
        resp = requests.get(skald_url, auth=auth, params=params, stream=True)

        if resp.status_code != 200:
            return jsonify({"error": "Failed to fetch stream"}), resp.status_code

        # Process the stream
        stream_data = []
        for line in resp.iter_lines():
            if line:
                message = json.loads(line.decode('utf-8'))  # Parse JSON object
                stream_data.append(message)

        # Check if there's an existing stream entry for this tenant
        stream_entry = MessageStream.query.filter_by(tenantuuid=tenant_uuid).first()

        if not stream_entry:
            # Create a new stream entry if it doesn't exist
            stream_entry = MessageStream(
                tenantuuid=tenant_uuid,
                stream=stream_data
            )
            db.session.add(stream_entry)
        else:
            # Update the existing stream
            stream_entry.stream = stream_data

        # Commit the changes to the database
        db.session.commit()

    except Exception as e:
        current_app.logger.error(f"Error updating stream: {str(e)}")
        return jsonify({"error": "An internal error occurred while updating the stream"}), 500

    # Step 2: Now fetch and return the updated stream for the tenant
    try:
        stream_entry = MessageStream.query.filter_by(tenantuuid=tenant_uuid).first()

        if not stream_entry:
            return jsonify({"error": "No message stream found"}), 404

        return jsonify({"stream": stream_entry.stream})

    except Exception as e:
        current_app.logger.error(f"Error in get_messagestream: {str(e)}")
        return jsonify({"error": "An internal error occurred while fetching the stream"}), 500


 """

@messages_bp.route('/messages', methods=['GET'])
@login_required
def get_messages():
    user_uuid = session.get('user_id')
    tenant_uuid = session.get('tenant_uuid')

    if not user_uuid or not tenant_uuid:
        return jsonify({"error": "Unauthorized access", "user_uuid": user_uuid, "tenant_uuid": tenant_uuid}), 403

    try:
        messages = Messages.query.filter(
            Messages.tenantuuid == tenant_uuid,
            or_(Messages.useruuid == '00000000-0000-0000-0000-000000000000')
        ).order_by(Messages.created_at.desc()).all()

        message_list = [{
            'uuid': str(msg.messageuuid),
            'title': msg.title,
            'content': msg.content,
            'timestamp': msg.created_at,
            'is_read': msg.is_read,
            'entity_uuid': str(msg.entityuuid) if msg.entityuuid else None,
            'entity_type': msg.entity_type if msg.entity_type else None,
            'conversation_uuid': str(msg.conversationuuid) if msg.conversationuuid else None
        } for msg in messages]

        return jsonify(message_list)
    except Exception as e:
        current_app.logger.error(f"Error in get_messages: {str(e)}")
        current_app.logger.error(traceback.format_exc())
        return jsonify({"error": "An internal error occurred"}), 500

@messages_bp.route('/notifications/recent', methods=['GET'])
@login_required
def get_recent_notifications():
    """Get recent unread notifications for the header dropdown"""
    tenant_uuid = session.get('tenant_uuid')

    if not tenant_uuid:
        return jsonify({"error": "Unauthorized access"}), 403

    try:
        # Get recent unread system messages and conversations (excluding terminal sessions)
        # Limit to 10 most recent unread items
        recent_messages = Messages.query.filter(
            Messages.tenantuuid == tenant_uuid,
            Messages.is_read == False,
            Messages.message_type != 'terminal'  # Exclude terminal sessions
        ).order_by(Messages.created_at.desc()).limit(10).all()

        notifications = []
        for msg in recent_messages:
            # Determine icon and type based on message content
            icon_class = "fas fa-info-circle text-primary"
            if "device" in msg.title.lower() or "registered" in msg.title.lower():
                icon_class = "fas fa-laptop text-success"
            elif "error" in msg.title.lower() or "failed" in msg.title.lower():
                icon_class = "fas fa-exclamation-triangle text-warning"
            elif "chat" in msg.message_type:
                icon_class = "fas fa-comments text-info"

            # Format timestamp
            from datetime import datetime
            timestamp = datetime.fromtimestamp(msg.created_at)
            if timestamp.date() == datetime.today().date():
                time_display = timestamp.strftime("%I:%M %p")
            else:
                time_display = timestamp.strftime("%b %d")

            # Truncate content for preview
            content_preview = msg.content[:80] + "..." if len(msg.content) > 80 else msg.content

            notifications.append({
                'uuid': str(msg.messageuuid),
                'title': msg.title,
                'content': content_preview,
                'timestamp': time_display,
                'icon_class': icon_class,
                'is_conversation': msg.conversationuuid is not None,
                'view_url': f"/messagecentre/view/{msg.messageuuid}"
            })

        # Get total unread count (excluding terminal sessions)
        unread_count = Messages.query.filter(
            Messages.tenantuuid == tenant_uuid,
            Messages.is_read == False,
            Messages.message_type != 'terminal'  # Exclude terminal sessions
        ).count()

        return jsonify({
            'notifications': notifications,
            'unread_count': unread_count,
            'has_more': unread_count > 10
        })

    except Exception as e:
        current_app.logger.error(f"Error in get_recent_notifications: {str(e)}")
        return jsonify({"error": "An internal error occurred"}), 500

@messages_bp.route('/notifications/<notification_id>/mark-read', methods=['POST'])
@csrf.exempt
@login_required
def mark_notification_read(notification_id):
    """Mark a specific notification as read"""
    tenant_uuid = session.get('tenant_uuid')

    if not tenant_uuid:
        return jsonify({"error": "Unauthorized access"}), 403

    try:
        message = Messages.query.filter_by(
            messageuuid=notification_id,
            tenantuuid=tenant_uuid
        ).first()

        if not message:
            return jsonify({"error": "Notification not found"}), 404

        message.is_read = True
        db.session.commit()

        return jsonify({"success": "Notification marked as read"})

    except Exception as e:
        current_app.logger.error(f"Error marking notification as read: {str(e)}")
        db.session.rollback()
        return jsonify({"error": "An internal error occurred"}), 500

@messages_bp.route('/notifications/mark-all-read', methods=['POST'])
@csrf.exempt
@login_required
def mark_all_notifications_read():
    """Mark all notifications as read for the current tenant"""
    tenant_uuid = session.get('tenant_uuid')

    if not tenant_uuid:
        return jsonify({"error": "Unauthorized access"}), 403

    try:
        # Update all unread messages for this tenant
        updated_count = Messages.query.filter_by(
            tenantuuid=tenant_uuid,
            is_read=False
        ).update({'is_read': True})

        db.session.commit()

        return jsonify({
            "success": "All notifications marked as read",
            "updated_count": updated_count
        })

    except Exception as e:
        current_app.logger.error(f"Error marking all notifications as read: {str(e)}")
        db.session.rollback()
        return jsonify({"error": "An internal error occurred"}), 500

@messages_bp.route('/messages/script', methods=['POST'])
def post_message_script():
    if not check_api_key():
        return jsonify({"error": "Unauthorized access"}), 403

    data = request.get_json()
    tenant_uuid = data.get('tenantuuid')
    user_uuid = '00000000-0000-0000-0000-000000000000'  # System user UUID

    current_app.logger.info(f"Posting message for tenant_uuid {tenant_uuid}")

    if not tenant_uuid:
        return jsonify({"error": "Tenant UUID is required"}), 400

    title = data.get('title')
    content = data.get('content')
    entity_uuid = data.get('entity_uuid')  # For device, group, etc.
    entity_type = data.get('entity_type', 'system')  # Default to 'system' if not specified

    if not title or not content:
        return jsonify({"error": "Title and content are required"}), 400

    try:
        message_uuid = str(uuid.uuid4())
        message = Messages(
            messageuuid=message_uuid,
            conversationuuid=str(uuid.uuid4()),  # Generate new conversation UUID
            useruuid=user_uuid,
            tenantuuid=tenant_uuid,
            entityuuid=entity_uuid,
            entity_type=entity_type,
            title=title,
            content=content,
            is_read=False,
            created_at=int(time.time())
        )
        db.session.add(message)
        db.session.commit()

        current_app.logger.info(f"Successfully posted message: {message_uuid}")
        return jsonify({"success": "Message posted", "messageuuid": message_uuid}), 201
    except IntegrityError as e:
        current_app.logger.error(f'IntegrityError posting message. Rolling back... Error: {e}')
        db.session.rollback()
        return jsonify({'error': 'Integrity error: ' + str(e)}), 400
    except Exception as e:
        current_app.logger.error(f"Failed to post message. Reason: {e}. Rolling back...")
        db.session.rollback()
        return jsonify({'error': str(e)}), 500