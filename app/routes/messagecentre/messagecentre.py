# Filepath: app/routes/messagecentre/messagecentre.py
from flask import Blueprint, render_template, session, current_app, abort
from app.models import Messages, db, Devices
from app.utilities.app_access_login_required import login_required
from app.utilities.app_logging_helper import log_with_route
from sqlalchemy import or_, and_, func
import logging
from datetime import datetime
import uuid
from markdown import markdown

messagecentre_bp = Blueprint('messagecentre_bp', __name__)

@messagecentre_bp.route('/messagecentre', methods=['GET'])
@login_required
def messagecentre():
    try:
        tenant_uuid = session.get('tenant_uuid')

        # Get system messages (all messages from system user, excluding terminal)
        system_messages = Messages.query.filter(
            Messages.tenantuuid == tenant_uuid,
            Messages.useruuid == '00000000-0000-0000-0000-000000000000',
            Messages.message_type != 'terminal'  # Exclude terminal sessions
        ).order_by(Messages.created_at.desc()).all()

        # Get conversations (messages with conversation UUID, excluding terminal)
        conversations = db.session.query(
            Messages.conversationuuid,
            Messages.entity_type,
            Messages.entityuuid,
            func.max(Messages.created_at).label('last_message_time')
        ).filter(
            Messages.tenantuuid == tenant_uuid,
            Messages.conversationuuid.isnot(None),
            Messages.useruuid != '00000000-0000-0000-0000-000000000000',  # Exclude system messages
            Messages.message_type != 'terminal'  # Exclude terminal sessions
        ).group_by(
            Messages.conversationuuid,
            Messages.entity_type,
            Messages.entityuuid
        ).order_by(
            func.max(Messages.created_at).desc()
        ).all()

        # Get terminal sessions (grouped by device)
        terminal_sessions = db.session.query(
            Messages.entityuuid,
            Messages.entity_type,
            func.max(Messages.created_at).label('last_session_time'),
            func.count(Messages.messageuuid).label('query_count')
        ).filter(
            Messages.tenantuuid == tenant_uuid,
            Messages.message_type == 'terminal'
        ).group_by(
            Messages.entityuuid,
            Messages.entity_type
        ).order_by(
            func.max(Messages.created_at).desc()
        ).all()

        formatted_items = []

        # Format system messages
        for msg in system_messages:
            timestamp = datetime.fromtimestamp(msg.created_at)
            time_display = timestamp.strftime("%I:%M %p") if timestamp.date() == datetime.today().date() else timestamp.strftime("%b %d")

            formatted_items.append({
                'uuid': str(msg.messageuuid),
                'title': msg.title,
                'content': msg.content,
                'timestamp': time_display,
                'is_read': msg.is_read,
                'sender': "System Message",
                'is_conversation': False,
                'is_terminal': False,
                'entity_info': ""
            })

        # Format conversations
        for conv in conversations:
            # Get the last message from this conversation
            last_message = Messages.query.filter(
                Messages.conversationuuid == conv.conversationuuid
            ).order_by(Messages.created_at.desc()).first()

            # Get entity info
            entity_info = ""
            if conv.entity_type == 'device':
                device = Devices.query.get(conv.entityuuid)
                entity_info = f"Conversation with {device.devicename if device else 'Unknown Device'}"

            timestamp = datetime.fromtimestamp(conv.last_message_time)
            time_display = timestamp.strftime("%I:%M %p") if timestamp.date() == datetime.today().date() else timestamp.strftime("%b %d")

            formatted_items.append({
                'uuid': str(conv.conversationuuid),
                'title': entity_info,
                'content': last_message.content if last_message else "No messages",
                'timestamp': time_display,
                'is_read': True,  # You might want to check if all messages are read
                'sender': "Chat",
                'is_conversation': True,
                'is_terminal': False,
                'entity_info': entity_info
            })

        # Format terminal sessions
        formatted_terminal_sessions = []
        for session_data in terminal_sessions:
            if session_data.entity_type == 'device':
                device = Devices.query.get(session_data.entityuuid)
                device_name = device.devicename if device else 'Unknown Device'

                timestamp = datetime.fromtimestamp(session_data.last_session_time)
                time_display = timestamp.strftime("%I:%M %p") if timestamp.date() == datetime.today().date() else timestamp.strftime("%b %d")

                formatted_terminal_sessions.append({
                    'uuid': str(session_data.entityuuid),
                    'title': f"Terminal Session - {device_name}",
                    'content': f"{session_data.query_count} queries executed",
                    'timestamp': time_display,
                    'is_read': True,
                    'sender': "Terminal",
                    'is_conversation': False,
                    'is_terminal': True,
                    'entity_info': f"Terminal on {device_name}",
                    'device_uuid': str(session_data.entityuuid),
                    'query_count': session_data.query_count
                })

        return render_template(
            'messagecentre/index.html',
            messages=formatted_items,
            terminal_sessions=formatted_terminal_sessions,
            total_messages=len(formatted_items),
            total_terminal_sessions=len(formatted_terminal_sessions),
            unread_count=sum(1 for msg in formatted_items if not msg['is_read']),
            conversation_count=len(conversations)
        )

    except Exception as e:
        current_app.logger.error(f"Error in messagecentre route: {str(e)}")
        return render_template('errors/500.html'), 500

@messagecentre_bp.route('/messagecentre/view/<message_id>', methods=['GET'])
@login_required
def messageview(message_id):
    try:
        tenant_uuid = session.get('tenant_uuid')
        message_uuid = uuid.UUID(message_id)

        # First check if this is a conversation UUID
        conversation_messages = Messages.query.filter(
            Messages.tenantuuid == tenant_uuid,
            Messages.conversationuuid == message_uuid
        ).order_by(Messages.sequence_id.asc()).all()

        if conversation_messages:
            # This is a conversation, redirect to conversation view
            return view_conversation(message_id)

        # If not a conversation, look for individual message
        message = Messages.query.filter_by(
            messageuuid=message_uuid,
            tenantuuid=tenant_uuid
        ).first_or_404()

        # Mark message as read if it's not already
        if not message.is_read:
            message.is_read = True
            db.session.commit()

        # Format timestamp
        timestamp = datetime.fromtimestamp(message.created_at)
        formatted_timestamp = timestamp.strftime("%B %d, %Y at %I:%M %p")

        # Use the same type checking logic for the sender
        is_system = str(message.useruuid) == '00000000-0000-0000-0000-000000000000' if isinstance(message.useruuid, uuid.UUID) else message.useruuid == '00000000-0000-0000-0000-000000000000'

        # Get entity info
        entity_info = ""
        if message.entity_type and message.entityuuid:
            if message.entity_type == 'device':
                device = Devices.query.get(message.entityuuid)
                entity_info = f" - {device.devicename if device else 'Unknown Device'}"

        formatted_message = {
            'uuid': str(message.messageuuid),
            'title': message.title,
            'content': message.content,
            'timestamp': formatted_timestamp,
            'is_read': message.is_read,
            'sender': "System Message" if is_system else "Unknown Sender",
            'entity_info': entity_info
        }

        log_with_route(logging.INFO, f"Viewing message {message_id}", route=f'/messagecentre/view/{message_id}')

        return render_template('messagecentre/messageview.html', message=formatted_message)

    except ValueError:
        current_app.logger.error(f"Invalid message ID format: {message_id}")
        abort(404)
    except Exception as e:
        current_app.logger.error(f"Error in messageview route: {str(e)}")
        return render_template('errors/500.html'), 500

@messagecentre_bp.route('/messagecentre/conversation/<conversation_id>', methods=['GET'])
@login_required
def view_conversation(conversation_id):
    try:
        tenant_uuid = session.get('tenant_uuid')
        conversation_uuid = uuid.UUID(conversation_id)

        # Get all messages in this conversation ordered by sequence_id for guaranteed chronological order
        messages = Messages.query.filter(
            Messages.tenantuuid == tenant_uuid,
            Messages.conversationuuid == conversation_uuid
        ).order_by(Messages.sequence_id.asc()).all()

        if not messages:
            abort(404)

        # Get entity info from first message
        entity_info = ""
        if messages[0].entity_type == 'device':
            device = Devices.query.get(messages[0].entityuuid)
            entity_info = f"Conversation with {device.devicename if device else 'Unknown Device'}"

        formatted_messages = [{
            'uuid': str(msg.messageuuid),
            'content': markdown(msg.content) if msg.content else "",  # Process markdown
            'timestamp': datetime.fromtimestamp(msg.created_at).strftime("%B %d, %Y at %I:%M %p"),
            'is_system': str(msg.useruuid) == '00000000-0000-0000-0000-000000000000'
        } for msg in messages]

        return render_template(
            'messagecentre/conversation.html',
            conversation_id=conversation_id,
            entity_info=entity_info,
            messages=formatted_messages
        )

    except ValueError:
        abort(404)
    except Exception as e:
        current_app.logger.error(f"Error in view_conversation: {str(e)}")
        return render_template('errors/500.html'), 500