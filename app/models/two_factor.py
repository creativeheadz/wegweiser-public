# Filepath: app/models/two_factor.py
from . import db
from datetime import datetime
from passlib.totp import TOTP
from passlib.exc import TokenError, MalformedTokenError
import base64
import os
from sqlalchemy.dialects.postgresql import UUID
import uuid
import logging
from app.utilities.app_logging_helper import log_with_route

class UserTwoFactor(db.Model):
    __tablename__ = 'user_two_factor'
    id = db.Column(db.Integer, primary_key=True)
    user_uuid = db.Column(UUID(as_uuid=True), db.ForeignKey('accounts.useruuid', ondelete="CASCADE"), nullable=False, unique=True)
    totp_secret = db.Column(db.String(32), nullable=False)
    is_enabled = db.Column(db.Boolean, default=False)
    backup_codes = db.Column(db.JSON)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_used = db.Column(db.DateTime)
    used_windows = db.Column(db.JSON, default=list)

    def __init__(self, user_uuid):
        if isinstance(user_uuid, str):
            user_uuid = uuid.UUID(user_uuid)
        self.user_uuid = user_uuid
        self.totp_secret = base64.b32encode(os.urandom(20)).decode('utf-8')
        self.backup_codes = self._generate_backup_codes()
        self.is_enabled = False
        self.used_windows = []

    def _generate_backup_codes(self, count=8, length=10):
        """Generate cryptographically secure backup codes"""
        codes = []
        for _ in range(count):
            random_bytes = os.urandom(length)
            code = base64.b32encode(random_bytes)[:length].decode('utf-8')
            codes.append(code)
        return codes

    def verify_totp(self, token):
        """Verify a TOTP token with time window tracking"""
        try:
            totp = TOTP(key=self.totp_secret, issuer="Wegweiser", digits=6)
            match_result = totp.match(token)
            
            if match_result:
                self.last_used = datetime.utcnow()
                db.session.commit()
                return True
            return False

        except (TokenError, MalformedTokenError) as e:
            log_with_route(logging.ERROR, f"TOTP verification error: {str(e)}")
            return False
        except Exception as e:
            log_with_route(logging.ERROR, f"Unexpected error in TOTP verification: {str(e)}")
            return False

    def verify_backup_code(self, code):
        """Verify and consume a backup code"""
        try:
            log_with_route(logging.INFO, f"Verifying backup code: {code}")
            
            if not isinstance(code, str):
                log_with_route(logging.ERROR, f"Invalid code type: {type(code)}")
                return False

            # Clean the code (remove spaces and hyphens)
            cleaned_code = code.strip().replace('-', '')
            log_with_route(logging.INFO, f"Cleaned code: {cleaned_code}")

            # Handle case where backup_codes is None or not a list
            if not self.backup_codes or not isinstance(self.backup_codes, list):
                log_with_route(logging.ERROR, "No backup codes available")
                return False

            log_with_route(logging.INFO, f"Checking code against backup codes: {self.backup_codes}")

            # Check if the code exists and consume it
            if cleaned_code in self.backup_codes:
                self.backup_codes.remove(cleaned_code)
                db.session.commit()
                log_with_route(logging.INFO, "Backup code verified successfully")
                return True

            log_with_route(logging.WARNING, "Invalid backup code")
            return False

        except Exception as e:
            log_with_route(logging.ERROR, f"Error in verify_backup_code: {str(e)}")
            return False
    
    def get_provisioning_uri(self, email):
        """Generate URI for QR code"""
        totp = TOTP(key=self.totp_secret, issuer="Wegweiser", digits=6)
        return totp.to_uri(label=email)

    def get_new_backup_codes(self):
        """Generate new set of backup codes and invalidate old ones"""
        self.backup_codes = self._generate_backup_codes()
        db.session.commit()
        return self.backup_codes

    @property
    def key(self):
        """Get the current secret key"""
        return self.totp_secret