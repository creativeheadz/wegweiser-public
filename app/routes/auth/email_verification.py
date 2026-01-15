# Filepath: app/routes/auth/email_verification.py
from flask import Blueprint, request, render_template, redirect, url_for, flash, jsonify
from app.utilities.email_verification import verify_email_token, resend_verification_email
from app.utilities.app_logging_helper import log_with_route
from app.models import db, Accounts
import logging

# Create blueprint
auth_bp = Blueprint('auth_bp', __name__, url_prefix='/auth')

@auth_bp.route('/verify-email/<token>')
def verify_email(token):
    """Handle email verification when user clicks the link"""
    try:
        success, message = verify_email_token(token)
        
        if success:
            flash('Your email has been verified successfully! You can now log in.', 'success')
            log_with_route(logging.INFO, f"Email verification successful for token: {token[:8]}...")
            return redirect(url_for('login_bp.login'))
        else:
            flash(f'Email verification failed: {message}', 'danger')
            log_with_route(logging.WARNING, f"Email verification failed for token: {token[:8]}... - {message}")
            return redirect(url_for('login_bp.login'))
            
    except Exception as e:
        log_with_route(logging.ERROR, f"Error in email verification route: {str(e)}")
        flash('An error occurred during email verification. Please try again.', 'danger')
        return redirect(url_for('login_bp.login'))

@auth_bp.route('/resend-verification', methods=['GET', 'POST'])
def resend_verification():
    """Handle resending verification emails"""
    if request.method == 'GET':
        return render_template('auth/resend_verification.html')
    
    try:
        email = request.form.get('email')
        if not email:
            flash('Please provide an email address.', 'danger')
            return render_template('auth/resend_verification.html')
        
        success, message = resend_verification_email(email)
        
        if success:
            flash('Verification email has been sent. Please check your inbox.', 'success')
            log_with_route(logging.INFO, f"Verification email resent to: {email}")
        else:
            flash(f'Failed to resend verification email: {message}', 'danger')
            log_with_route(logging.WARNING, f"Failed to resend verification email to: {email} - {message}")
        
        return render_template('auth/resend_verification.html')
        
    except Exception as e:
        log_with_route(logging.ERROR, f"Error in resend verification route: {str(e)}")
        flash('An error occurred. Please try again.', 'danger')
        return render_template('auth/resend_verification.html')

@auth_bp.route('/check-verification-status/<email>')
def check_verification_status(email):
    """API endpoint to check if an email is verified"""
    try:
        user = Accounts.query.filter_by(companyemail=email).first()
        if not user:
            return jsonify({'verified': False, 'message': 'User not found'})
        
        return jsonify({
            'verified': user.email_verified,
            'message': 'Email verified' if user.email_verified else 'Email not verified'
        })
        
    except Exception as e:
        log_with_route(logging.ERROR, f"Error checking verification status for {email}: {str(e)}")
        return jsonify({'verified': False, 'message': 'Error checking status'}), 500
