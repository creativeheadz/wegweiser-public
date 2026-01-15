# Filepath: app/routes/ai/ai_device_metadata.py
# Filepath: app/routes/ai/ai.py
# Flask imports
from flask import Blueprint, request, jsonify, current_app, session, render_template

# SQLAlchemy imports
from sqlalchemy import func, distinct, text
from sqlalchemy.exc import IntegrityError


# Standard library imports
import os
import time
import uuid
import json
import logging
from uuid import UUID
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from app.utilities.app_logging_helper import log_with_route
# Third party imports
from dotenv import load_dotenv


# App models
from app.models import (
    db,
    Devices,
    DeviceMetadata,
    Tenants
)
from app.models import Conversations as ConversationModel

# App utilities
from app import csrf
from app.utilities.app_logging_helper import log_with_route
from app.utilities.app_access_login_required import login_required
#from app.utilities.enhanced_chat import EnhancedChatManager
#from app.utilities.enhanced_memory import EnhancedMemoryManager
from app.utilities.langchain_utils import (
    EntityMemoryManager,
    create_langchain_conversation,
    get_ai_response,
    adapt_response_style,
    generate_health_score_analysis,
    generate_entity_suggestions,
    get_tenant_uuid_for_entity
)

from . import ai_bp  # Import the blueprint

load_dotenv()
LOG_DEVICE_HEALTH_SCORE = os.getenv('LOG_DEVICE_HEALTH_SCORE', 'False').lower() == 'true'

def checkDir(dirToCheck):
    if not os.path.isdir(dirToCheck):
        os.makedirs(dirToCheck)
    log_with_route(logging.INFO, f'{dirToCheck} directory checked/created.')




@ai_bp.route('/device/metadata', methods=['POST'])
@csrf.exempt
def update_device_metadata():
    """Handle device metadata updates"""
    try:
        data = request.json

        # Validate request data
        if not all(field in data for field in ['deviceuuid', 'metalogos_type', 'metalogos']):
            return jsonify({"error": "Missing required fields"}), 400

        device = Devices.query.get(data['deviceuuid'])
        if not device:
            return jsonify({"error": "Device not found"}), 404

        # Create new metadata
        new_metadata = DeviceMetadata(
            deviceuuid=device.deviceuuid,
            metalogos_type=data['metalogos_type'],
            metalogos=data['metalogos'],
            ai_analysis=data.get('ai_analysis'),
            score=data.get('score')
        )

        try:
            # Save metadata
            db.session.add(new_metadata)
            db.session.commit()

            return jsonify({
                "message": "Metadata updated successfully",
                "metadatauuid": str(new_metadata.metadatauuid)
            }), 201

        except Exception as e:
            db.session.rollback()
            log_with_route(logging.ERROR, f"Database error: {str(e)}")
            return jsonify({"error": "Database error"}), 500

    except Exception as e:
        log_with_route(logging.ERROR, f"Request processing error: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500

def _extract_concerns(metadata: DeviceMetadata) -> List[str]:
    """Extract concerns from metadata analysis"""
    concerns = []

    if not metadata.ai_analysis:
        return concerns

    # Look for specific patterns indicating concerns
    if 'error' in metadata.ai_analysis.lower():
        concerns.append(f"Error detected in {metadata.metalogos_type}")
    if 'warning' in metadata.ai_analysis.lower():
        concerns.append(f"Warning in {metadata.metalogos_type}")
    if metadata.score and float(metadata.score) < 70:
        concerns.append(f"Low health score ({metadata.score}) in {metadata.metalogos_type}")

    return concerns

def _create_experience_summary(metadata: DeviceMetadata) -> str:
    """Create a summary of the experience from metadata"""
    if metadata.ai_analysis:
        # Take first sentence or up to 100 characters
        summary = metadata.ai_analysis.split('.')[0]
        return summary[:100] + ('...' if len(summary) > 100 else '')
    return f"New {metadata.metalogos_type} data received"