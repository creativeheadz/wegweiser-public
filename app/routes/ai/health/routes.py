# Filepath: app/routes/ai/health/routes.py
# Health-related endpoints

from flask import jsonify, session
import logging

from app.utilities.app_logging_helper import log_with_route
from app.utilities.app_access_login_required import login_required

from app.routes.ai import ai_bp

@ai_bp.route('/memory/health', methods=['GET'])
@login_required
def memory_health():
    """Check memory store health"""
    try:
        from app.utilities.memory_store import MemoryStore
        memory_store = MemoryStore()
        health = memory_store.health_check()
        return jsonify(health)
    except ImportError:
        log_with_route(logging.ERROR, "MemoryStore module not found")
        return jsonify({"error": "Memory store not available"}), 500
    except Exception as e:
        log_with_route(logging.ERROR, f"Error checking memory health: {str(e)}")
        return jsonify({"error": "Failed to check memory health"}), 500
