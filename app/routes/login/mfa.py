# Filepath: app/routes/login/mfa.py
# Filepath: app/routes/two_factor.py
import qrcode
import io
import base64
import uuid
from flask import Blueprint, render_template, redirect, url_for, flash, session, request, current_app
from app.models import db, Accounts, UserTwoFactor
from app.forms.two_factor import EnableTwoFactorForm, BackupCodeForm, TwoFactorForm
from app.utilities.app_logging_helper import log_with_route
from app.utilities.app_access_login_required import login_required
from flask_principal import Identity, identity_changed
import logging
from datetime import datetime

two_factor_bp = Blueprint('two_factor_bp', __name__)

def perform_login(account):
    """Helper function to perform login actions"""
    from flask import request
    import time
    
    session.clear()
    # Convert UUID to string for session storage
    session['user_id'] = str(account.useruuid)
    session['userfirstname'] = account.firstname
    session['userlastname'] = account.lastname
    session['companyname'] = account.companyname
    session['tenant_uuid'] = str(account.tenantuuid)  # Make sure to set tenant_uuid
    session['role'] = account.role.rolename if account.role else None
    session['theme'] = account.theme if account.theme else 'light-theme'
    session['companyemail'] = account.companyemail
    session['profileimage'] = account.profile_picture
    session['two_factor_complete'] = True  # Add this to indicate 2FA is complete
    
    # Track login IP and timestamp for security auditing
    try:
        def get_client_ip():
            if request.headers.get('X-Forwarded-For'):
                return request.headers.get('X-Forwarded-For').split(',')[0].strip()
            return request.remote_addr
        
        client_ip = get_client_ip()
        account.last_login_ip = client_ip
        account.last_login_at = int(time.time())
        db.session.commit()
        log_with_route(logging.DEBUG, f"Updated login IP for {account.companyemail}: {client_ip}")
    except Exception as e:
        log_with_route(logging.WARNING, f"Failed to update login IP for {account.companyemail}: {str(e)}")

@two_factor_bp.route('/two-factor/backup', methods=['GET', 'POST'])
def backup_code():
    if not session.get('partial_login'):
        flash('You need to complete the first step of authentication.', 'danger')
        return redirect(url_for('login_bp.login'))

    form = BackupCodeForm()
    
    # Check honeypot field (anti-bot trap)
    honeypot = request.form.get('website', '')
    if honeypot:
        # Bot detected - honeypot field was filled
        log_with_route(logging.WARNING, f"HONEYPOT BLOCKED: Bot detected at backup code verification - honeypot value: '{honeypot[:50]}'")
        flash('Authentication failed. Please try again.', 'danger')
        return render_template('login/backup_code.html', form=form)
    
    if form.validate_on_submit():
        try:
            # Get user_uuid from session
            user_uuid_str = session.get('temp_user_id')
            if not user_uuid_str:
                flash('Authentication session expired. Please log in again.', 'danger')
                return redirect(url_for('login_bp.login'))

            # Convert string to UUID
            user_uuid = uuid.UUID(str(user_uuid_str))
            
            # Get user
            user = Accounts.query.filter_by(useruuid=user_uuid).first()
            if not user:
                flash('User not found. Please log in again.', 'danger')
                return redirect(url_for('login_bp.login'))

            # Get 2FA record
            two_factor = UserTwoFactor.query.filter_by(user_uuid=user_uuid).first()
            if not two_factor:
                flash('Two-factor authentication is not properly set up.', 'danger')
                return redirect(url_for('login_bp.login'))

            # Get backup code from form
            backup_code = form.code.data
            log_with_route(logging.INFO, f"Attempting to verify backup code: {backup_code}")
            
            # Verify code
            if two_factor.verify_backup_code(str(backup_code)):
                perform_login(user)
                session.pop('partial_login', None)
                session.pop('temp_user_id', None)
                
                identity = Identity(user.useruuid)
                identity_changed.send(current_app._get_current_object(), identity=identity)
                
                flash('You should generate new backup codes for your account.', 'warning')
                log_with_route(logging.INFO, f"Successful backup code login for user {user.companyemail}")
                return redirect(url_for('dashboard_bp.dashboard'))
            
            log_with_route(logging.WARNING, f"Failed backup code attempt")
            flash('Invalid backup code. Please try again.', 'danger')

        except Exception as e:
            log_with_route(logging.ERROR, f"Backup code verification error: {str(e)}")
            flash('An error occurred. Please try again.', 'danger')
            return redirect(url_for('login_bp.login'))

    return render_template('login/backup_code.html', form=form)

@two_factor_bp.route('/setup-2fa', methods=['GET', 'POST'])
@login_required
def setup_2fa():
    form = EnableTwoFactorForm()
    user_uuid = session['user_id']
    account = Accounts.query.get(user_uuid)
    
    # Check if 2FA is already enabled
    existing_2fa = UserTwoFactor.query.filter_by(user_uuid=user_uuid).first()
    if existing_2fa and existing_2fa.is_enabled:
        flash('Two-factor authentication is already enabled.', 'info')
        return redirect(url_for('profile_bp.profile'))

    if not existing_2fa:
        # Create new 2FA setup
        existing_2fa = UserTwoFactor(user_uuid=user_uuid)
        db.session.add(existing_2fa)
        db.session.commit()

    # Check honeypot field (anti-bot trap)
    honeypot = request.form.get('website', '')
    if honeypot:
        # Bot detected - honeypot field was filled
        log_with_route(logging.WARNING, f"HONEYPOT BLOCKED: Bot detected at 2FA from session user - honeypot value: '{honeypot[:50]}'")
        flash('Authentication failed. Please try again.', 'danger')
        return render_template('login/two_factor.html', form=form)
    
    if form.validate_on_submit():
        if existing_2fa.verify_totp(form.token.data):
            existing_2fa.is_enabled = True
            db.session.commit()
            flash('Two-factor authentication has been enabled successfully.', 'success')
            log_with_route(logging.INFO, f"2FA enabled for user {account.companyemail}")
            return redirect(url_for('profile_bp.profile'))
        else:
            flash('Invalid verification code. Please try again.', 'danger')

    # Generate QR code
    qr = qrcode.QRCode(version=1, box_size=10, border=5)
    provisioning_uri = existing_2fa.get_provisioning_uri(account.companyemail)
    qr.add_data(provisioning_uri)
    qr.make(fit=True)

    img = qr.make_image(fill_color="black", back_color="white")
    img_buffer = io.BytesIO()
    img.save(img_buffer, format='PNG')
    img_str = base64.b64encode(img_buffer.getvalue()).decode()
    
    return render_template('user/setup_2fa.html',
                         form=form,
                         qr_code=f"data:image/png;base64,{img_str}",
                         secret_key=existing_2fa.key,
                         backup_codes=existing_2fa.backup_codes)

@two_factor_bp.route('/disable-2fa', methods=['POST'])
@login_required
def disable_2fa():
    user_uuid = session['user_id']
    account = Accounts.query.get(user_uuid)
    two_factor = UserTwoFactor.query.filter_by(user_uuid=user_uuid).first()
    
    if two_factor:
        db.session.delete(two_factor)
        db.session.commit()
        flash('Two-factor authentication has been disabled.', 'success')
        log_with_route(logging.INFO, f"2FA disabled for user {account.companyemail}")
    
    return redirect(url_for('profile_bp.profile'))

@two_factor_bp.route('/new-backup-codes', methods=['POST'])
@login_required
def generate_new_backup_codes():
    user_uuid = session['user_id']
    account = Accounts.query.get(user_uuid)
    two_factor = UserTwoFactor.query.filter_by(user_uuid=user_uuid).first()

    if two_factor:
        new_codes = two_factor.get_new_backup_codes()
        flash('New backup codes have been generated. Please save them in a secure location.', 'success')
        log_with_route(logging.INFO, f"New backup codes generated for user {account.companyemail}")
        return render_template('user/backup_codes.html', backup_codes=new_codes, now=datetime.now)

    flash('Two-factor authentication is not enabled.', 'danger')
    return redirect(url_for('profile_bp.profile'))