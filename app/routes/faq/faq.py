# Filepath: app/routes/faq/faq.py
# Filepath: app/routes/faq.py
from flask import Blueprint, render_template
from app.utilities.app_access_login_required import login_required
from app.utilities.ui_get_updated_faqs import get_updated_faqs
from app.utilities.app_logging_helper import log_with_route
import logging

faq_bp = Blueprint('faq_bp', __name__)

@faq_bp.route('/faq', methods=['GET'])
@login_required
def faq():
    # Log access to this route
    log_with_route(logging.INFO, "Accessed FAQ page", route='/faq')

    # Get the updated FAQs
    faqs = get_updated_faqs()

    # Render the FAQ page with the FAQs data
    return render_template('faq/index.html', faqs=faqs)
