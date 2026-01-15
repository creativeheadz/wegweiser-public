#!/usr/bin/env python3
"""
Test script to verify the application can start with Key Vault secrets
"""

import sys
import os
import logging

# Add the parent directory to the path so we can import the app
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def test_app_startup():
    """Test that the Flask app can start with Key Vault configuration"""
    print("🧪 Testing Flask app startup with Key Vault secrets...")
    
    try:
        # Import and create the Flask app
        from app import create_app
        
        print("  Creating Flask app...")
        app = create_app()
        
        print("  Testing app configuration...")
        with app.app_context():
            # Check that critical secrets are loaded
            secret_key = app.config.get('SECRET_KEY')
            api_key = app.config.get('API_KEY')
            
            if not secret_key:
                print("❌ SECRET_KEY not found in app config")
                return False
            
            if not api_key:
                print("❌ API_KEY not found in app config")
                return False
            
            print(f"  ✅ SECRET_KEY loaded: {secret_key[:10]}...")
            print(f"  ✅ API_KEY loaded: {api_key[:10]}...")
            
            # Test other Key Vault secrets
            azure_openai_key = app.config.get('AZURE_OPENAI_API_KEY')
            if azure_openai_key:
                print(f"  ✅ AZURE_OPENAI_API_KEY loaded: {azure_openai_key[:10]}...")
            
            database_url = app.config.get('SQLALCHEMY_DATABASE_URI')
            if database_url:
                print(f"  ✅ Database URL loaded: {database_url[:20]}...")
            
        print("✅ Flask app startup test passed!")
        return True
        
    except Exception as e:
        print(f"❌ Flask app startup test failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def test_secret_retrieval():
    """Test direct secret retrieval from Key Vault"""
    print("\n🧪 Testing direct Key Vault secret retrieval...")
    
    try:
        from app import get_secret
        
        # Test retrieving the secrets we just migrated
        secrets_to_test = ['SECRETKEY', 'APIKEY']
        
        for secret_name in secrets_to_test:
            print(f"  Testing {secret_name}...")
            value = get_secret(secret_name)
            if value:
                print(f"  ✅ {secret_name}: {value[:10]}...")
            else:
                print(f"  ❌ {secret_name}: Failed to retrieve")
                return False
        
        print("✅ Direct secret retrieval test passed!")
        return True
        
    except Exception as e:
        print(f"❌ Direct secret retrieval test failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Run all tests"""
    print("🚀 Testing Application with Key Vault Integration")
    print("=" * 60)
    
    # Suppress some logging for cleaner output
    logging.getLogger('azure').setLevel(logging.WARNING)
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    
    tests = [
        ("Direct Secret Retrieval", test_secret_retrieval),
        ("Flask App Startup", test_app_startup)
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        try:
            if test_func():
                passed += 1
            else:
                print(f"❌ {test_name} failed")
        except Exception as e:
            print(f"❌ {test_name} failed with exception: {str(e)}")
    
    print(f"\n📊 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! Key Vault integration is working.")
        return True
    else:
        print("⚠️  Some tests failed. Check the issues above.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
