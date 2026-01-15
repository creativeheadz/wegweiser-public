# Filepath: app/routes/contact/contact.py
from flask import Blueprint, request, jsonify, current_app
import requests
import logging
from app.utilities.app_logging_helper import log_with_route
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_wtf.csrf import CSRFProtect
from app import csrf

contact_bp = Blueprint('contact_bp', __name__)

CORS(contact_bp, resources={
    r"/contact": {
        "origins": ["https://wegweiser.tech", "https://www.wegweiser.tech"],
        "methods": ["POST", "OPTIONS"],
        "allow_headers": ["Content-Type", "Accept"],
        "supports_credentials": True
    }
})

limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["5 per minute"]
)

def create_supportdesk_ticket(name, email, subject, message):
    """Create a ticket in the support desk system."""
    try:
        from app import get_secret
        
        supportdesk_url = "https://support.oldforge.tech/api/v1"
        supportdesk_token = get_secret('SUPPORTDESKAPITOKEN')
        
        headers = {
            "Authorization": f"Token token={supportdesk_token}",
            "Content-Type": "application/json"
        }

        # First create or get the user
        user_data = {
            "firstname": name,
            "email": email,
            "roles": ["Customer"]
        }

        user_response = requests.post(
            f"{supportdesk_url}/users",
            json=user_data,
            headers=headers,
            timeout=10
        )

        if not user_response.ok and user_response.status_code != 422:  # 422 means user exists
            log_with_route(logging.ERROR, f"Failed to create user: {user_response.status_code} - {user_response.text}")
            return False, None

        # Get user ID either from creation or lookup
        if user_response.status_code == 422:
            # User exists, look them up
            search_response = requests.get(
                f"{supportdesk_url}/users/search",
                params={"query": email},
                headers=headers,
                timeout=10
            )
            if not search_response.ok:
                log_with_route(logging.ERROR, f"Failed to lookup user: {search_response.text}")
                return False, None
            user_id = search_response.json()[0]['id']
        else:
            user_id = user_response.json()['id']

        # Now create the ticket
        ticket_data = {
            "title": f"Website Contact: {subject}",
            "group": "Wegweiser Customers",
            "customer_id": user_id,
            "article": {
                "subject": subject,
                "body": message,
                "type": "web",
                "sender": "Customer",
                "internal": False
            },
            "tags": "website_contact"
        }

        ticket_response = requests.post(
            f"{supportdesk_url}/tickets",
            json=ticket_data,
            headers=headers,
            timeout=10
        )
        
        if not ticket_response.ok:
            log_with_route(logging.ERROR, f"Zammad response: {ticket_response.status_code} - {ticket_response.text}")
            return False, None
            
        log_with_route(logging.INFO, f"Support ticket created successfully for {email}")
        return True, ticket_response.json().get('id')
        
    except requests.RequestException as e:
        log_with_route(logging.ERROR, f"Failed to create support ticket for {email}. Error: {str(e)} - Response: {e.response.text if hasattr(e, 'response') else 'No response'}", exc_info=True)
        return False, None

@contact_bp.route('/contact', methods=['POST'])
@csrf.exempt
@limiter.limit("5 per minute")
def handle_contact():
    client_ip = request.headers.get('X-Real-Ip')
    log_with_route(logging.INFO, f'Contact form submission from IP: {client_ip}')
    
    try:
        name = request.form.get('YourName')
        email = request.form.get('EmailId')
        subject = request.form.get('Subject')
        message = request.form.get('Message')

        if not all([name, email, subject, message]):
            log_with_route(logging.WARNING, f'Invalid contact form submission from {client_ip}: Missing required fields')
            return jsonify({
                'success': False,
                'message': 'All fields are required'
            }), 400

        # Create ticket using the helper function
        success, ticket_id = create_supportdesk_ticket(name, email, subject, message)
        
        if not success:
            return jsonify({
                'success': False,
                'message': 'Failed to create ticket. Please try again later.'
            }), 500

        log_with_route(logging.INFO, f'Successfully created ticket for {email}')
        return jsonify({
            'success': True,
            'message': 'Your message has been received. We will get back to you soon.'
        })

    except Exception as e:
        log_with_route(logging.ERROR, f'Error processing contact form: {str(e)}', exc_info=True)
        return jsonify({
            'success': False,
            'message': 'An unexpected error occurred. Please try again later.'
        }), 500