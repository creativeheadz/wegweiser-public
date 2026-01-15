# Filepath: app/utilities/email_verification.py
import secrets
import string
from flask import url_for, current_app, render_template_string
from flask_mail import Message
from app import mail
from app.models import db, EmailVerification, Accounts
from app.utilities.app_logging_helper import log_with_route
import logging
from datetime import datetime
from datetime import datetime

def generate_verification_token(length=32):
    """Generate a secure random token for email verification"""
    alphabet = string.ascii_letters + string.digits
    return ''.join(secrets.choice(alphabet) for _ in range(length))

def create_verification_token(user_uuid, email):
    """Create a new email verification token for a user"""
    try:
        # Generate unique token
        token = generate_verification_token()
        
        # Ensure token is unique
        while EmailVerification.query.filter_by(token=token).first():
            token = generate_verification_token()
        
        # Create verification record
        verification = EmailVerification(
            user_uuid=user_uuid,
            token=token,
            email=email,
            expires_in_hours=24  # Token expires in 24 hours
        )
        
        db.session.add(verification)
        db.session.commit()
        
        log_with_route(logging.INFO, f"Created verification token for {email}")
        return verification
        
    except Exception as e:
        db.session.rollback()
        log_with_route(logging.ERROR, f"Failed to create verification token for {email}: {str(e)}")
        return None

def send_verification_email(email, firstname, token):
    """Send verification email to user"""
    try:
        # Generate verification URL
        verification_url = url_for('auth_bp.verify_email', token=token, _external=True)
        
        # Email template
        current_year = datetime.now().year

        email_template = """
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Verify Your Email - Wegweiser</title>
            <style>
            body {
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                line-height: 1.6;
                color: #333;
                max-width: 600px;
                margin: 0 auto;
                padding: 20px;
                background-color: #f4f4f4;
            }
            .email-container {
                background-color: white;
                padding: 30px;
                border-radius: 10px;
                box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
            }
            .logo {
                text-align: center;
                margin-bottom: 30px;
            }
            .logo h1 {
                color: #2c3e50;
                font-size: 28px;
                margin: 0;
            }
            .content {
                text-align: center;
            }
            .verify-button {
                display: inline-block;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                padding: 15px 30px;
                text-decoration: none;
                border-radius: 25px;
                font-weight: bold;
                margin: 20px 0;
                transition: transform 0.2s;
            }
            .verify-button:hover {
                transform: translateY(-2px);
            }
            .footer {
                margin-top: 30px;
                padding-top: 20px;
                border-top: 1px solid #eee;
                font-size: 12px;
                color: #666;
                text-align: center;
            }
            .alternative-link {
                margin-top: 20px;
                padding: 15px;
                background-color: #f8f9fa;
                border-radius: 5px;
                font-size: 12px;
                word-break: break-all;
            }
            </style>
        </head>
        <body>
            <div class="email-container">
            <div class="logo">
                <h1>Wegweiser</h1>
            </div>
            
            <div class="content">
                <h2>Welcome to Wegweiser, {{ firstname }}!</h2>
                <p>Thank you for registering with Wegweiser. To complete your registration and activate your account, please verify your email address by clicking the button below:</p>
                
                <a href="{{ verification_url }}" class="verify-button">Verify Email Address</a>
                
                <p>This verification link will expire in 24 hours for security reasons.</p>
                
                <div class="alternative-link">
                <p><strong>If the button doesn't work, copy and paste this link into your browser:</strong></p>
                <p>{{ verification_url }}</p>
                </div>
                
                <p>If you didn't create an account with Wegweiser, you can safely ignore this email.</p>
            </div>
            
            <div class="footer">
                <p>This is an automated message from Wegweiser. Please do not reply to this email.</p>
                <p>&copy; {{ current_year }} Wegweiser. All rights reserved.</p>
            </div>
            </div>
        </body>
        </html>
        """

        # Render template with variables, including current_year
        current_year = datetime.now().year
        html_content = render_template_string(
            email_template,
            firstname=firstname,
            verification_url=verification_url,
            current_year=current_year
        )
        
        # Create and send email
        msg = Message(
            subject="Verify Your Email Address - Wegweiser",
            recipients=[email],
            html=html_content,
            sender=current_app.config['MAIL_DEFAULT_SENDER']
        )
        
        mail.send(msg)
        log_with_route(logging.INFO, f"Verification email sent to {email}")
        return True
        
    except Exception as e:
        log_with_route(logging.ERROR, f"Failed to send verification email to {email}: {str(e)}")
        return False

def verify_email_token(token):
    """Verify an email verification token"""
    try:
        # Find the verification record
        verification = EmailVerification.query.filter_by(token=token).first()
        
        if not verification:
            log_with_route(logging.WARNING, f"Invalid verification token: {token}")
            return False, "Invalid verification token"
        
        if not verification.is_valid():
            if verification.is_expired():
                log_with_route(logging.WARNING, f"Expired verification token for {verification.email}")
                return False, "Verification token has expired"
            else:
                log_with_route(logging.WARNING, f"Already used verification token for {verification.email}")
                return False, "Verification token has already been used"
        
        # Mark token as used
        verification.mark_as_used()
        
        # Update user's email verification status
        user = Accounts.query.get(verification.user_uuid)
        if user:
            user.email_verified = True
            db.session.commit()
            log_with_route(logging.INFO, f"Email verified successfully for {verification.email}")
            return True, "Email verified successfully"
        else:
            log_with_route(logging.ERROR, f"User not found for verification token: {token}")
            return False, "User not found"
            
    except Exception as e:
        db.session.rollback()
        log_with_route(logging.ERROR, f"Error verifying email token {token}: {str(e)}")
        return False, "An error occurred during verification"

def resend_verification_email(email):
    """Resend verification email for a user"""
    try:
        user = Accounts.query.filter_by(companyemail=email).first()
        if not user:
            return False, "User not found"
        
        if user.email_verified:
            return False, "Email is already verified"
        
        # Invalidate any existing tokens for this user
        existing_tokens = EmailVerification.query.filter_by(
            user_uuid=user.useruuid, 
            is_used=False
        ).all()
        
        for token in existing_tokens:
            token.is_used = True
        
        # Create new verification token
        verification = create_verification_token(user.useruuid, email)
        if not verification:
            return False, "Failed to create verification token"
        
        # Send verification email
        success = send_verification_email(email, user.firstname, verification.token)
        if success:
            return True, "Verification email sent successfully"
        else:
            return False, "Failed to send verification email"
            
    except Exception as e:
        log_with_route(logging.ERROR, f"Error resending verification email to {email}: {str(e)}")
        return False, "An error occurred while resending verification email"
