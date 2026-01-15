#!/usr/bin/env python3
"""
Email Configuration Diagnostic Script
"""

import os
import smtplib
from email.mime.text import MIMEText
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def test_env_variables():
    """Test if environment variables are loaded correctly"""
    print("🔍 Environment Variables Check:")
    
    mail_vars = [
        'MAIL_SERVER',
        'MAIL_PORT', 
        'MAIL_USE_TLS',
        'MAIL_USE_SSL',
        'MAIL_USERNAME',
        'MAIL_PASSWORD',
        'MAIL_DEFAULT_SENDER'
    ]
    
    for var in mail_vars:
        value = os.getenv(var)
        if var == 'MAIL_PASSWORD':
            display_value = '*' * len(value) if value else 'NOT SET'
        else:
            display_value = value or 'NOT SET'
        print(f"   {var}: {display_value}")
    
    return all(os.getenv(var) for var in mail_vars)

def test_smtp_direct():
    """Test SMTP connection directly with the specified credentials"""
    print("\n📡 Testing SMTP Connection:")
    
    # Use the exact credentials you provided
    smtp_server = 'smtp.ionos.co.uk'
    smtp_port = 587
    username = 'support@wegweiser.tech'
    password = '<enter password>'
    
    try:
        print(f"   Connecting to {smtp_server}:{smtp_port}...")
        server = smtplib.SMTP(smtp_server, smtp_port)
        
        print("   Starting TLS...")
        server.starttls()
        
        print("   Attempting authentication...")
        server.login(username, password)
        
        print("   ✅ Authentication successful!")
        
        # Test creating a simple message
        msg = MIMEText("Test message")
        msg['Subject'] = 'Test Email'
        msg['From'] = username
        msg['To'] = 'test@example.com'
        
        print("   ✅ Message creation successful!")
        
        server.quit()
        return True
        
    except smtplib.SMTPAuthenticationError as e:
        print(f"   ❌ Authentication failed: {e}")
        return False
    except smtplib.SMTPConnectError as e:
        print(f"   ❌ Connection failed: {e}")
        return False
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return False

def test_flask_mail_config():
    """Test Flask-Mail configuration"""
    print("\n🔧 Testing Flask-Mail Configuration:")
    
    try:
        from app import create_app
        from flask_mail import Message
        from app import mail
        
        app = create_app()
        with app.app_context():
            print("   Flask app created successfully")
            
            # Check Flask-Mail configuration
            config_vars = [
                'MAIL_SERVER',
                'MAIL_PORT',
                'MAIL_USE_TLS', 
                'MAIL_USE_SSL',
                'MAIL_USERNAME',
                'MAIL_PASSWORD',
                'MAIL_DEFAULT_SENDER'
            ]
            
            print("   Flask-Mail Configuration:")
            for var in config_vars:
                value = app.config.get(var)
                if var == 'MAIL_PASSWORD':
                    display_value = '*' * len(str(value)) if value else 'NOT SET'
                else:
                    display_value = value or 'NOT SET'
                print(f"     {var}: {display_value}")
            
            # Try to create a test message
            msg = Message(
                subject="Test Email",
                recipients=["test@example.com"],
                body="This is a test email",
                sender=app.config['MAIL_DEFAULT_SENDER']
            )
            
            print("   ✅ Flask-Mail message creation successful!")
            
            # Note: We won't actually send the email to avoid spam
            print("   📧 Email sending test skipped (would send to test@example.com)")
            
            return True
            
    except Exception as e:
        print(f"   ❌ Flask-Mail test failed: {e}")
        return False

def main():
    print("🧪 Wegweiser Email Configuration Diagnostic")
    print("=" * 60)
    
    # Test 1: Environment variables
    env_ok = test_env_variables()
    
    # Test 2: Direct SMTP connection
    smtp_ok = test_smtp_direct()
    
    # Test 3: Flask-Mail configuration
    flask_ok = test_flask_mail_config()
    
    print("\n" + "=" * 60)
    print("📊 Summary:")
    print(f"   Environment Variables: {'✅ OK' if env_ok else '❌ FAIL'}")
    print(f"   SMTP Connection: {'✅ OK' if smtp_ok else '❌ FAIL'}")
    print(f"   Flask-Mail Config: {'✅ OK' if flask_ok else '❌ FAIL'}")
    
    if all([env_ok, smtp_ok, flask_ok]):
        print("\n🎉 All tests passed! Email should be working.")
    else:
        print("\n⚠️  Some tests failed. Check the output above for details.")

if __name__ == "__main__":
    main()
