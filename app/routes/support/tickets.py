# Filepath: app/routes/support/tickets.py
from flask import Blueprint, render_template, request, redirect, url_for, flash, session, current_app
import requests
import logging
import os
from app.utilities.app_logging_helper import log_with_route
from app.utilities.app_access_login_required import login_required
from app import get_secret
from app.models import db, Accounts
from datetime import datetime

tickets_bp = Blueprint('tickets_bp', __name__)

def get_zammad_headers():
    """Get headers for Zammad API requests with token authentication"""
    try:
        # Retrieve token from Azure Key Vault
        token = get_secret('SUPPORTDESKAPITOKEN')
        
        # Log success but not the actual token for security
        log_with_route(logging.INFO, f"Using Zammad API token")
        
        if not token:
            log_with_route(logging.ERROR, "No Zammad API token found in environment or secrets")
            raise ValueError("Missing Zammad API token")
            
        return {
            "Authorization": f"Token token={token}",
            "Content-Type": "application/json"
        }
    except Exception as e:
        log_with_route(logging.ERROR, f"Error retrieving Zammad token: {str(e)}")
        # Return basic headers so the request can still be attempted
        return {"Content-Type": "application/json"}

def test_zammad_connection():
    """Test if the Zammad connection is working properly"""
    try:
        supportdesk_url = "https://support.oldforge.tech/api/v1"
        headers = get_zammad_headers()
        
        # Try a simple request to test authentication
        response = requests.get(
            f"{supportdesk_url}/users/me",
            headers=headers,
            timeout=10
        )
        
        if response.ok:
            log_with_route(logging.INFO, "Zammad connection test successful")
            return True
        else:
            log_with_route(logging.ERROR, f"Zammad connection test failed: {response.status_code} - {response.text}")
            return False
    except Exception as e:
        log_with_route(logging.ERROR, f"Zammad connection test error: {str(e)}")
        return False

def get_zammad_priority_value(priority_string):
    """Convert priority string to the format expected by Zammad API"""
    log_with_route(logging.DEBUG, f"Raw priority string from form: '{priority_string}'")
    
    # Fix mapping to align with the form values
    priority_map = {
        "3 low": 1,    # ID 1 in Zammad is low priority
        "2 normal": 2, # ID 2 in Zammad is normal priority
        "1 high": 3    # ID 3 in Zammad is high priority
    }
    
    # Return mapped value or default to 2 (normal) if not found
    priority_value = priority_map.get(priority_string, 2)
    log_with_route(logging.INFO, f"Mapped priority '{priority_string}' to ID: {priority_value}")
    
    return priority_value

@tickets_bp.route('/support', methods=['GET'])
@login_required
def support_dashboard():
    """Display user's support tickets and form to create new ones"""
    try:
        # Get current user info
        user_id = session.get('user_id')
        user = db.session.query(Accounts).filter_by(useruuid=user_id).first()
        
        if not user:
            flash('User information not found.', 'danger')
            return redirect(url_for('dashboard_bp.dashboard'))
        
        # Test Zammad connection before proceeding
        if not test_zammad_connection():
            flash('Unable to connect to the support system. Please try again later.', 'warning')
            return render_template('support/tickets.html', tickets=[], user=user, connection_error=True)
        
        # Get user's tickets from Zammad
        supportdesk_url = "https://support.oldforge.tech/api/v1"
        headers = get_zammad_headers()
        
        # First find the user in Zammad by email
        search_response = requests.get(
            f"{supportdesk_url}/users/search",
            params={"query": user.companyemail},
            headers=headers,
            timeout=10
        )
        
        tickets = []
        if search_response.ok and search_response.json():
            zammad_user_id = search_response.json()[0]['id']
            log_with_route(logging.INFO, f"Found Zammad user ID: {zammad_user_id}")
            
            # Get all tickets with expand=true to get more information
            all_tickets_response = requests.get(
                f"{supportdesk_url}/tickets?expand=true&limit=50",
                headers=headers,
                timeout=10
            )
            
            if all_tickets_response.ok:
                all_tickets = all_tickets_response.json()
                log_with_route(logging.INFO, f"Retrieved {len(all_tickets)} tickets from Zammad")
                
                # Filter tickets where our user is either customer, owner, or created_by
                user_tickets = []
                for ticket in all_tickets:
                    # Check if user is customer (by ID)
                    if ticket.get('customer_id') == zammad_user_id:
                        user_tickets.append(ticket)
                        log_with_route(logging.INFO, f"Found ticket #{ticket['number']} where user is customer")
                    # Or check if user is customer (by email from expanded property)
                    elif ticket.get('customer') == user.companyemail:
                        user_tickets.append(ticket)
                        log_with_route(logging.INFO, f"Found ticket #{ticket['number']} where user is customer (by email)")
                    # Or check if user created the ticket
                    elif ticket.get('created_by_id') == zammad_user_id or ticket.get('created_by') == user.companyemail:
                        user_tickets.append(ticket)
                        log_with_route(logging.INFO, f"Found ticket #{ticket['number']} where user is creator")
                    # Or check if user owns the ticket
                    elif ticket.get('owner_id') == zammad_user_id or ticket.get('owner') == user.companyemail:
                        user_tickets.append(ticket)
                        log_with_route(logging.INFO, f"Found ticket #{ticket['number']} where user is owner")
                
                log_with_route(logging.INFO, f"Found {len(user_tickets)} tickets associated with user {user.companyemail}")
                
                # Format timestamps and add to tickets list
                for ticket in user_tickets:
                    # Format created_at timestamp
                    if 'created_at' in ticket:
                        created_at = datetime.fromisoformat(ticket['created_at'].replace('Z', '+00:00'))
                        ticket['formatted_date'] = created_at.strftime('%Y-%m-%d %H:%M')
                    
                    tickets.append(ticket)
                
            else:
                log_with_route(logging.ERROR, f"Failed to retrieve tickets: {all_tickets_response.status_code} - {all_tickets_response.text}")
        else:
            log_with_route(logging.WARNING, f"No Zammad user found for email: {user.companyemail}")
        
        return render_template('support/tickets.html', tickets=tickets, user=user, connection_error=False)
    
    except Exception as e:
        log_with_route(logging.ERROR, f"Error retrieving support tickets: {str(e)}", exc_info=True)
        flash('An error occurred while retrieving support tickets.', 'danger')
        return render_template('support/tickets.html', tickets=[], user=user if 'user' in locals() else None, connection_error=True)

@tickets_bp.route('/support/create', methods=['POST'])
@login_required
def create_ticket():
    """Create a new support ticket in Zammad"""
    try:
        # Get form data
        subject = request.form.get('subject')
        body = request.form.get('body')
        priority_string = request.form.get('priority', '2 normal')
        
        # Map the priority string to the proper value expected by Zammad
        priority = get_zammad_priority_value(priority_string)
        log_with_route(logging.INFO, f"Priority selected: {priority_string}, mapped to: {priority}")
        
        if not subject or not body:
            flash('Please provide both subject and description.', 'danger')
            return redirect(url_for('tickets_bp.support_dashboard'))
        
        # Get current user info
        user_id = session.get('user_id')
        user = db.session.query(Accounts).filter_by(useruuid=user_id).first()
        
        if not user:
            flash('User information not found.', 'danger')
            return redirect(url_for('tickets_bp.support_dashboard'))
        
        # Test Zammad connection before proceeding
        if not test_zammad_connection():
            flash('Unable to connect to the support system. Please try again later.', 'warning')
            return redirect(url_for('tickets_bp.support_dashboard'))
        
        # Create ticket in Zammad
        supportdesk_url = "https://support.oldforge.tech/api/v1"
        headers = get_zammad_headers()
        
        # Find user in Zammad
        search_response = requests.get(
            f"{supportdesk_url}/users/search",
            params={"query": user.companyemail},
            headers=headers,
            timeout=10
        )
        
        # Log the response for debugging
        log_with_route(logging.INFO, f"User search response: {search_response.status_code} - {search_response.text[:200]}")
        
        zammad_user_id = None
        if search_response.ok and search_response.json():
            zammad_user_id = search_response.json()[0]['id']
            log_with_route(logging.INFO, f"Found existing Zammad user with ID: {zammad_user_id}")
        else:
            # User doesn't exist in Zammad, create them
            log_with_route(logging.INFO, f"Creating new Zammad user for {user.companyemail}")
            
            # Create a secure password for the user
            import secrets
            import string
            password = ''.join(secrets.choice(string.ascii_letters + string.digits) for i in range(12))
            
            user_data = {
                "firstname": user.firstname,
                "lastname": user.lastname,
                "email": user.companyemail,
                "login": user.companyemail,
                "password": password,
                "roles": ["Customer"]
            }
            
            log_with_route(logging.INFO, f"Zammad user creation request: {user_data}")
            
            user_response = requests.post(
                f"{supportdesk_url}/users",
                json=user_data,
                headers=headers,
                timeout=10
            )
            
            if not user_response.ok:
                log_with_route(logging.ERROR, f"Failed to create Zammad user: {user_response.status_code} - {user_response.text}")
                flash('Failed to create support ticket. Support system is currently unavailable.', 'danger')
                return redirect(url_for('tickets_bp.support_dashboard'))
                
            zammad_user_id = user_response.json()['id']
            log_with_route(logging.INFO, f"Created new Zammad user with ID: {zammad_user_id}")
        
        # Create the actual ticket
        ticket_data = {
            "title": subject,
            "group": "Wegweiser Customers",
            "customer_id": zammad_user_id,
            "priority_id": priority,  # Use priority_id instead of priority with the numeric value
            "article": {
                "subject": subject,
                "body": body,
                "type": "web",
                "sender": "Customer",
                "internal": False
            }
        }
        
        log_with_route(logging.INFO, f"Creating ticket with data: {ticket_data}")
        
        ticket_response = requests.post(
            f"{supportdesk_url}/tickets",
            json=ticket_data,
            headers=headers,
            timeout=10
        )
        
        if ticket_response.ok:
            log_with_route(logging.INFO, f"Ticket created successfully with ID: {ticket_response.json().get('id')}")
            flash('Support ticket created successfully.', 'success')
        else:
            log_with_route(logging.ERROR, f"Failed to create ticket: {ticket_response.status_code} - {ticket_response.text}")
            flash('Failed to create support ticket.', 'danger')
        
        return redirect(url_for('tickets_bp.support_dashboard'))
    
    except Exception as e:
        log_with_route(logging.ERROR, f"Error creating support ticket: {str(e)}", exc_info=True)
        flash('An error occurred while creating support ticket.', 'danger')
        return redirect(url_for('tickets_bp.support_dashboard'))

@tickets_bp.route('/support/view/<int:ticket_id>', methods=['GET'])
@login_required
def view_ticket(ticket_id):
    """View a specific ticket and its articles/replies"""
    try:
        # Get current user info
        user_id = session.get('user_id')
        user = db.session.query(Accounts).filter_by(useruuid=user_id).first()
        
        if not user:
            flash('User information not found.', 'danger')
            return redirect(url_for('dashboard_bp.dashboard'))
        
        # Get ticket details from Zammad
        supportdesk_url = "https://support.oldforge.tech/api/v1"
        headers = get_zammad_headers()
        
        # Get ticket details
        ticket_response = requests.get(
            f"{supportdesk_url}/tickets/{ticket_id}",
            headers=headers,
            timeout=10
        )
        
        if not ticket_response.ok:
            flash('Ticket not found or access denied.', 'danger')
            return redirect(url_for('tickets_bp.support_dashboard'))
            
        ticket = ticket_response.json()
        
        # Get ticket articles (conversation)
        articles_response = requests.get(
            f"{supportdesk_url}/ticket_articles/by_ticket/{ticket_id}",
            headers=headers,
            timeout=10
        )
        
        articles = []
        if articles_response.ok:
            articles = articles_response.json()
            
            # Format date for each article
            for article in articles:
                if 'created_at' in article:
                    created_at = datetime.fromisoformat(article['created_at'].replace('Z', '+00:00'))
                    article['formatted_date'] = created_at.strftime('%Y-%m-%d %H:%M')
        
        return render_template('support/view_ticket.html', ticket=ticket, articles=articles, user=user)
    
    except Exception as e:
        log_with_route(logging.ERROR, f"Error viewing ticket: {str(e)}", exc_info=True)
        flash('An error occurred while retrieving ticket details.', 'danger')
        return redirect(url_for('tickets_bp.support_dashboard'))

@tickets_bp.route('/support/reply/<int:ticket_id>', methods=['POST'])
@login_required
def reply_to_ticket(ticket_id):
    """Add a reply to an existing ticket"""
    try:
        # Get form data
        body = request.form.get('reply')
        
        if not body:
            flash('Reply cannot be empty.', 'danger')
            return redirect(url_for('tickets_bp.view_ticket', ticket_id=ticket_id))
        
        # Create reply in Zammad
        supportdesk_url = "https://support.oldforge.tech/api/v1"
        headers = get_zammad_headers()
        
        article_data = {
            "ticket_id": ticket_id,
            "body": body,
            "type": "web",
            "sender": "Customer",
            "internal": False
        }
        
        reply_response = requests.post(
            f"{supportdesk_url}/ticket_articles",
            json=article_data,
            headers=headers,
            timeout=10
        )
        
        if reply_response.ok:
            flash('Reply added successfully.', 'success')
        else:
            log_with_route(logging.ERROR, f"Failed to add reply: {reply_response.text}")
            flash('Failed to add reply.', 'danger')
        
        return redirect(url_for('tickets_bp.view_ticket', ticket_id=ticket_id))
    
    except Exception as e:
        log_with_route(logging.ERROR, f"Error replying to ticket: {str(e)}", exc_info=True)
        flash('An error occurred while adding reply.', 'danger')
        return redirect(url_for('tickets_bp.view_ticket', ticket_id=ticket_id))