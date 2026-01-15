# Filepath: app/routes/tenant/quick_start.py
# Filepath: app/routes/quick_start.py
# Filepath: app/routes/quickstart.py
from flask import Blueprint, session, render_template, request, redirect, url_for, flash, current_app
from app.utilities.app_access_login_required import login_required
from app.utilities.ui_get_updated_faqs import get_updated_faqs
from app.utilities.app_logging_helper import log_with_route
from app.utilities.guided_tour_manager import get_tour_for_page
from app.models import db, Accounts, GuidedTour
import logging

quickstart_bp = Blueprint('quickstart_bp', __name__)

@quickstart_bp.route('/quickstart', methods=['GET'])
@login_required
def quickstart():
    user_id = session.get('user_id')
    user = Accounts.query.get(user_id)

    if not user:
        log_with_route(logging.WARNING, f'User with ID {user_id} not found in the database.')
        flash('User not found.', 'danger')
        return redirect(url_for('login_bp.login'))

    # Log access to this route
    log_with_route(logging.INFO, "Accessed Quick Start Page", route='/quickstart')

    # Get tour data for this page
    tour_data = get_tour_for_page('quickstart', user_id)

    # Render the quickstart page with tour data
    return render_template('/quickstart/index.html', tour_data=tour_data)


@quickstart_bp.route('/quickstart/debug-tours')
@login_required
def debug_tours():
    """Debug route to check tour data."""
    try:
        from app.models import GuidedTour
        tours = GuidedTour.query.all()

        result = {
            'total_tours': len(tours),
            'tours': []
        }

        for tour in tours:
            result['tours'].append({
                'page_identifier': tour.page_identifier,
                'tour_name': tour.tour_name,
                'is_active': tour.is_active,
                'steps_count': len(tour.steps) if tour.steps else 0
            })

        return result
    except Exception as e:
        return {'error': str(e)}
