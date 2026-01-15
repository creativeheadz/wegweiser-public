# Filepath: app/routes/ai/core.py
# Core utilities and shared functions for AI routes

# Flask imports
from flask import current_app, session
import logging
import os
import time
import uuid
from typing import List, Dict, Any, Optional
import re

# App models
from app.models import (
    db,
    Devices,
    DeviceMetadata,
    Tenants,
    Messages,
    Groups,
    Organisations,
    DeviceStatus,
    DeviceGpu,
    DeviceBios,
    DeviceMemory,
    DeviceDrives,
    DeviceBattery,
    DeviceNetworks,
    DevicePrinters,
)
from app.models import Conversations as ConversationModel
from app.models import Conversations as LegacyConversationModel

# App utilities
from app.utilities.app_logging_helper import log_with_route
from app.utilities.langchain_utils import get_tenant_uuid_for_entity

from dotenv import load_dotenv
load_dotenv()
LOG_DEVICE_HEALTH_SCORE = os.getenv('LOG_DEVICE_HEALTH_SCORE', 'False').lower() == 'true'

def checkDir(dirToCheck):
    if not os.path.isdir(dirToCheck):
        os.makedirs(dirToCheck)
    log_with_route(logging.INFO, f'{dirToCheck} directory checked/created.')

def get_entity(entity_type, entity_uuid):
    """Get an entity by type and UUID"""
    if entity_type == 'device':
        return Devices.query.get(entity_uuid)
    elif entity_type == 'group':
        return Groups.query.get(entity_uuid)
    elif entity_type == 'organisation':
        return Organisations.query.get(entity_uuid)
    elif entity_type == 'tenant':
        return Tenants.query.get(entity_uuid)
    else:
        return None

def get_or_create_conversation(entity_type, entity_uuid):
    """Get or create a conversation for an entity"""
    conversation = LegacyConversationModel.query.filter_by(
        entityuuid=entity_uuid,
        entity_type=entity_type
    ).order_by(LegacyConversationModel.last_updated.desc()).first()

    if not conversation:
        tenantuuid = get_tenant_uuid_for_entity(entity_uuid, entity_type)
        if entity_type == 'device':
            conversation = LegacyConversationModel(
                tenantuuid=tenantuuid,
                deviceuuid=entity_uuid,
                entityuuid=entity_uuid,
                entity_type=entity_type
            )
        else:
            conversation = LegacyConversationModel.create_non_device_conversation(
                tenantuuid=tenantuuid,
                entityuuid=entity_uuid,
                entity_type=entity_type
            )
        db.session.add(conversation)
        db.session.commit()

    return conversation

def store_conversation(conversation, user_id, entity_uuid, tenantuuid, user_message, ai_response_content, entity_type):
    """Store a conversation in the database"""
    try:
        # Create user message record with real timestamp
        user_message_record = Messages(
            messageuuid=uuid.uuid4(),
            conversationuuid=conversation.conversationuuid,
            useruuid=user_id,  # User's message has useruuid
            tenantuuid=tenantuuid,
            entityuuid=entity_uuid,
            entity_type=entity_type,
            title='User Message',
            content=user_message,
            is_read=True,  # Mark as read since it's the user's own message
            created_at=int(time.time()),
            message_type='chat'
        )

        # Create AI response record (note: no useruuid for AI messages)
        # sequence_id will auto-increment to ensure proper ordering
        ai_message_record = Messages(
            messageuuid=uuid.uuid4(),
            conversationuuid=conversation.conversationuuid,
            useruuid=None,  # AI message has no user ID
            tenantuuid=tenantuuid,
            entityuuid=entity_uuid,
            entity_type=entity_type,
            title='AI Response',
            content=ai_response_content,
            is_read=True,
            created_at=int(time.time()),
            message_type='chat'
        )

        # Update conversation's last_updated timestamp
        conversation.last_updated = int(time.time())

        # Add both messages to the session
        db.session.add(user_message_record)
        db.session.add(ai_message_record)
        db.session.add(conversation)

        # Commit the changes
        db.session.commit()

        log_with_route(logging.INFO, f'Stored conversation messages for {entity_type} UUID {entity_uuid}')

    except Exception as e:
        db.session.rollback()
        log_with_route(logging.ERROR, f'Error storing conversation: {str(e)}')
        raise

def get_tenant_profile(tenant):
    """Get a tenant profile string"""
    return f"""
    Specializations: {tenant.specializations}
    SLA Details: {tenant.sla_details}
    Industry: {tenant.industry}
    Preferred Communication Style: {tenant.preferred_communication_style}
    """

def get_printers_by_deviceuuid(deviceuuid):
    """Helper function to get printer information for a device"""
    return DevicePrinters.query.filter_by(deviceuuid=deviceuuid).all()

def _extract_top_events(metalogos):
    """Extract top events from metalogos data"""
    if not metalogos or not isinstance(metalogos, dict):
        return []

    try:
        sources = metalogos.get('Sources', {})
        top_events = sources.get('TopEvents', [])
        return top_events[:10]  # Return top 10 events
    except Exception as e:
        log_with_route(logging.ERROR, f"Error extracting top events: {str(e)}")
        return []
