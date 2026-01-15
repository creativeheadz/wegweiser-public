# Filepath: app/utilities/ui_get_updated_faqs.py
from app.models import db, FAQ
from flask import current_app

def get_updated_faqs():
    try:
        # Use ORM query instead of raw SQL for better reliability
        faqs = FAQ.query.order_by(FAQ.order.asc()).all()
        return faqs
    except Exception as e:
        current_app.logger.error(f"Error fetching FAQs: {str(e)}")
        return []