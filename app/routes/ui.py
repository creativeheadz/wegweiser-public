# Filepath: app/routes/ui.py
from flask import Blueprint, session, render_template, request, redirect, url_for, flash, current_app, jsonify, g
from app.utilities.app_access_role_required import role_required
from app.utilities.app_access_login_required import login_required
from app.forms.tenant_profile import TenantProfileForm
from werkzeug.utils import secure_filename
from app.utilities.notifications import create_notification
from app.forms.chat_form import ChatForm
from app.utilities.langchain_utils import generate_entity_suggestions, generate_tool_recommendations
from markupsafe import Markup
from flask import render_template_string
from app.models import TenantMetadata
from datetime import datetime, timedelta



# Utilities for device management
from app.utilities.ui_devices_printers import fetch_printers_by_device
from app.utilities.ui_devices_eventlogs import fetch_event_logs_by_device
from app.utilities.ui_devices_devicetable import get_devices_table_data
from app.utilities.ui_devices_devicedetails import get_device_details

# Utilities for wegcoin balance and AI task statuses
from app.utilities.ui_wegcoins_currencystate import get_tenant_wegcoin_balance

# Logging
from app.utilities.app_logging_helper import log_with_route
import logging

# Models and database
from app.models import db, Accounts, Tenants, Organisations, Devices, Groups, Roles, UserXOrganisation, DeviceMetadata, HealthScoreHistory
from flask_mail import Message
from app import mail, master_permission, admin_or_master_permission

# SQLAlchemy imports
from sqlalchemy import text, desc
from sqlalchemy.exc import SQLAlchemyError, IntegrityError

# Utilities
from datetime import datetime, timezone
from uuid import UUID
from flask_bcrypt import Bcrypt
from markupsafe import Markup
bcrypt = Bcrypt()

# Misc
import json
import time
import os
import secrets
import string
import uuid
from dotenv import load_dotenv



# Load environment variables
load_dotenv()

ui_bp = Blueprint('ui', __name__, url_prefix='/ui')




    
@ui_bp.route('/devices/<string:deviceuuid>/eventlog/<log_type>')
@login_required
def get_device_eventlog(deviceuuid, log_type):
    try:
        deviceuuid = UUID(deviceuuid)
    except ValueError:
        log_with_route(logging.ERROR, "Invalid device UUID")
        return "Invalid device UUID", 400

    tenantuuid = session.get('tenant_uuid')
    if not tenantuuid:
        log_with_route(logging.ERROR, "No tenant_uuid found in session")
        return "Unauthorized access", 403

    # Support both event logs and security audit types
    valid_log_types = ['eventsFiltered-Application', 'eventsFiltered-Security', 'eventsFiltered-System', 'lynis-audit']
    if log_type not in valid_log_types:
        log_with_route(logging.ERROR, f"Invalid log type: {log_type}")
        return "Invalid log type", 400

    query = text("""
    SELECT dm.ai_analysis, dm.created_at, dm.score
    FROM public.devicemetadata dm
    JOIN public.devices d ON dm.deviceuuid = d.deviceuuid
    WHERE dm.deviceuuid = :deviceuuid
      AND d.tenantuuid = :tenantuuid
      AND dm.metalogos_type = :log_type
    ORDER BY dm.created_at DESC
    LIMIT 1
    """)

    try:
        result = db.session.execute(query, {'deviceuuid': str(deviceuuid), 'tenantuuid': tenantuuid, 'log_type': log_type})
        row = result.fetchone()

        if row:
            analysis, created_at, score = row
            readable_time = datetime.fromtimestamp(created_at).strftime('%Y-%m-%d %H:%M:%S')

            # Format output based on log type
            if log_type == 'lynis-audit':
                # For Lynis audits, include the security score prominently
                score_color = 'success' if score >= 80 else 'warning' if score >= 60 else 'danger'
                score_html = f"""
                <div class="alert alert-info mb-3">
                    <div class="row align-items-center">
                        <div class="col-auto">
                            <h5 class="mb-0">Security Audit Report</h5>
                        </div>
                        <div class="col-auto ms-auto">
                            <span class="badge bg-{score_color} fs-6">Security Score: {score}/100</span>
                        </div>
                    </div>
                </div>
                <p><small class="text-muted"><i class="fas fa-clock me-1"></i>Report Generated: {readable_time}</small></p>
                """
                eventlog_html = score_html + Markup(analysis)
            else:
                # For event logs, use the original format
                eventlog_html = f"<p><small class='text-muted'>Timestamp: {readable_time}</small></p>" + Markup(analysis)

            log_with_route(logging.DEBUG, f"Fetched {log_type} for device {deviceuuid}")
            return eventlog_html
        else:
            if log_type == 'lynis-audit':
                return Markup('<div class="alert alert-warning"><i class="fas fa-info-circle me-2"></i>No security audit available yet. Schedule a Lynis audit to see security analysis.</div>')
            else:
                log_with_route(logging.DEBUG, f"No event logs available for device {deviceuuid} and log type {log_type}")
                return Markup('<p>No event logs available</p>')
    except Exception as e:
        log_with_route(logging.ERROR, f"Error fetching {log_type}: {str(e)}")
        return f"An error occurred while fetching {log_type}: {str(e)}", 500





def send_welcome_email(email, password):
    msg = Message("Welcome to Wegweiser",
                  recipients=[email])
    msg.body = f"""
    Welcome to Wegweiser!

    Your account has been created successfully.
    Here are your login details:

    Email: {email}
    Password: {password}

    Please log in and change your password immediately.

    Best regards,
    The Wegweiser Team
    """
    mail.send(msg)


def generate_secure_password(length=16):
    alphabet = string.ascii_letters + string.digits + string.punctuation
    password = ''.join(secrets.choice(alphabet) for i in range(length))
    return password

@ui_bp.route('/create_user', methods=['POST'])
@login_required
@admin_or_master_permission().require(http_exception=403)
def create_user():
    data = request.form
    firstname = data.get('name').split()[0]
    lastname = ' '.join(data.get('name').split()[1:]) if len(data.get('name').split()) > 1 else ''
    email = data.get('email')
    tenant_uuid = session.get('tenant_uuid')
    
    log_with_route(logging.INFO, f"Request to create master user: {email}...")
    
    if not all([firstname, email, tenant_uuid]):
        log_with_route(logging.ERROR, "Required fields missing when creating user")
        flash('All fields are required', 'error')
        return redirect(url_for('ui.get_tenants_overview'))
    
    tenant = Tenants.query.filter_by(tenantuuid=tenant_uuid).first()
    if not tenant:
        log_with_route(logging.ERROR, "Tenant not found during user creation")
        flash('Tenant not found', 'error')
        return redirect(url_for('ui.get_tenants_overview'))
    
    password = generate_secure_password()
    hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
    
    role_obj = Roles.query.filter_by(rolename='master').first()
    if not role_obj:
        log_with_route(logging.ERROR, "Master role not found during user creation")
        flash('Master role not found', 'error')
        return redirect(url_for('ui.get_tenants_overview'))
    
    user_uuid = str(uuid.uuid4())
    new_user = Accounts(
        useruuid=user_uuid,
        firstname=firstname,
        lastname=lastname,
        companyname=tenant.tenantname,
        companyemail=email,
        password=hashed_password,
        role_id=role_obj.roleuuid,
        tenantuuid=tenant_uuid
    )
    
    try:
        db.session.add(new_user)
        
        # Add associations for all organizations in the tenant
        orgs = Organisations.query.filter_by(tenantuuid=tenant_uuid).all()
        for org in orgs:
            user_org = UserXOrganisation(useruuid=new_user.useruuid, orguuid=org.orguuid)
            db.session.add(user_org)
            log_with_route(logging.DEBUG, f"Adding user-org association: user={new_user.useruuid}, org={org.orguuid}")
        
        db.session.commit()
        log_with_route(logging.INFO, f"New master user created: {new_user.useruuid}")
        
        try:
            send_welcome_email(email, password)
            log_with_route(logging.INFO, f"Welcome email sent to: {email}")
        except Exception as mail_error:
            log_with_route(logging.ERROR, f"Failed to send welcome email: {str(mail_error)}")
        
        flash('Master user created successfully. A welcome email has been sent with login instructions.', 'success')
        return redirect(url_for('ui.get_tenants_overview'))
    
    except SQLAlchemyError as e:
        db.session.rollback()
        log_with_route(logging.ERROR, f"Database error occurred: {str(e)}")
        flash(f'An error occurred while creating the user: {str(e)}', 'error')
        return redirect(url_for('ui.get_tenants_overview'))
    except Exception as e:
        db.session.rollback()
        log_with_route(logging.ERROR, f"Unexpected error: {str(e)}")
        flash('An unexpected error occurred. Please try again.', 'error')
        return redirect(url_for('ui.get_tenants_overview'))




@ui_bp.route('/delete_user', methods=['POST'])
@login_required
@admin_or_master_permission().require(http_exception=403)
def delete_user():
    data = request.json
    user_id = data.get('user_id')
    current_user = Accounts.query.get(session.get('user_id'))
    
    if not user_id:
        log_with_route(logging.ERROR, "User ID is required for deletion")
        return jsonify({'success': False, 'error': 'User ID is required'}), 400

    user = Accounts.query.get(user_id)
    if not user:
        log_with_route(logging.ERROR, f"User with ID {user_id} not found")
        return jsonify({'success': False, 'error': 'User not found'}), 404

    # Prevent self-deletion or deletion of admin/master by non-admin
    if user_id == current_user.useruuid or (user.role.rolename in ['admin', 'master'] and current_user.role.rolename != 'admin'):
        log_with_route(logging.ERROR, f"Unauthorized deletion attempt by user {current_user.useruuid}")
        return jsonify({'success': False, 'error': 'You cannot delete this user'}), 403

    try:
        # Delete associated UserXOrganisation entries
        UserXOrganisation.query.filter_by(useruuid=user_id).delete()
        
        # Delete the user
        db.session.delete(user)
        db.session.commit()
        log_with_route(logging.INFO, f"User with ID {user_id} deleted successfully")
        return jsonify({'success': True, 'message': 'User deleted successfully'}), 200
    except SQLAlchemyError as e:
        db.session.rollback()
        log_with_route(logging.ERROR, f"Database error occurred while deleting user: {str(e)}")
        return jsonify({'success': False, 'error': f"Database error: {str(e)}"}), 500
    except Exception as e:
        db.session.rollback()
        log_with_route(logging.ERROR, f"Unexpected error occurred while deleting user: {str(e)}")
        return jsonify({'success': False, 'error': f"An unexpected error occurred: {str(e)}"}), 500




@ui_bp.route('/send-test-email')
def send_test_email():
    msg = Message(
        "Test Email",
        sender=current_app.config['MAIL_DEFAULT_SENDER'],
        recipients=["andreitv@gmail.com"]  # replace with a valid recipient email
    )
    try:
        mail.send(msg)
        log_with_route(logging.INFO, "Test email sent successfully")
        return "Email sent successfully!"
    except Exception as e:
        log_with_route(logging.ERROR, f"Failed to send test email: {str(e)}")
        return str(e), 500



def _get_event_summary(metalogos):
    """Extract key summary information from metalogos"""
    if isinstance(metalogos, str):
        metalogos = json.loads(metalogos)
    
    return {
        'error_count': sum(1 for event in metalogos['Sources']['TopEvents'] 
                          if event.get('Level') == 'ERROR'),
        'warning_count': sum(1 for event in metalogos['Sources']['TopEvents'] 
                           if event.get('Level') == 'WARNING'),
        'critical_count': sum(1 for event in metalogos['Sources']['TopEvents'] 
                            if event.get('Level') == 'CRITICAL'),
        'top_events': [
            {
                **event,
                'Level': event.get('Level', 'N/A')  # Ensure 'Level' has a default value
            }
            for event in metalogos['Sources']['TopEvents'][:50]
        ]
    }


        

@ui_bp.route('/device/<uuid:device_uuid>/health_history')
@login_required
def get_device_health_history(device_uuid):
    """
    Get the health score history for a specific device.
    
    Args:
        device_uuid: UUID of the device
        
    Returns:
        JSON response containing the device's health score history data
    """
    try:
        # Verify device exists and get current health score
        device = Devices.query.get_or_404(device_uuid)
        
        # Get historical health scores
        history = HealthScoreHistory.query.filter_by(
            entity_type='device',
            entity_uuid=device_uuid
        ).order_by(HealthScoreHistory.timestamp).all()
        
        # Format data for response
        data = [{'x': h.timestamp.isoformat(), 'y': h.health_score} for h in history]
        
        # Add current health score if available
        if device.health_score is not None:
            data.append({
                'x': datetime.utcnow().isoformat(),
                'y': device.health_score
            })
            
        return jsonify(data)
        
    except ValueError as e:
        return jsonify({'error': str(e)}), 404
    except Exception as e:
        log_with_route(
            logging.ERROR,
            f"Error in get_device_health_history: {str(e)}",
            exc_info=True
        )
        return jsonify({'error': 'An unexpected error occurred'}), 500