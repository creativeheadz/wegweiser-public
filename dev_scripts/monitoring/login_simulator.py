#!/usr/bin/env python3
"""
Advanced Login & MFA Simulator for Live Monitoring
Simulates complete user authentication flows including MFA
"""

import os
import sys
import time
import logging
from typing import Tuple, Optional, Dict
from dataclasses import dataclass
from passlib.totp import TOTP

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

logger = logging.getLogger(__name__)


@dataclass
class LoginSimulationResult:
    """Result of login simulation"""
    success: bool
    duration_ms: float
    message: str
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    mfa_required: bool = False
    mfa_verified: bool = False


class LoginSimulator:
    """Simulates user login flows"""
    
    def __init__(self, base_url: str = "http://localhost", timeout: int = 10):
        self.base_url = base_url.rstrip('/')
        self.timeout = timeout
        self.session = None
    
    def setup_test_user(self, email: str, password: str) -> Tuple[bool, str]:
        """
        Setup a test user in the database
        
        Returns:
            (success, user_id)
        """
        try:
            from app import create_app
            from app.models import db, Accounts, Tenants, Roles
            from flask_bcrypt import Bcrypt
            import uuid
            
            app = create_app()
            bcrypt = Bcrypt(app)
            
            with app.app_context():
                # Check if user exists
                existing_user = Accounts.query.filter_by(companyemail=email).first()
                if existing_user:
                    logger.info(f"Test user {email} already exists")
                    return True, str(existing_user.useruuid)
                
                # Create test tenant if needed
                test_tenant = Tenants.query.filter_by(tenantname="Test Tenant").first()
                if not test_tenant:
                    test_tenant = Tenants(
                        tenantuuid=uuid.uuid4(),
                        tenantname="Test Tenant",
                        tenantdomain="test.local"
                    )
                    db.session.add(test_tenant)
                    db.session.commit()
                
                # Get or create user role
                user_role = Roles.query.filter_by(rolename="user").first()
                if not user_role:
                    user_role = Roles(rolename="user", roledescription="Regular User")
                    db.session.add(user_role)
                    db.session.commit()
                
                # Create test user
                user_uuid = uuid.uuid4()
                hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
                
                test_user = Accounts(
                    useruuid=user_uuid,
                    tenantuuid=test_tenant.tenantuuid,
                    companyemail=email,
                    firstname="Test",
                    lastname="User",
                    password=hashed_password,
                    email_verified=True,
                    role_id=user_role.id
                )
                
                db.session.add(test_user)
                db.session.commit()
                
                logger.info(f"Test user {email} created successfully")
                return True, str(user_uuid)
        
        except Exception as e:
            logger.error(f"Failed to setup test user: {str(e)}")
            return False, None
    
    def setup_mfa_for_user(self, user_id: str) -> Tuple[bool, Optional[str]]:
        """
        Setup MFA for a test user
        
        Returns:
            (success, totp_secret)
        """
        try:
            from app import create_app
            from app.models import db, UserTwoFactor
            import uuid
            
            app = create_app()
            
            with app.app_context():
                # Check if MFA already exists
                existing_mfa = UserTwoFactor.query.filter_by(user_uuid=user_id).first()
                if existing_mfa:
                    logger.info(f"MFA already exists for user {user_id}")
                    return True, existing_mfa.totp_secret
                
                # Create new MFA
                mfa = UserTwoFactor(user_uuid=user_id)
                mfa.is_enabled = True
                db.session.add(mfa)
                db.session.commit()
                
                logger.info(f"MFA setup for user {user_id}")
                return True, mfa.totp_secret
        
        except Exception as e:
            logger.error(f"Failed to setup MFA: {str(e)}")
            return False, None
    
    def generate_totp_code(self, secret: str) -> str:
        """Generate a valid TOTP code"""
        try:
            totp = TOTP(key=secret, issuer="Wegweiser", digits=6)
            token = totp.generate().token
            logger.info(f"Generated TOTP code: {token}")
            return token
        except Exception as e:
            logger.error(f"Failed to generate TOTP: {str(e)}")
            return None
    
    def simulate_login_with_mfa(
        self,
        email: str,
        password: str,
        use_backup_code: bool = False
    ) -> LoginSimulationResult:
        """
        Simulate complete login flow with MFA
        
        Args:
            email: User email
            password: User password
            use_backup_code: Use backup code instead of TOTP
        
        Returns:
            LoginSimulationResult
        """
        start_time = time.time()
        
        try:
            import requests
            from bs4 import BeautifulSoup
            
            # Step 1: Setup test user if needed
            user_exists, user_id = self.setup_test_user(email, password)
            if not user_exists:
                return LoginSimulationResult(
                    success=False,
                    duration_ms=(time.time() - start_time) * 1000,
                    message="Failed to setup test user"
                )
            
            # Step 2: Setup MFA
            mfa_setup, totp_secret = self.setup_mfa_for_user(user_id)
            if not mfa_setup:
                return LoginSimulationResult(
                    success=False,
                    duration_ms=(time.time() - start_time) * 1000,
                    message="Failed to setup MFA"
                )
            
            # Step 3: Get login page and extract CSRF token
            session = requests.Session()
            login_page = session.get(
                f"{self.base_url}/login",
                timeout=self.timeout
            )
            
            if login_page.status_code != 200:
                return LoginSimulationResult(
                    success=False,
                    duration_ms=(time.time() - start_time) * 1000,
                    message=f"Login page returned {login_page.status_code}"
                )
            
            # Extract CSRF token
            soup = BeautifulSoup(login_page.text, 'html.parser')
            csrf_token = None
            csrf_input = soup.find('input', {'name': 'csrf_token'})
            if csrf_input:
                csrf_token = csrf_input.get('value')
            
            # Step 4: Attempt login
            login_data = {
                'email': email,
                'password': password,
                'csrf_token': csrf_token or '',
                'g-recaptcha-response': 'test-token'  # Mock reCAPTCHA
            }
            
            login_response = session.post(
                f"{self.base_url}/login",
                data=login_data,
                timeout=self.timeout,
                allow_redirects=False
            )
            
            # Step 5: Check if MFA is required
            if login_response.status_code == 302:
                redirect_location = login_response.headers.get('Location', '')
                if 'two-factor' in redirect_location or 'mfa' in redirect_location:
                    # MFA required - get MFA page
                    mfa_page = session.get(
                        f"{self.base_url}{redirect_location}",
                        timeout=self.timeout
                    )
                    
                    if mfa_page.status_code != 200:
                        return LoginSimulationResult(
                            success=False,
                            duration_ms=(time.time() - start_time) * 1000,
                            message="Failed to access MFA page",
                            mfa_required=True
                        )
                    
                    # Step 6: Submit MFA code
                    if use_backup_code:
                        # Get backup codes from database
                        from app import create_app
                        from app.models import db, UserTwoFactor
                        
                        app = create_app()
                        with app.app_context():
                            mfa_record = UserTwoFactor.query.filter_by(user_uuid=user_id).first()
                            if not mfa_record or not mfa_record.backup_codes:
                                return LoginSimulationResult(
                                    success=False,
                                    duration_ms=(time.time() - start_time) * 1000,
                                    message="No backup codes available",
                                    mfa_required=True
                                )
                            mfa_code = mfa_record.backup_codes[0]
                    else:
                        # Generate TOTP code
                        mfa_code = self.generate_totp_code(totp_secret)
                        if not mfa_code:
                            return LoginSimulationResult(
                                success=False,
                                duration_ms=(time.time() - start_time) * 1000,
                                message="Failed to generate TOTP code",
                                mfa_required=True
                            )
                    
                    # Submit MFA
                    mfa_data = {
                        'code': mfa_code,
                        'csrf_token': csrf_token or ''
                    }
                    
                    mfa_response = session.post(
                        f"{self.base_url}/two-factor",
                        data=mfa_data,
                        timeout=self.timeout,
                        allow_redirects=False
                    )
                    
                    if mfa_response.status_code == 302:
                        return LoginSimulationResult(
                            success=True,
                            duration_ms=(time.time() - start_time) * 1000,
                            message="Login with MFA successful",
                            user_id=user_id,
                            mfa_required=True,
                            mfa_verified=True
                        )
                    else:
                        return LoginSimulationResult(
                            success=False,
                            duration_ms=(time.time() - start_time) * 1000,
                            message=f"MFA verification failed: {mfa_response.status_code}",
                            mfa_required=True
                        )
            
            elif login_response.status_code == 302:
                # Login successful without MFA
                return LoginSimulationResult(
                    success=True,
                    duration_ms=(time.time() - start_time) * 1000,
                    message="Login successful",
                    user_id=user_id,
                    mfa_required=False
                )
            else:
                return LoginSimulationResult(
                    success=False,
                    duration_ms=(time.time() - start_time) * 1000,
                    message=f"Login failed: {login_response.status_code}"
                )
        
        except Exception as e:
            return LoginSimulationResult(
                success=False,
                duration_ms=(time.time() - start_time) * 1000,
                message=f"Login simulation error: {str(e)}"
            )

