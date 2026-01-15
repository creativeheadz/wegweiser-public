# Filepath: app/routes/ai/chat_routes.py
import traceback
import sys
from typing import Dict, Any, Optional, List
from flask import Blueprint, request, jsonify, current_app, session
from app.utilities.app_logging_helper import log_with_route
from app.utilities.app_access_login_required import login_required
from app.models import (
    db,
    Devices,
    Groups,
    Organisations,
    Tenants,
    Messages,
    Conversations
)
from sqlalchemy import text
import logging
import json
import time
from uuid import UUID
from markupsafe import escape

from . import ai_bp  # Import the blueprint

def get_entity(entity_type, entity_uuid):
    """Get entity by type and UUID"""
    print(f"Getting entity {entity_type} {entity_uuid}", file=sys.stderr)
    entity_models = {
        'device': Devices,
        'group': Groups,
        'organisation': Organisations,
        'tenant': Tenants
    }

    model = entity_models.get(entity_type)
    if not model:
        return None

    return model.query.get(entity_uuid)

def get_chat_manager():
    """Get or create ChatManager instance within application context"""
    print("Creating chat manager...", file=sys.stderr)
    if not hasattr(current_app, 'chat_manager'):
        current_app.chat_manager = ChatManager()
    return current_app.chat_manager

def get_metadata_handler():
    """Get or create MetadataHandler instance within application context"""
    if not hasattr(current_app, 'metadata_handler'):
        current_app.metadata_handler = MetadataHandler()
    return current_app.metadata_handler

def get_health_analyzer():
    """Get or create HealthAnalyzer instance within application context"""
    if not hasattr(current_app, 'health_analyzer'):
        current_app.health_analyzer = HealthAnalyzer()
    return current_app.health_analyzer

def format_ai_response(text):
    """
    Sanitize AI response to prevent XSS while preserving code formatting.
    Uses the HTML sanitizer to ensure safe rendering across themes.
    """
    from app.utilities.html_sanitizer import sanitize_html
    return sanitize_html(text)

@ai_bp.route('/<entity_type>/<uuid:entity_uuid>/chat/enhanced', methods=['POST'])
@login_required
def enhanced_chat(entity_type, entity_uuid):
    """Enhanced chat endpoint with proper validation and error handling"""
    try:
        data = request.get_json()
        user_message = data.get('message', '').strip()
        conversation_uuid = data.get('conversation_uuid')

        # Validate entity type
        if entity_type not in ['device', 'group', 'organisation', 'tenant']:
            return jsonify({
                "error": "Invalid entity type",
                "details": f"Entity type '{entity_type}' not supported"
            }), 400

        # Get or create conversation
        conversation = Conversations.get_or_create_conversation(
            tenantuuid=session.get('tenant_uuid'),
            entityuuid=entity_uuid,
            entity_type=entity_type
        )

        # Initialize chat manager
        chat_manager = ChatManager()

        # Process message
        result = chat_manager.process_message(
            user_id=session.get('user_id'),
            entity_type=entity_type,
            entity_uuid=str(entity_uuid),
            message=user_message,
            tenant_uuid=session.get('tenant_uuid'),
            conversation_uuid=conversation_uuid
        )

        # Format the response with proper HTML structure
        formatted_response = format_ai_response(result.get('response', ''))

        response = {
            "response": formatted_response,
            "conversation_uuid": str(conversation.conversationuuid) if conversation else None,
            "buttons": result.get('buttons', []),
            "is_formatted": True  # Now this is trusted markup
        }

        return jsonify(response)

    except Exception as e:
        log_with_route(logging.ERROR, f"Error generating response: {str(e)}")
        return jsonify({
            "error": "Failed to process message",
            "details": str(e)
        }), 500

@ai_bp.route('/<entity_type>/<uuid:entity_uuid>/chat_history/enhanced', methods=['GET'])
@login_required
def get_enhanced_chat_history(entity_type, entity_uuid):
    """Get chat history with pagination"""
    try:
        # Get the most recent 15 messages, ordered by sequence_id for guaranteed chronological order
        # This ensures proper conversation flow regardless of timestamp precision
        messages = Messages.query.filter_by(
            entityuuid=entity_uuid,
            entity_type=entity_type,
            message_type='chat'
        ).order_by(
            Messages.sequence_id.asc()
        ).all()

        # Take only the last 15 messages (most recent)
        messages = messages[-15:] if len(messages) > 15 else messages

        # Sanitize message content to prevent security issues when theme changes
        from app.utilities.html_sanitizer import sanitize_html

        return jsonify({
            'messages': [{
                'content': sanitize_html(msg.content) if msg.useruuid is None else msg.content,  # Sanitize AI messages only
                'is_ai': msg.useruuid is None,
                'timestamp': msg.created_at * 1000,
                'conversation_uuid': str(msg.conversationuuid),
                'message_uuid': str(msg.messageuuid),
                'is_formatted': True  # Always HTML/markup now
            } for msg in messages]
        })

    except Exception as e:
        log_with_route(logging.ERROR, f"Error getting enhanced chat history: {str(e)}")
        return jsonify({
            'error': 'Failed to load chat history',
            'messages': []
        }), 500

def generate_contextual_buttons(entity_type, entity, metadata_handler):
    """Generate contextual buttons based on entity state"""
    buttons = [{"text": "System Status", "action": "status"}]

    try:
        # Get recent analyses
        recent_analyses = metadata_handler.get_recent_analyses(
            entity_type=entity_type,
            entity_uuid=str(entity.entityuuid),
            limit=5
        )

        # Add buttons based on analyses
        for analysis in recent_analyses:
            if analysis.get('score', 100) < 70:
                buttons.append({"text": "View Issues", "action": "issues"})
                break

        if entity_type == 'device':
            buttons.extend([
                {"text": "Performance", "action": "performance"},
                {"text": "Security", "action": "security"}
            ])
        elif entity_type in ['group', 'organisation', 'tenant']:
            buttons.append({"text": "Analytics", "action": "analytics"})

    except Exception as e:
        log_with_route(logging.ERROR, f"Error generating buttons: {str(e)}")
        # Return basic buttons if there's an error
        if entity_type == 'device':
            buttons.extend([
                {"text": "Performance", "action": "performance"},
                {"text": "Security", "action": "security"}
            ])

    return buttons

@ai_bp.route('/<entity_type>/<uuid:entity_uuid>/chat/history/<int:page>', methods=['GET'])
@login_required
def get_paginated_chat_history(entity_type, entity_uuid, page):
    """Paginated history for loading older messages"""
    try:
        PAGE_SIZE = 50
        offset = (page - 1) * PAGE_SIZE

        # Get total count for pagination
        total_count = Messages.query.filter_by(
            entityuuid=entity_uuid,
            entity_type=entity_type,
            message_type='chat'
        ).count()

        # Get messages for current page, ordered by sequence_id for guaranteed chronological order
        messages = Messages.query.filter_by(
            entityuuid=entity_uuid,
            entity_type=entity_type,
            message_type='chat'
        ).order_by(
            Messages.sequence_id.asc()
        ).offset(offset).limit(PAGE_SIZE).all()

        # Sanitize message content for paginated history as well
        from app.utilities.html_sanitizer import sanitize_html

        return jsonify({
            'messages': [{
                'content': sanitize_html(msg.content) if msg.useruuid is None else msg.content,  # Sanitize AI messages only
                'is_ai': msg.useruuid is None,
                'timestamp': msg.created_at * 1000,
                'message_uuid': str(msg.messageuuid),
                'is_formatted': msg.useruuid is None  # Mark AI messages as formatted
            } for msg in messages],
            'has_more': total_count > (offset + PAGE_SIZE),
            'total_count': total_count
        })

    except Exception as e:
        log_with_route(logging.ERROR, f"Error getting paginated history: {str(e)}")
        return jsonify({
            'error': 'Failed to load chat history',
            'messages': []
        }), 500

@ai_bp.route('/<entity_type>/<uuid:entity_uuid>/tags', methods=['POST'])
@login_required
def update_entity_tags(entity_type, entity_uuid):
    """Update entity tags"""
    try:
        if entity_type != 'device':
            return jsonify({"error": "Tags are only supported for devices"}), 400

        data = request.get_json()
        if not isinstance(data, dict):
            return jsonify({"error": "Invalid tags format"}), 400

        device = Devices.query.get(entity_uuid)
        if not device:
            return jsonify({"error": "Device not found"}), 404

        # Note: Tags functionality removed with consciousness feature
        # This endpoint is deprecated
        return jsonify({
            "message": "Tags functionality has been removed",
            "tags": {}
        })

    except Exception as e:
        log_with_route(logging.ERROR, f"Error updating tags: {str(e)}")
        return jsonify({"error": "Failed to update tags"}), 500

@ai_bp.route('/<entity_type>/<uuid:entity_uuid>/tags', methods=['DELETE'])
@login_required
def remove_entity_tags(entity_type, entity_uuid):
    """Remove entity tags"""
    try:
        if entity_type != 'device':
            return jsonify({"error": "Tags are only supported for devices"}), 400

        data = request.get_json()
        if not isinstance(data, list):
            return jsonify({"error": "Invalid tag keys format"}), 400

        device = Devices.query.get(entity_uuid)
        if not device:
            return jsonify({"error": "Device not found"}), 404

        # Note: Tags functionality removed with consciousness feature
        # This endpoint is deprecated
        return jsonify({
            "message": "Tags functionality has been removed",
            "tags": {}
        })

    except Exception as e:
        log_with_route(logging.ERROR, f"Error removing tags: {str(e)}")
        return jsonify({"error": "Failed to remove tags"}), 500