# Filepath: app/routes/ai/entity/routes.py
# Entity-related endpoints

from flask import jsonify, request, session
import logging
from uuid import UUID

from app.utilities.app_logging_helper import log_with_route
from app.utilities.app_access_login_required import login_required
from app.utilities.langchain_utils import (
    generate_health_score_analysis,
    generate_entity_suggestions
)

from app.routes.ai import ai_bp
from app.routes.ai.core import get_entity
from app.routes.ai.entity.utils import get_entity_context

@ai_bp.route('/<entity_type>/<uuid:entity_uuid>/health_score_analysis', methods=['GET'])
@login_required
def get_health_score_analysis(entity_type, entity_uuid):
    """Get health score analysis for an entity"""
    analysis = generate_health_score_analysis(entity_type, entity_uuid)
    return jsonify({"analysis": analysis})

@ai_bp.route('/<entity_type>/<uuid:entity_uuid>/suggestions', methods=['GET'])
@login_required
def get_entity_suggestions(entity_type, entity_uuid):
    """Get suggestions for an entity"""
    suggestions = generate_entity_suggestions(entity_type, entity_uuid)
    return jsonify({"suggestions": suggestions})
