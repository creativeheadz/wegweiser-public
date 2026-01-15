# Filepath: app/routes/api/tours.py
"""
API routes for guided tour management.
Handles tour progress tracking and user interactions.
"""

import logging
from flask import Blueprint, request, jsonify, session
from app.utilities.app_access_login_required import login_required
from app.utilities.guided_tour_manager import (
    mark_step_complete, 
    reset_tour_progress, 
    get_user_tour_progress
)
from app.utilities.app_logging_helper import log_with_route

tours_api_bp = Blueprint('tours_api_bp', __name__, url_prefix='/api/tours')


@tours_api_bp.route('/step-complete', methods=['POST'])
@login_required
def api_mark_step_complete():
    """Mark a tour step as completed for the current user."""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        page_identifier = data.get('page_identifier')
        step_id = data.get('step_id')
        
        if not page_identifier or not step_id:
            return jsonify({'error': 'Missing page_identifier or step_id'}), 400
        
        user_id = session.get('user_id')
        if not user_id:
            return jsonify({'error': 'User not authenticated'}), 401
        
        success = mark_step_complete(user_id, page_identifier, step_id)
        
        if success:
            log_with_route(logging.INFO, f"Step {step_id} marked complete for user {user_id} on page {page_identifier}")
            return jsonify({'success': True, 'message': 'Step marked as complete'})
        else:
            return jsonify({'error': 'Failed to mark step as complete'}), 500
    
    except Exception as e:
        log_with_route(logging.ERROR, f"Error in api_mark_step_complete: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500


@tours_api_bp.route('/complete', methods=['POST'])
@login_required
def api_mark_tour_complete():
    """Mark entire tour as completed for the current user."""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        page_identifier = data.get('page_identifier')
        if not page_identifier:
            return jsonify({'error': 'Missing page_identifier'}), 400
        
        user_id = session.get('user_id')
        if not user_id:
            return jsonify({'error': 'User not authenticated'}), 401
        
        # Get current progress to log completion
        progress = get_user_tour_progress(user_id, page_identifier)
        
        log_with_route(logging.INFO, f"Tour completed for user {user_id} on page {page_identifier}")
        return jsonify({'success': True, 'message': 'Tour marked as complete', 'progress': progress})
    
    except Exception as e:
        log_with_route(logging.ERROR, f"Error in api_mark_tour_complete: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500


@tours_api_bp.route('/reset', methods=['POST'])
@login_required
def api_reset_tour_progress():
    """Reset tour progress for the current user."""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        page_identifier = data.get('page_identifier')
        if not page_identifier:
            return jsonify({'error': 'Missing page_identifier'}), 400
        
        user_id = session.get('user_id')
        if not user_id:
            return jsonify({'error': 'User not authenticated'}), 401
        
        success = reset_tour_progress(user_id, page_identifier)
        
        if success:
            log_with_route(logging.INFO, f"Tour progress reset for user {user_id} on page {page_identifier}")
            return jsonify({'success': True, 'message': 'Tour progress reset'})
        else:
            return jsonify({'error': 'Failed to reset tour progress'}), 500
    
    except Exception as e:
        log_with_route(logging.ERROR, f"Error in api_reset_tour_progress: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500


@tours_api_bp.route('/progress/<page_identifier>', methods=['GET'])
@login_required
def api_get_tour_progress(page_identifier):
    """Get tour progress for a specific page."""
    try:
        user_id = session.get('user_id')
        if not user_id:
            return jsonify({'error': 'User not authenticated'}), 401
        
        progress = get_user_tour_progress(user_id, page_identifier)
        
        if progress is not None:
            return jsonify({'success': True, 'progress': progress})
        else:
            return jsonify({'success': True, 'progress': None, 'message': 'No progress found'})
    
    except Exception as e:
        log_with_route(logging.ERROR, f"Error in api_get_tour_progress: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500
