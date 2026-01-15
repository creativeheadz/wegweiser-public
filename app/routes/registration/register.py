# Filepath: app/routes/registration/register.py
import re
import requests
import uuid
import time
from datetime import datetime
from flask import Blueprint, request, render_template, redirect, url_for, session, current_app, flash
from app.models import db, Accounts, Tenants, Organisations, ServerCore, Groups, bcrypt, Roles, Messages, Conversations
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import DataRequired, Email, Length, EqualTo
from flask_wtf.csrf import CSRFProtect
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from threading import Thread
import threading
import logging
from app.utilities.app_logging_helper import log_with_route
from app.forms.register import RegistrationForm
from app.utilities.email_verification import create_verification_token, send_verification_email

register_bp = Blueprint('register_bp', __name__)
csrf = CSRFProtect()

limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["5 per minute"]
)

# In-memory storage for IP-based registration tracking (consider Redis for production)
_registration_tracker = {}
_tracker_lock = threading.Lock()

def get_client_ip():
    if request.headers.get('X-Forwarded-For'):
        return request.headers.get('X-Forwarded-For').split(',')[0].strip()
    return request.remote_addr

def check_ip_registration_limit(ip_address, max_registrations=2, window_hours=24):
    """
    Check if an IP has exceeded registration limits.
    Returns: (allowed: bool, count: int, message: str)
    """
    with _tracker_lock:
        current_time = time.time()
        window_start = current_time - (window_hours * 3600)
        
        # Clean up old entries
        expired_ips = [ip for ip, timestamps in _registration_tracker.items() 
                      if all(ts < window_start for ts in timestamps)]
        for ip in expired_ips:
            del _registration_tracker[ip]
        
        # Get recent registrations for this IP
        recent_registrations = _registration_tracker.get(ip_address, [])
        recent_registrations = [ts for ts in recent_registrations if ts >= window_start]
        
        if len(recent_registrations) >= max_registrations:
            return False, len(recent_registrations), f"Maximum {max_registrations} registrations per {window_hours} hours exceeded"
        
        return True, len(recent_registrations), "OK"

def record_ip_registration(ip_address):
    """Record a successful registration from an IP address"""
    with _tracker_lock:
        if ip_address not in _registration_tracker:
            _registration_tracker[ip_address] = []
        _registration_tracker[ip_address].append(time.time())
        log_with_route(logging.INFO, f"Recorded registration from IP {ip_address}, total: {len(_registration_tracker[ip_address])}")

def verify_recaptcha_v3(token):
    if not token:
        log_with_route(logging.ERROR, "No reCAPTCHA token provided")
        return False, 0, {"error": "No token provided"}
        
    secret_key = current_app.config['RECAPTCHA_PRIVATE_KEY']
    if not secret_key:
        log_with_route(logging.ERROR, "No reCAPTCHA secret key configured")
        return False, 0, {"error": "No secret key"}
        
    payload = {
        'secret': secret_key,
        'response': token
    }
    
    try:
        response = requests.post('https://www.google.com/recaptcha/api/siteverify', data=payload)
        result = response.json()
        log_with_route(logging.INFO, f"reCAPTCHA verification response: {result}")
        return result.get('success'), result.get('score', 0), result
    except Exception as e:
        log_with_route(logging.ERROR, f"reCAPTCHA verification failed with error: {str(e)}")
        return False, 0, {"error": str(e)}

def create_supportdesk_user(firstname, lastname, email, password, company):
    """Create a Zammad user, first checking if they already exist."""
    try:
        from app import get_secret
        
        supportdesk_url = "https://support.oldforge.tech/api/v1"
        supportdesk_token = get_secret('SUPPORTDESKAPITOKEN')
        
        headers = {
            "Authorization": f"Token token={supportdesk_token}",
            "Content-Type": "application/json"
        }

        # First try to find if user exists
        search_response = requests.get(
            f"{supportdesk_url}/users/search",
            params={"query": email},
            headers=headers,
            timeout=10
        )

        if search_response.ok and search_response.json():
            user_id = search_response.json()[0]['id']
            log_with_route(logging.INFO, f"User {email} already exists in Zammad")
        else:
            # Create new user
            user_data = {
                "firstname": firstname,
                "lastname": lastname,
                "email": email,
                "login": email,
                "password": password,
                "roles": ["Customer"]
            }
            
            user_response = requests.post(
                f"{supportdesk_url}/users",
                json=user_data,
                headers=headers,
                timeout=10
            )
            
            if not user_response.ok:
                log_with_route(logging.ERROR, f"Failed to create Zammad user: {user_response.text}")
                return False
                
            user_id = user_response.json()['id']

        # Create ticket for new registration
        ticket_data = {
            "title": f"New Tenant Registration: {company}",
            "group": "Wegweiser Customers",
            "customer_id": user_id,
            "article": {
                "subject": "New Tenant Registration",
                "body": f"""New tenant registration completed:
                
Company: {company}
Contact: {firstname} {lastname}
Email: {email}

Please review and setup any necessary configurations.""",
                "type": "web",
                "sender": "System",
                "internal": True
            },
            "tags": "new_tenant"
        }

        ticket_response = requests.post(
            f"{supportdesk_url}/tickets",
            json=ticket_data,
            headers=headers,
            timeout=10
        )
        
        if not ticket_response.ok:
            log_with_route(logging.ERROR, f"Failed to create registration ticket: {ticket_response.text}")
            
        log_with_route(logging.INFO, f"Support desk setup completed for {email}")
        return True
        
    except Exception as e:
        log_with_route(logging.ERROR, f"Error in support desk setup for {email}: {str(e)}", exc_info=True)
        return False

def create_helpdesk_user_async(firstname, lastname, companyemail, password, companyname):
    """Async wrapper that won't fail registration if helpdesk is unavailable."""
    try:
        supportdesk_success = create_supportdesk_user(firstname, lastname, companyemail, password, companyname)
        if not supportdesk_success:
            log_with_route(logging.WARNING, f"Helpdesk setup failed for {companyemail}, but local registration was successful.")
    except Exception as e:
        log_with_route(logging.ERROR, f"Error during helpdesk setup for {companyemail}: {e}", exc_info=True)

@register_bp.route('/register', methods=['GET', 'POST'])
@limiter.limit("5 per minute")
def register():
    form = RegistrationForm()

    if request.method == 'POST':
        client_ip = get_client_ip()
        
        # Check honeypot field FIRST (anti-bot trap)
        honeypot = request.form.get('website', '')
        if honeypot:
            # Bot detected - honeypot field was filled
            log_with_route(logging.WARNING, f"HONEYPOT BLOCKED: Bot detected from {client_ip} - honeypot value: '{honeypot[:50]}'")
            flash('Registration failed. Please try again.', 'danger')
            return render_template('register.html', form=form)
        
        # Check IP-based registration limits
        allowed, reg_count, limit_message = check_ip_registration_limit(client_ip, max_registrations=2, window_hours=24)
        if not allowed:
            # Extract form data even for blocked attempts (for analysis)
            blocked_data = {
                'email': request.form.get('companyemail', 'not_provided')[:100],
                'company': request.form.get('companyname', 'not_provided')[:100],
                'name': f"{request.form.get('firstname', '')} {request.form.get('lastname', '')}".strip()[:100]
            }
            flash('Too many registration attempts from your IP address. Please try again later or contact support.', 'danger')
            log_with_route(logging.WARNING, f"IP RATE LIMIT BLOCKED: {client_ip} - {limit_message} (count: {reg_count}) - Attempted data: {blocked_data}")
            return render_template('register.html', form=form)
        
        recaptcha_token = request.form.get('g-recaptcha-response')
        success, score, recaptcha_result = verify_recaptcha_v3(recaptcha_token)

        # Enhanced bot detection - analyze request headers
        user_agent = request.headers.get('User-Agent', 'Unknown')
        platform_header = request.headers.get('Sec-Ch-Ua-Platform', '').strip('"')
        
        # Detect header inconsistencies (OS mismatch between User-Agent and Sec-Ch-Ua-Platform)
        bot_indicators = []
        if platform_header and user_agent:
            ua_lower = user_agent.lower()
            platform_lower = platform_header.lower()
            
            # Check for OS mismatches
            if ('windows' in ua_lower and 'linux' in platform_lower) or \
               ('mac' in ua_lower and 'linux' in platform_lower) or \
               ('linux' in ua_lower and ('windows' in platform_lower or 'macos' in platform_lower)):
                bot_indicators.append(f"OS_MISMATCH(UA:{user_agent[:50]},Platform:{platform_header})")
        
        # Extract and sanitize form data for logging (before validation)
        submitted_data = {
            'firstname': request.form.get('firstname', 'not_provided')[:50],
            'lastname': request.form.get('lastname', 'not_provided')[:50],
            'companyname': request.form.get('companyname', 'not_provided')[:100],
            'companyemail': request.form.get('companyemail', 'not_provided')[:100],
            'has_password': bool(request.form.get('password'))
        }
        
        # Log comprehensive registration attempt details INCLUDING payload
        log_details = {
            'ip': client_ip,
            'score': score,
            'recaptcha_success': success,
            'user_agent': user_agent[:100],
            'platform': platform_header,
            'bot_indicators': bot_indicators if bot_indicators else 'none',
            'submitted_data': submitted_data
        }
        log_with_route(logging.INFO, f"Registration attempt: {log_details}")

        # Layered security approach: reCAPTCHA is a soft warning, not a hard block
        # If reCAPTCHA fails BUT other checks pass, we allow registration with email verification as final gate
        recaptcha_suspicious = not success or score < 0.5
        
        if recaptcha_suspicious:
            # Log the low score but don't block immediately
            log_with_route(logging.WARNING, f"reCAPTCHA LOW SCORE (allowing with caution): {client_ip}: score={score}, bot_indicators={bot_indicators}, data={submitted_data}")
            
            # If BOTH reCAPTCHA fails AND we have other bot indicators, then block
            if bot_indicators:
                flash('Registration failed security validation. Please try again or contact support.', 'danger')
                log_with_route(logging.WARNING, f"reCAPTCHA + BOT INDICATORS BLOCKED: {client_ip}: score={score}, indicators={bot_indicators}")
                return redirect(url_for('register_bp.register'))
            
            # Otherwise, allow but require email verification (which is already enforced)
            log_with_route(logging.INFO, f"Low reCAPTCHA score allowed (no other bot indicators): {client_ip} - will require email verification")

        if form.validate_on_submit():
            firstname = form.firstname.data
            lastname = form.lastname.data
            companyname = form.companyname.data
            companyemail = form.companyemail.data
            password = form.password.data

            log_with_route(logging.INFO, f'Request to register from {client_ip}: {companyemail}...')

            Session = sessionmaker(bind=db.engine)
            db_session = Session()

            try:
                # Check if the tenant exists, otherwise create a new tenant
                tenant = db_session.query(Tenants).filter_by(tenantname=companyname).first()
                is_new_tenant = False
                if tenant:
                    tenant_uuid = tenant.tenantuuid
                else:
                    tenant_uuid = str(uuid.uuid4())
                    new_tenant = Tenants(
                        tenantuuid=tenant_uuid,
                        tenantname=companyname,
                        created_at=time.time()
                    )
                    db_session.add(new_tenant)
                    is_new_tenant = True

                # Hash the password
                hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')

                # Determine the appropriate role: 'master' for first user in tenant, 'user' for others
                if is_new_tenant:
                    # First user in a new tenant gets 'master' role
                    role = db_session.query(Roles).filter_by(rolename='master').first()
                    log_with_route(logging.INFO, f"Assigning 'master' role to first user in new tenant: {companyname}")
                else:
                    # Check if this is actually the first user in an existing tenant (edge case)
                    existing_users_count = db_session.query(Accounts).filter_by(tenantuuid=tenant_uuid).count()
                    if existing_users_count == 0:
                        # No users exist in this tenant, make this user the master
                        role = db_session.query(Roles).filter_by(rolename='master').first()
                        log_with_route(logging.INFO, f"Assigning 'master' role to first user in existing tenant with no users: {companyname}")
                    else:
                        # Additional users in existing tenant get 'user' role
                        role = db_session.query(Roles).filter_by(rolename='user').first()
                        log_with_route(logging.INFO, f"Assigning 'user' role to additional user in existing tenant: {companyname}")

                if not role:
                    log_with_route(logging.ERROR, f"Role not found during registration for tenant: {companyname}")
                    flash('System error: Role configuration issue. Please contact support.', 'danger')
                    return render_template('register.html', form=form)

                # Create a new user (unverified)
                user_uuid = str(uuid.uuid4())
                new_user = Accounts(
                    useruuid=user_uuid,
                    firstname=firstname,
                    lastname=lastname,
                    companyname=companyname,
                    companyemail=companyemail,
                    password=hashed_password,
                    role_id=role.roleuuid,
                    tenantuuid=tenant_uuid,
                    email_verified=False,  # User starts as unverified
                    registration_ip=client_ip  # Track registration IP for security
                )
                db_session.add(new_user)
                db_session.commit()

                # Create an organization for the tenant
                org_uuid = str(uuid.uuid4())
                new_organisation = Organisations(
                    orguuid=org_uuid,
                    orgname=companyname,
                    tenantuuid=tenant_uuid
                )
                db_session.add(new_organisation)

                # Create a default group for the organization
                group_uuid = str(uuid.uuid4())
                new_group = Groups(
                    groupuuid=group_uuid,
                    groupname='Default',
                    orguuid=org_uuid,
                    tenantuuid=tenant_uuid
                )
                db_session.add(new_group)

                db_session.commit()

                # Post-registration actions for new tenants
                if not tenant:  # Only for newly created tenants
                    # 1. Assign 250 wegcoins as welcome bonus
                    try:
                        from app.models.wegcoin_transaction import WegcoinTransaction

                        # Update the tenant's wegcoin balance directly in the same session
                        new_tenant.available_wegcoins = 250

                        # Create the transaction record
                        wegcoin_transaction = WegcoinTransaction(
                            tenantuuid=tenant_uuid,
                            amount=250,
                            transaction_type='registration_bonus',
                            description='Welcome bonus for new tenant registration'
                        )
                        db_session.add(wegcoin_transaction)
                        db_session.commit()

                        log_with_route(logging.INFO, f"Assigned 250 wegcoins welcome bonus to new tenant: {companyname}")
                    except Exception as e:
                        log_with_route(logging.ERROR, f"Failed to assign wegcoins to new tenant {companyname}: {e}")
                        db_session.rollback()

                    # 2. Create welcome notification (using separate session to avoid conflicts)
                    try:
                        # Use the global db.session for notifications to avoid session conflicts
                        # Create a conversation for the welcome message
                        welcome_conversation = Conversations(
                            conversationuuid=str(uuid.uuid4()),
                            tenantuuid=tenant_uuid,
                            deviceuuid=None,  # Not a device conversation
                            entityuuid=tenant_uuid,
                            entity_type='tenant'
                        )
                        db.session.add(welcome_conversation)
                        db.session.flush()  # Flush to get the conversation UUID

                        # Create the welcome notification message
                        welcome_message = Messages(
                            messageuuid=str(uuid.uuid4()),
                            conversationuuid=welcome_conversation.conversationuuid,
                            useruuid='00000000-0000-0000-0000-000000000000',  # System message
                            tenantuuid=tenant_uuid,
                            entityuuid=tenant_uuid,
                            entity_type='tenant',
                            title=f'Welcome to Wegweiser, {firstname}!',
                            content=f'Welcome to Wegweiser! We\'ve credited your account with 250 Wegcoins to get you started. Deploy our agents on your machines to begin monitoring and gain valuable insights. Visit the Help & Support section for step-by-step guidance on your first steps.',
                            is_read=False,
                            created_at=int(time.time()),
                            message_type='system'
                        )
                        db.session.add(welcome_message)
                        db.session.commit()

                        log_with_route(logging.INFO, f"Created welcome notification for new tenant: {companyname}")
                    except Exception as e:
                        log_with_route(logging.ERROR, f"Failed to create welcome notification for new tenant {companyname}: {e}")
                        db.session.rollback()

                    # 2. Send webhook notification to N8N
                    from app.utilities.webhook_sender import send_tenant_registration_notification

                    webhook_result = send_tenant_registration_notification(
                        companyname=companyname,
                        additional_data={
                            "firstname": firstname,
                            "lastname": lastname,
                            "companyemail": companyemail,
                            "tenant_uuid": tenant_uuid,
                            "registration_timestamp": time.time()
                        }
                    )

                # Start helpdesk user creation in a separate thread
                Thread(target=create_helpdesk_user_async, args=(firstname, lastname, companyemail, password, companyname)).start()

                # Record this IP's successful registration
                record_ip_registration(client_ip)
                
                # Log successful registration with full details for security audit
                registration_details = {
                    'ip': client_ip,
                    'email': companyemail,
                    'name': f"{firstname} {lastname}",
                    'company': companyname,
                    'tenant_uuid': tenant_uuid,
                    'user_uuid': user_uuid,
                    'role': role.rolename if role else 'unknown',
                    'recaptcha_score': score,
                    'is_new_tenant': is_new_tenant
                }
                log_with_route(logging.INFO, f"REGISTRATION SUCCESS: {registration_details}")
                
                # Create email verification token and send verification email
                verification = create_verification_token(new_user.useruuid, companyemail)
                if verification:
                    email_sent = send_verification_email(companyemail, firstname, verification.token)
                    if email_sent:
                        flash('Registration successful! Please check your email and click the verification link to activate your account.', 'success')
                        log_with_route(logging.INFO, f"Verification email sent to {companyemail} from IP {client_ip}")
                    else:
                        flash('Registration successful, but there was an issue sending the verification email. Please contact support.', 'warning')
                        log_with_route(logging.WARNING, f"User registered from {client_ip} but verification email failed for {companyemail}")
                else:
                    flash('Registration successful, but there was an issue creating the verification token. Please contact support.', 'warning')
                    log_with_route(logging.WARNING, f"User registered from {client_ip} but verification token creation failed for {companyemail}")

                return redirect(url_for('login_bp.login'))

            except Exception as e:
                db_session.rollback()
                log_with_route(logging.ERROR, f'Unexpected error during registration: {e}', exc_info=True)
                flash('An unexpected error occurred.', 'danger')
                return render_template('register.html', form=form)

            finally:
                db_session.close()
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    flash(f"Error in {getattr(form, field).label.text}: {error}", 'danger')

    return render_template('register.html', form=form)