#!/usr/bin/env python3
"""
Verification script for session security implementation
Checks that all components are properly implemented without requiring running app
"""

import os
import sys
import importlib.util

def check_file_exists(filepath, description):
    """Check if a file exists"""
    if os.path.exists(filepath):
        print(f"  ✅ {description}: {filepath}")
        return True
    else:
        print(f"  ❌ {description} missing: {filepath}")
        return False

def check_imports_in_file(filepath, imports_to_check, description):
    """Check if specific imports exist in a file"""
    if not os.path.exists(filepath):
        print(f"  ❌ {description}: File not found")
        return False
    
    try:
        with open(filepath, 'r') as f:
            content = f.read()
        
        missing_imports = []
        for import_item in imports_to_check:
            if import_item not in content:
                missing_imports.append(import_item)
        
        if missing_imports:
            print(f"  ❌ {description}: Missing imports: {missing_imports}")
            return False
        else:
            print(f"  ✅ {description}: All required imports present")
            return True
            
    except Exception as e:
        print(f"  ❌ {description}: Error reading file: {str(e)}")
        return False

def check_config_in_file(filepath, configs_to_check, description):
    """Check if specific configurations exist in a file"""
    if not os.path.exists(filepath):
        print(f"  ❌ {description}: File not found")
        return False
    
    try:
        with open(filepath, 'r') as f:
            content = f.read()
        
        missing_configs = []
        for config_item in configs_to_check:
            if config_item not in content:
                missing_configs.append(config_item)
        
        if missing_configs:
            print(f"  ❌ {description}: Missing configurations: {missing_configs}")
            return False
        else:
            print(f"  ✅ {description}: All required configurations present")
            return True
            
    except Exception as e:
        print(f"  ❌ {description}: Error reading file: {str(e)}")
        return False

def verify_session_manager():
    """Verify session manager implementation"""
    print("🔧 Verifying Session Manager Implementation...")
    
    filepath = "app/utilities/session_manager.py"
    
    # Check file exists
    if not check_file_exists(filepath, "Session Manager"):
        return False
    
    # Check required methods
    required_methods = [
        "def regenerate_session",
        "def track_user_session", 
        "def invalidate_user_sessions",
        "def get_user_sessions",
        "def handle_role_change",
        "def force_logout_user"
    ]
    
    return check_config_in_file(filepath, required_methods, "Session Manager Methods")

def verify_app_config():
    """Verify app configuration for sessions"""
    print("\n⚙️  Verifying App Configuration...")
    
    filepath = "app/__init__.py"
    
    # Check Redis session configuration
    redis_configs = [
        "SESSION_TYPE'] = 'redis'",
        "SESSION_REDIS",
        "SESSION_PERMANENT'] = True",
        "PERMANENT_SESSION_LIFETIME",
        "SESSION_COOKIE_SECURE'] = True",
        "SESSION_COOKIE_HTTPONLY'] = True",
        "SESSION_COOKIE_SAMESITE'] = 'Lax'"
    ]
    
    config_result = check_config_in_file(filepath, redis_configs, "Redis Session Configuration")
    
    # Check security headers
    security_headers = [
        "X-Frame-Options",
        "X-Content-Type-Options",
        "X-XSS-Protection",
        "Content-Security-Policy",
        "Referrer-Policy"
    ]
    
    headers_result = check_config_in_file(filepath, security_headers, "Security Headers")
    
    return config_result and headers_result

def verify_login_integration():
    """Verify login route integration"""
    print("\n🔐 Verifying Login Integration...")
    
    filepath = "app/routes/login/login.py"
    
    # Check session manager import
    import_result = check_imports_in_file(
        filepath, 
        ["from app.utilities.session_manager import session_manager"],
        "Session Manager Import"
    )
    
    # Check session regeneration in perform_login
    integration_items = [
        "session_manager.regenerate_session",
        "session_manager.track_user_session"
    ]
    
    integration_result = check_config_in_file(filepath, integration_items, "Login Integration")
    
    return import_result and integration_result

def verify_admin_interface():
    """Verify admin session management interface"""
    print("\n👨‍💼 Verifying Admin Interface...")
    
    # Check admin route file
    admin_route_file = "app/routes/admin/session_management.py"
    admin_route_result = check_file_exists(admin_route_file, "Admin Session Routes")
    
    # Check admin template
    admin_template_file = "app/templates/administration/admin_sessions.html"
    admin_template_result = check_file_exists(admin_template_file, "Admin Session Template")
    
    # Check navigation integration
    nav_file = "app/templates/base.html"
    nav_integration = check_config_in_file(
        nav_file,
        ["session_admin_bp.view_sessions", "Session Management"],
        "Navigation Integration"
    )
    
    return admin_route_result and admin_template_result and nav_integration

def verify_dependencies():
    """Verify required dependencies"""
    print("\n📦 Verifying Dependencies...")
    
    try:
        import redis
        print("  ✅ Redis package available")
        redis_available = True
    except ImportError:
        print("  ❌ Redis package not available")
        redis_available = False
    
    try:
        import flask_session
        print("  ✅ Flask-Session package available")
        flask_session_available = True
    except ImportError:
        print("  ❌ Flask-Session package not available")
        flask_session_available = False
    
    return redis_available and flask_session_available

def verify_file_structure():
    """Verify file structure is correct"""
    print("\n📁 Verifying File Structure...")
    
    required_files = [
        ("app/__init__.py", "Main App Configuration"),
        ("app/utilities/session_manager.py", "Session Manager"),
        ("app/routes/login/login.py", "Login Routes"),
        ("app/routes/admin/session_management.py", "Admin Session Routes"),
        ("app/templates/administration/admin_sessions.html", "Admin Template"),
        ("app/templates/base.html", "Base Template")
    ]
    
    all_exist = True
    for filepath, description in required_files:
        if not check_file_exists(filepath, description):
            all_exist = False
    
    return all_exist

def main():
    """Run all verification checks"""
    print("🔒 Session Security Implementation Verification")
    print("=" * 60)
    
    checks = [
        ("File Structure", verify_file_structure),
        ("Dependencies", verify_dependencies),
        ("Session Manager", verify_session_manager),
        ("App Configuration", verify_app_config),
        ("Login Integration", verify_login_integration),
        ("Admin Interface", verify_admin_interface),
    ]
    
    results = []
    for check_name, check_func in checks:
        try:
            result = check_func()
            results.append((check_name, result))
        except Exception as e:
            print(f"  ❌ Check {check_name} failed with exception: {str(e)}")
            results.append((check_name, False))
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 Verification Results:")
    
    passed = 0
    total = len(results)
    
    for check_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"  {status} {check_name}")
        if result:
            passed += 1
    
    print(f"\n🎯 Overall: {passed}/{total} checks passed")
    
    if passed == total:
        print("🎉 All session security implementations are correctly in place!")
        print("\n📋 Next Steps:")
        print("  1. Start the application to test Redis connectivity")
        print("  2. Test login/logout functionality")
        print("  3. Access admin session management at /admin/sessions")
        print("  4. Verify security headers in browser developer tools")
        return True
    else:
        print("⚠️  Some session security implementations need attention.")
        return False

if __name__ == "__main__":
    main()
