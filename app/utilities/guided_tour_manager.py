# Filepath: app/utilities/guided_tour_manager.py
"""
Utility functions for managing guided tours across the application.
Provides a clean API for retrieving, validating, and managing tour data.
"""

import logging
import time
from flask import session
from app.models import GuidedTour, TourProgress, db
from app.utilities.app_logging_helper import log_with_route


def get_tour_for_page(page_identifier, user_id=None):
    """
    Get tour configuration for a specific page.
    
    Args:
        page_identifier (str): Unique identifier for the page
        user_id (str, optional): User ID to include progress information
    
    Returns:
        dict: Tour configuration with optional progress data
    """
    try:
        tour = GuidedTour.get_by_page(page_identifier)
        if not tour:
            return None
        
        tour_data = tour.to_dict()
        
        # Add user progress if user_id is provided
        if user_id:
            progress = TourProgress.get_user_progress(user_id, tour.tour_id)
            if progress:
                tour_data['user_progress'] = {
                    'completed_steps': progress.completed_steps or [],
                    'is_completed': progress.is_completed,
                    'last_step': progress.last_step,
                    'last_accessed': progress.last_accessed
                }
            else:
                tour_data['user_progress'] = {
                    'completed_steps': [],
                    'is_completed': False,
                    'last_step': None,
                    'last_accessed': None
                }
        
        return tour_data
    
    except Exception as e:
        log_with_route(logging.ERROR, f"Error retrieving tour for page {page_identifier}: {str(e)}")
        return None


def create_tour(page_identifier, page_title, tour_name, steps, tour_description=None, 
                tour_config=None, auto_start=False, created_by=None):
    """
    Create a new guided tour.
    
    Args:
        page_identifier (str): Unique identifier for the page
        page_title (str): Human-readable page name
        tour_name (str): Name of the tour
        steps (list): List of tour steps
        tour_description (str, optional): Description of the tour
        tour_config (dict, optional): Shepherd.js configuration
        auto_start (bool): Whether to auto-start the tour
        created_by (str, optional): User ID who created the tour
    
    Returns:
        GuidedTour: Created tour object or None if failed
    """
    try:
        # Validate steps
        if not validate_tour_steps(steps):
            log_with_route(logging.ERROR, f"Invalid tour steps for {page_identifier}")
            return None
        
        # Check if tour already exists for this page
        existing_tour = GuidedTour.get_by_page(page_identifier)
        if existing_tour:
            log_with_route(logging.WARNING, f"Tour already exists for page {page_identifier}")
            return None
        
        tour = GuidedTour(
            page_identifier=page_identifier,
            page_title=page_title,
            tour_name=tour_name,
            tour_description=tour_description,
            steps=steps,
            tour_config=tour_config or {},
            auto_start=auto_start,
            created_by=created_by
        )
        
        db.session.add(tour)
        db.session.commit()
        
        log_with_route(logging.INFO, f"Created tour for page {page_identifier}")
        return tour
    
    except Exception as e:
        log_with_route(logging.ERROR, f"Error creating tour for page {page_identifier}: {str(e)}")
        db.session.rollback()
        return None


def update_tour_steps(page_identifier, steps):
    """
    Update steps for an existing tour.
    
    Args:
        page_identifier (str): Page identifier
        steps (list): New tour steps
    
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        if not validate_tour_steps(steps):
            log_with_route(logging.ERROR, f"Invalid tour steps for {page_identifier}")
            return False
        
        tour = GuidedTour.get_by_page(page_identifier)
        if not tour:
            log_with_route(logging.ERROR, f"Tour not found for page {page_identifier}")
            return False
        
        tour.update_steps(steps)
        log_with_route(logging.INFO, f"Updated tour steps for page {page_identifier}")
        return True
    
    except Exception as e:
        log_with_route(logging.ERROR, f"Error updating tour steps for page {page_identifier}: {str(e)}")
        return False


def validate_tour_steps(steps):
    """
    Validate tour steps structure.
    
    Args:
        steps (list): List of tour steps to validate
    
    Returns:
        bool: True if valid, False otherwise
    """
    if not isinstance(steps, list) or len(steps) == 0:
        return False
    
    required_fields = ['id', 'text']
    
    for step in steps:
        if not isinstance(step, dict):
            return False
        
        # Check required fields
        for field in required_fields:
            if field not in step:
                return False
        
        # Validate attachTo if present
        if 'attachTo' in step:
            attach_to = step['attachTo']
            if isinstance(attach_to, dict):
                if 'element' not in attach_to:
                    return False
            elif not isinstance(attach_to, str):
                return False
    
    return True


def mark_step_complete(user_id, page_identifier, step_id):
    """
    Mark a tour step as completed for a user.
    
    Args:
        user_id (str): User ID
        page_identifier (str): Page identifier
        step_id (str): Step ID to mark as complete
    
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        tour = GuidedTour.get_by_page(page_identifier)
        if not tour:
            return False
        
        progress = TourProgress.create_or_update(user_id, tour.tour_id)
        progress.mark_step_complete(step_id)
        
        log_with_route(logging.INFO, f"Marked step {step_id} complete for user {user_id} on page {page_identifier}")
        return True
    
    except Exception as e:
        log_with_route(logging.ERROR, f"Error marking step complete: {str(e)}")
        return False


def reset_tour_progress(user_id, page_identifier):
    """
    Reset tour progress for a user on a specific page.
    
    Args:
        user_id (str): User ID
        page_identifier (str): Page identifier
    
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        tour = GuidedTour.get_by_page(page_identifier)
        if not tour:
            return False
        
        progress = TourProgress.get_user_progress(user_id, tour.tour_id)
        if progress:
            progress.reset_progress()
            log_with_route(logging.INFO, f"Reset tour progress for user {user_id} on page {page_identifier}")
        
        return True
    
    except Exception as e:
        log_with_route(logging.ERROR, f"Error resetting tour progress: {str(e)}")
        return False


def get_user_tour_progress(user_id, page_identifier):
    """
    Get tour progress for a specific user and page.
    
    Args:
        user_id (str): User ID
        page_identifier (str): Page identifier
    
    Returns:
        dict: Progress information or None
    """
    try:
        tour = GuidedTour.get_by_page(page_identifier)
        if not tour:
            return None
        
        progress = TourProgress.get_user_progress(user_id, tour.tour_id)
        if not progress:
            return None
        
        return {
            'completed_steps': progress.completed_steps or [],
            'is_completed': progress.is_completed,
            'last_step': progress.last_step,
            'progress_percentage': len(progress.completed_steps or []) / len(tour.steps) * 100 if tour.steps else 0
        }
    
    except Exception as e:
        log_with_route(logging.ERROR, f"Error getting user tour progress: {str(e)}")
        return None


def get_all_tours():
    """
    Get all tours (both active and inactive).

    Returns:
        list: List of tour dictionaries
    """
    try:
        tours = GuidedTour.query.all()  # Get ALL tours, not just active ones
        return [tour.to_dict() for tour in tours]

    except Exception as e:
        log_with_route(logging.ERROR, f"Error getting all tours: {str(e)}")
        return []


def get_all_active_tours():
    """
    Get only active tours (for user-facing functionality).

    Returns:
        list: List of active tour dictionaries
    """
    try:
        tours = GuidedTour.get_all_active()
        return [tour.to_dict() for tour in tours]

    except Exception as e:
        log_with_route(logging.ERROR, f"Error getting active tours: {str(e)}")
        return []


def deactivate_tour(page_identifier):
    """
    Deactivate a tour for a specific page.
    
    Args:
        page_identifier (str): Page identifier
    
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        tour = GuidedTour.get_by_page(page_identifier)
        if not tour:
            return False
        
        tour.is_active = False
        tour.updated_at = int(time.time())
        db.session.commit()
        
        log_with_route(logging.INFO, f"Deactivated tour for page {page_identifier}")
        return True
    
    except Exception as e:
        log_with_route(logging.ERROR, f"Error deactivating tour: {str(e)}")
        return False
