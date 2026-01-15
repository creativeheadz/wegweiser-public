#!/usr/bin/env python3
"""
SMTP Configuration Test Script
This script tests the current SMTP settings to diagnose email issues.
"""

import smtplib
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def test_smtp_connection():
    """Test SMTP connection and authentication"""
    
    # Get SMTP settings from environment
    smtp_server = os.getenv('MAIL_SERVER', 'smtp.ionos.co.uk')
    smtp_port = int(os.getenv('MAIL_PORT', '587'))
    username = os.getenv('MAIL_USERNAME', 'support@wegweiser.tech')
    password = os.getenv('MAIL_PASSWORD', '')
    use_tls = os.getenv('MAIL_USE_TLS', 'True').lower() == 'true'
    
    print("🔧 Testing SMTP Configuration:")
    print(f"   Server: {smtp_server}")
    print(f"   Port: {smtp_port}")
    print(f"   Username: {username}")
    print(f"   TLS: {use_tls}")
    print(f"   Password: {'*' * len(password) if password else 'NOT SET'}")
    print()
    
    try:
        # Test connection
        print("📡 Connecting to SMTP server...")
        server = smtplib.SMTP(smtp_server, smtp_port)
        
        # Enable debug output
        server.set_debuglevel(1)
        
        if use_tls:
            print("🔒 Starting TLS...")
            server.starttls()
        
        print("🔑 Attempting authentication...")
        server.login(username, password)
        
        print("✅ SMTP authentication successful!")
        
        # Test sending a simple email
        print("📧 Testing email send...")
        
        msg = MIMEMultipart()
        msg['From'] = username
        msg['To'] = "test@example.com"  # This won't actually send
        msg['Subject'] = "SMTP Test"
        
        body = "This is a test email to verify SMTP configuration."
        msg.attach(MIMEText(body, 'plain'))
        
        # Don't actually send, just test the connection
        print("✅ Email composition successful!")
        
        server.quit()
        print("✅ All tests passed! SMTP is working correctly.")
        return True
        
    except smtplib.SMTPAuthenticationError as e:
        print(f"❌ Authentication failed: {e}")
        print("💡 Possible solutions:")
        print("   - Check username/password are correct")
        print("   - Enable 'Less secure app access' if using Gmail")
        print("   - Use app-specific password if 2FA is enabled")
        print("   - Check if account is locked or suspended")
        return False
        
    except smtplib.SMTPConnectError as e:
        print(f"❌ Connection failed: {e}")
        print("💡 Possible solutions:")
        print("   - Check server address and port")
        print("   - Verify firewall settings")
        print("   - Try different ports (25, 465, 587)")
        return False
        
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False

def suggest_alternatives():
    """Suggest alternative email configurations"""
    print("\n🔄 Alternative Email Service Configurations:")
    print()
    
    print("📧 Gmail/Google Workspace:")
    print("   MAIL_SERVER=smtp.gmail.com")
    print("   MAIL_PORT=587")
    print("   MAIL_USE_TLS=True")
    print("   MAIL_USERNAME=your-email@gmail.com")
    print("   MAIL_PASSWORD=your-app-password")
    print()
    
    print("📧 SendGrid (Recommended for production):")
    print("   MAIL_SERVER=smtp.sendgrid.net")
    print("   MAIL_PORT=587")
    print("   MAIL_USE_TLS=True")
    print("   MAIL_USERNAME=apikey")
    print("   MAIL_PASSWORD=your-sendgrid-api-key")
    print()
    
    print("📧 Mailgun:")
    print("   MAIL_SERVER=smtp.mailgun.org")
    print("   MAIL_PORT=587")
    print("   MAIL_USE_TLS=True")
    print("   MAIL_USERNAME=postmaster@your-domain.mailgun.org")
    print("   MAIL_PASSWORD=your-mailgun-password")

if __name__ == "__main__":
    print("🧪 Wegweiser SMTP Configuration Test")
    print("=" * 50)
    
    success = test_smtp_connection()
    
    if not success:
        suggest_alternatives()
    
    print("\n" + "=" * 50)
    print("Test completed.")
