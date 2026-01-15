# Filepath: app/routes/login/login.py
# Filepath: app/routes/login.py
import os
import requests
from flask import Blueprint, request, render_template, redirect, url_for, session, flash, current_app
from flask_principal import Identity, identity_changed
from app.models import db, Accounts, Tenants, Roles, Organisations, Groups, UserTwoFactor
from flask_bcrypt import Bcrypt
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import DataRequired, Email
from flask_wtf.csrf import CSRFProtect
from threading import Thread
import uuid
from app import microsoft
import time
from app.routes.registration.register import create_helpdesk_user_async
import logging
from app.utilities.app_logging_helper import log_with_route
from app.utilities.session_manager import session_manager
from flask import render_template, redirect, url_for, flash
from app.forms.login import LoginForm
from app.forms.two_factor import TwoFactorForm, BackupCodeForm
from functools import wraps

login_bp = Blueprint('login_bp', __name__)
bcrypt = Bcrypt()
csrf = CSRFProtect()

# Set up Flask-Limiter for rate limiting
limiter = Limiter(
    key_func=get_remote_address,
    app=current_app,
    default_limits=["5 per minute"]
)

class LoginForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Login')

def get_client_ip():
    if request.headers.get('X-Forwarded-For'):
        return request.headers.get('X-Forwarded-For').split(',')[0].strip()
    return request.remote_addr

def verify_recaptcha_v3(token):
    if not token:
        log_with_route(logging.WARNING, "reCAPTCHA token is empty or missing")
        return False, 0.0, {'success': False, 'error-codes': ['missing-input-response']}
    
    secret_key = current_app.config['RECAPTCHA_PRIVATE_KEY']
    if not secret_key:
        log_with_route(logging.ERROR, "reCAPTCHA secret key not configured")
        return False, 0.0, {'success': False, 'error-codes': ['missing-secret-key']}
    
    payload = {
        'secret': secret_key,
        'response': token
    }
    
    try:
        response = requests.post('https://www.google.com/recaptcha/api/siteverify', data=payload, timeout=5)
        result = response.json()
        
        # Enhanced logging for debugging
        success = result.get('success', False)
        score = result.get('score', 0.0)
        error_codes = result.get('error-codes', [])
        
        if not success:
            log_with_route(logging.WARNING, f"reCAPTCHA verification failed: {error_codes}")
        
        return success, score, result
    except requests.exceptions.Timeout:
        log_with_route(logging.ERROR, "reCAPTCHA verification timeout")
        return False, 0.0, {'success': False, 'error-codes': ['timeout']}
    except Exception as e:
        log_with_route(logging.ERROR, f"reCAPTCHA verification exception: {str(e)}")
        return False, 0.0, {'success': False, 'error-codes': ['exception']}

def two_factor_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('two_factor_complete') and session.get('user_id'):
            return redirect(url_for('login_bp.two_factor'))
        return f(*args, **kwargs)
    return decorated_function

@login_bp.route('/login', methods=['GET', 'POST'])
@limiter.limit("5 per minute")
def login():
    if request.method == 'GET' and session.get('partial_login'):
        return redirect(url_for('login_bp.two_factor'))

    form = LoginForm()
    if request.method == 'POST':
        # Clear session at the beginning of every POST request to avoid stale data
        session.clear()

        # Check honeypot field (anti-bot trap)
        honeypot = request.form.get('website', '')
        if honeypot:
            # Bot detected - honeypot field was filled
            log_with_route(logging.WARNING, f"HONEYPOT BLOCKED: Bot detected at login from {get_client_ip()} - honeypot value: '{honeypot[:50]}'")
            flash('Login failed. Please try again.', 'danger')
            return render_template('login/index.html', form=form, show_resend_link=False)

        recaptcha_token = request.form.get('g-recaptcha-response')
        success, score, recaptcha_result = verify_recaptcha_v3(recaptcha_token)

        # Log the reCAPTCHA interaction with more detail
        client_ip = get_client_ip()
        user_agent = request.headers.get('User-Agent', 'Unknown')
        is_safari = 'Safari' in user_agent and 'Chrome' not in user_agent
        
        log_with_route(logging.INFO, f'reCAPTCHA result: success={success}, score={score}, errors={recaptcha_result.get("error-codes", [])}, IP: {client_ip}, Safari: {is_safari}, session ID: {session.sid}')

        if not success:
            error_codes = recaptcha_result.get('error-codes', [])
            if 'timeout-or-duplicate' in error_codes:
                flash('Security verification expired. Please refresh the page and try again.', 'warning')
            elif 'missing-input-response' in error_codes:
                flash('Security verification is loading. Please wait a moment and try again.', 'warning')
            else:
                flash('Security verification failed. Please refresh the page and try again.', 'danger')
            log_with_route(logging.WARNING, f"reCAPTCHA failed for {client_ip}: {error_codes}, Safari: {is_safari}")
            return redirect(url_for('login_bp.login'))
        
        if score < 0.5:
            flash('Security verification score too low. If you\'re using Safari, try refreshing the page. Otherwise, please contact support.', 'warning')
            log_with_route(logging.WARNING, f"reCAPTCHA low score ({score}) for {client_ip}, Safari: {is_safari}")
            return redirect(url_for('login_bp.login'))

        email = form.email.data
        password = form.password.data

        account = Accounts.query.filter_by(companyemail=email).first()

        if account and bcrypt.check_password_hash(account.password, password):
            # Check if email is verified
            if not account.email_verified:
                flash('Please verify your email address before logging in. Check your inbox for the verification link.', 'warning')
                log_with_route(logging.WARNING, f'Login attempt from {client_ip} for unverified email: {email}')
                return render_template('login/index.html', form=form, show_resend_link=True, email=email)

            # Check if 2FA is enabled for this account
            two_factor = UserTwoFactor.query.filter_by(user_uuid=account.useruuid).first()

            if two_factor and two_factor.is_enabled:
                session['partial_login'] = True
                session['temp_user_id'] = account.useruuid
                log_with_route(logging.INFO, f'2FA required for user {email} from {client_ip}')
                return redirect(url_for('login_bp.two_factor'))

            # If no 2FA, proceed with normal login
            perform_login(account)
            identity_changed.send(current_app._get_current_object(),
                                  identity=Identity(account.useruuid))

            log_with_route(logging.INFO, f'Successful login from {client_ip} for email: {email}, session ID: {session.sid}')
            return redirect(url_for('dashboard_bp.dashboard'))
        else:
            flash('Login failed. Please check your credentials and try again.', 'danger')
            log_with_route(logging.WARNING, f'Failed login attempt from {client_ip} for email: {email}, session ID: {session.sid}')
            return redirect(url_for('login_bp.login'))

    return render_template('login/index.html', form=form)

@login_bp.route('/two-factor', methods=['GET', 'POST'])
def two_factor():
    if not session.get('partial_login'):
        return redirect(url_for('login_bp.login'))

    form = TwoFactorForm()
    if form.validate_on_submit():
        user_uuid = session.get('temp_user_id')
        two_factor = UserTwoFactor.query.filter_by(user_uuid=user_uuid).first()
        
        if two_factor.verify_totp(form.token.data):
            account = Accounts.query.get(user_uuid)
            perform_login(account)
            session['two_factor_complete'] = True
            session.pop('partial_login', None)
            session.pop('temp_user_id', None)

            identity_changed.send(current_app._get_current_object(),
                                  identity=Identity(account.useruuid))

            log_with_route(logging.INFO, f"User {account.companyemail} completed 2FA successfully")
            return redirect(url_for('dashboard_bp.dashboard'))
            
        log_with_route(logging.WARNING, f"Invalid 2FA attempt for user_uuid: {user_uuid}")
        flash('Invalid authentication code.', 'danger')
    
    return render_template('login/two_factor.html', form=form)

@login_bp.route('/two-factor/backup', methods=['GET', 'POST'])
def backup_code():
    if not session.get('partial_login'):
        flash('You need to complete the first step of authentication.', 'danger')
        return redirect(url_for('login_bp.login'))

    form = BackupCodeForm()

    # Add debug logging for request method and form data
    log_with_route(logging.INFO, f"Request method: {request.method}")
    log_with_route(logging.INFO, f"Form data: {request.form}")
    
    if request.method == 'POST':
        log_with_route(logging.INFO, f"Raw form code value: {request.form.get('code')}")
        log_with_route(logging.INFO, f"Form validation: {form.validate()}")
        log_with_route(logging.INFO, f"Form errors: {form.errors}")
        
        if form.validate_on_submit():
            try:
                # Get and validate user_uuid from session
                user_uuid = session.get('temp_user_id')
                log_with_route(logging.INFO, f"Session user_uuid: {user_uuid}")
                
                if not user_uuid:
                    flash('Authentication session expired. Please log in again.', 'danger')
                    return redirect(url_for('login_bp.login'))

                # Get the actual form data before any processing
                backup_code = form.code.data
                log_with_route(logging.INFO, f"Form code data: {backup_code}, Type: {type(backup_code)}")
                
                # Explicitly convert and clean the code here
                if backup_code:
                    backup_code = str(backup_code).strip()
                    log_with_route(logging.INFO, f"Cleaned backup code: {backup_code}")
                else:
                    log_with_route(logging.ERROR, "No backup code provided")
                    flash('Please enter a backup code.', 'danger')
                    return render_template('login/backup_code.html', form=form)

                # Get the user and 2FA records
                two_factor = UserTwoFactor.query.filter_by(user_uuid=uuid.UUID(user_uuid)).first()
                if not two_factor:
                    flash('Two-factor authentication is not properly set up.', 'danger')
                    return redirect(url_for('login_bp.login'))

                # Verify the code
                result = two_factor.verify_backup_code(backup_code)
                log_with_route(logging.INFO, f"Verification result: {result}")

                if result:
                    account = Accounts.query.get(uuid.UUID(user_uuid))
                    perform_login(account)
                    session['two_factor_complete'] = True
                    session.pop('partial_login', None)
                    session.pop('temp_user_id', None)

                    identity_changed.send(current_app._get_current_object(),
                                      identity=Identity(account.useruuid))

                    flash('You should generate new backup codes for your account.', 'warning')
                    return redirect(url_for('dashboard_bp.dashboard'))
                
                flash('Invalid backup code. Please try again.', 'danger')
                
            except Exception as e:
                log_with_route(logging.ERROR, f"Error in backup code verification: {str(e)}")
                flash('An error occurred. Please try again.', 'danger')
                
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    flash(f"{field}: {error}", 'danger')

    return render_template('login/backup_code.html', form=form)

@login_bp.route('/logout')
def logout():
    user_id = session.get('user_id')
    session_id = session.get('weg_session_id')

    if user_id:
        log_with_route(logging.INFO, f"User {user_id} is logging out, session ID: {session.sid}.")
        # Remove this specific session from user's active sessions
        # but keep other sessions active (don't invalidate all sessions)
        try:
            session_manager.invalidate_user_sessions(str(user_id), except_session_id=session_id)
        except Exception as e:
            log_with_route(logging.WARNING, f"Failed to update session tracking on logout: {str(e)}")
    else:
        log_with_route(logging.WARNING, f"An anonymous session is being cleared, session ID: {session.sid}.")

    session.clear()
    log_with_route(logging.INFO, f"Session cleared successfully, session ID: {session.sid}.")

    return redirect(url_for('login_bp.login'))

@login_bp.route('/login/microsoft')
def login_microsoft():
    redirect_uri = url_for('login_bp.auth_microsoft_callback', _external=True)
    return microsoft.authorize_redirect(redirect_uri)

@login_bp.route('/auth/microsoft/callback')
def auth_microsoft_callback():
    token = microsoft.authorize_access_token()
    user_info = microsoft.get('https://graph.microsoft.com/v1.0/me').json()

    # Handle the login or registration process here
    return handle_sso_login(user_info['givenName'], user_info['surname'], user_info['mail'])

def handle_sso_login(firstname, lastname, email):
    account = Accounts.query.filter_by(companyemail=email).first()

    if account:
        # User exists, log them in
        session.clear()
        session['user_id'] = account.useruuid
        session['userfirstname'] = account.firstname
        session['userlastname'] = account.lastname
        session['companyname'] = account.companyname
        session['tenant_uuid'] = account.tenantuuid
        session['role'] = account.role.rolename
        session['theme'] = account.theme if account.theme else 'light-theme'
        session['companyemail'] = account.companyemail
        session['profileimage'] = account.profile_picture

        identity_changed.send(current_app._get_current_object(),
                              identity=Identity(account.useruuid))

        log_with_route(logging.INFO, f'Successful SSO login for email: {email}, session ID: {session.sid}')
        return redirect(url_for('dashboard_bp.dashboard'))

    else:
        # User doesn't exist, create a new user and log them in
        tenant_uuid = str(uuid.uuid4())
        new_tenant = Tenants(
            tenantuuid=tenant_uuid,
            tenantname=email.split('@')[1],  # Using domain as tenant name
            created_at=time.time()
        )
        db.session.add(new_tenant)

        hashed_password = bcrypt.generate_password_hash(str(uuid.uuid4())).decode('utf-8')  # Random password

        role = db.session.query(Roles).filter_by(rolename='user').first()

        user_uuid = str(uuid.uuid4())
        new_user = Accounts(
            useruuid=user_uuid,
            firstname=firstname,
            lastname=lastname,
            companyname=email.split('@')[1],
            companyemail=email,
            password=hashed_password,
            role_id=role.roleuuid,
            tenantuuid=tenant_uuid
        )
        db.session.add(new_user)

        org_uuid = str(uuid.uuid4())
        new_organisation = Organisations(
            orguuid=org_uuid,
            orgname=email.split('@')[1],
            tenantuuid=tenant_uuid
        )
        db.session.add(new_organisation)

        group_uuid = str(uuid.uuid4())
        new_group = Groups(
            groupuuid=group_uuid,
            groupname='Default',
            orguuid=org_uuid,
            tenantuuid=tenant_uuid
        )
        db.session.add(new_group)

        db.session.commit()

        # SSO registration wegcoin assignment removed as requested

        try:
            webhook_url = "https://datenfluss.oldforge.tech/webhook-test/7507cccd-0aee-40ad-9b3c-23aa392ca94b"
            webhook_data = {"message": "New tenant registered"}
            response = requests.post(webhook_url, json=webhook_data, timeout=10)
            if response.status_code == 200:
                log_with_route(logging.INFO, f"Successfully sent webhook notification for new SSO tenant: {email.split('@')[1]}")
            else:
                log_with_route(logging.WARNING, f"Webhook notification failed with status {response.status_code} for SSO tenant: {email.split('@')[1]}")
        except Exception as e:
            log_with_route(logging.ERROR, f"Failed to send webhook notification for new SSO tenant {email.split('@')[1]}: {e}")

        # Start the helpdesk user creation in a separate thread
        Thread(target=create_helpdesk_user_async, args=(firstname, lastname, email, str(uuid.uuid4()), email.split('@')[1])).start()

        session.clear()
        session['user_id'] = user_uuid
        session['userfirstname'] = firstname
        session['userlastname'] = lastname
        session['companyname'] = email.split('@')[1]

        log_with_route(logging.INFO, f"New user registered and logged in via SSO: {email}, session ID: {session.sid}")
        return redirect(url_for('dashboard_bp.dashboard'))

def perform_login(account):
    """Helper function to set up user session with security enhancements"""
    session.clear()
    session['user_id'] = account.useruuid
    session['userfirstname'] = account.firstname
    session['userlastname'] = account.lastname
    session['companyname'] = account.companyname
    session['tenant_uuid'] = account.tenantuuid
    session['role'] = account.role.rolename
    session['theme'] = account.theme if account.theme else 'light-theme'
    session['companyemail'] = account.companyemail
    session['profileimage'] = account.profile_picture

    # Security enhancements
    session.permanent = True  # Enable session timeout

    # Regenerate session ID for security
    session_manager.regenerate_session(user_id=str(account.useruuid), reason="login")

    # Track session for concurrent session management
    session_manager.track_user_session(user_id=str(account.useruuid))
    
    # Track login IP and timestamp for security auditing
    try:
        client_ip = get_client_ip()
        account.last_login_ip = client_ip
        account.last_login_at = int(time.time())
        db.session.commit()
        log_with_route(logging.DEBUG, f"Updated login IP for {account.companyemail}: {client_ip}")
    except Exception as e:
        log_with_route(logging.WARNING, f"Failed to update login IP for {account.companyemail}: {str(e)}")

def checkDir(dirToCheck):
    if not os.path.isdir(dirToCheck):
        try:
            os.makedirs(dirToCheck)
            log_with_route(logging.INFO, f'{dirToCheck} created.')
        except Exception as e:
            log_with_route(logging.ERROR, f'Failed to create {dirToCheck}. Reason: {e}')