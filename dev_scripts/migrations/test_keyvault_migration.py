#!/usr/bin/env python3
"""
Test script for Key Vault migration utility
"""

import os
import sys
import tempfile
import json
from unittest.mock import patch, MagicMock

# Add the parent directory to the path so we can import the migration module
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tools.keyvault_migration import KeyVaultMigrator, load_env_secrets

def test_connection():
    """Test basic Key Vault connection"""
    print("🧪 Testing Key Vault connection...")
    
    migrator = KeyVaultMigrator()
    if migrator.test_connection():
        print("✅ Connection test passed")
        return True
    else:
        print("❌ Connection test failed")
        return False

def test_secret_operations():
    """Test basic secret operations"""
    print("\n🧪 Testing secret operations...")
    
    migrator = KeyVaultMigrator()
    test_secret_name = "TEST-SECRET-MIGRATION"
    test_secret_value = "test-value-12345"
    
    try:
        # Test setting a secret
        print(f"  Setting test secret: {test_secret_name}")
        if not migrator.set_secret(test_secret_name, test_secret_value):
            print("❌ Failed to set test secret")
            return False
        
        # Test retrieving the secret
        print(f"  Retrieving test secret: {test_secret_name}")
        retrieved_value = migrator.get_secret(test_secret_name)
        if retrieved_value != test_secret_value:
            print(f"❌ Value mismatch. Expected: {test_secret_value}, Got: {retrieved_value}")
            return False
        
        print("✅ Secret operations test passed")
        
        # Clean up test secret
        print(f"  Cleaning up test secret: {test_secret_name}")
        migrator.delete_secret(test_secret_name)
        
        return True
        
    except Exception as e:
        print(f"❌ Secret operations test failed: {str(e)}")
        return False

def test_env_loading():
    """Test loading secrets from .env file"""
    print("\n🧪 Testing .env file loading...")
    
    try:
        env_secrets = load_env_secrets()
        print(f"  Found {len(env_secrets)} secrets in .env:")
        for key in env_secrets.keys():
            print(f"    - {key}")
        
        if env_secrets:
            print("✅ .env loading test passed")
            return True
        else:
            print("⚠️  No secrets found in .env (this might be expected)")
            return True
            
    except Exception as e:
        print(f"❌ .env loading test failed: {str(e)}")
        return False

def test_backup_restore():
    """Test backup and restore functionality"""
    print("\n🧪 Testing backup and restore...")
    
    migrator = KeyVaultMigrator()
    test_secrets = {
        "TEST-BACKUP-1": "value1",
        "TEST-BACKUP-2": "value2"
    }
    
    try:
        # Set test secrets
        for name, value in test_secrets.items():
            migrator.set_secret(name, value)
        
        # Create backup
        backup = migrator.backup_current_secrets(list(test_secrets.keys()))
        
        # Verify backup contains our secrets
        for name, value in test_secrets.items():
            if name not in backup or backup[name] != value:
                print(f"❌ Backup verification failed for {name}")
                return False
        
        # Delete secrets
        for name in test_secrets.keys():
            migrator.delete_secret(name)
        
        # Restore from backup
        if not migrator.restore_from_backup():
            print("❌ Restore failed")
            return False
        
        # Verify restoration
        for name, value in test_secrets.items():
            retrieved = migrator.get_secret(name)
            if retrieved != value:
                print(f"❌ Restore verification failed for {name}")
                return False
        
        print("✅ Backup and restore test passed")
        
        # Clean up
        for name in test_secrets.keys():
            migrator.delete_secret(name)
        
        # Clean up backup file
        if os.path.exists(migrator.backup_file):
            os.remove(migrator.backup_file)
        
        return True
        
    except Exception as e:
        print(f"❌ Backup and restore test failed: {str(e)}")
        return False

def run_all_tests():
    """Run all tests"""
    print("🚀 Running Key Vault Migration Tests")
    print("=" * 50)
    
    tests = [
        ("Connection Test", test_connection),
        ("Secret Operations Test", test_secret_operations),
        ("Environment Loading Test", test_env_loading),
        ("Backup/Restore Test", test_backup_restore)
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
        print("🎉 All tests passed! Migration utility is ready to use.")
        return True
    else:
        print("⚠️  Some tests failed. Please check the issues above.")
        return False

def check_current_keyvault_secrets():
    """Check what secrets are currently in Key Vault"""
    print("\n🔍 Checking current Key Vault secrets...")
    
    migrator = KeyVaultMigrator()
    if not migrator.test_connection():
        return
    
    try:
        secrets = list(migrator.client.list_properties_of_secrets())
        print(f"📋 Found {len(secrets)} secrets in Key Vault:")
        
        # Group by category for better readability
        categories = {
            'Azure': [],
            'Stripe': [],
            'Celery': [],
            'Database': [],
            'Support': [],
            'Other': []
        }
        
        for secret in secrets:
            name = secret.name
            if 'AZURE' in name:
                categories['Azure'].append(name)
            elif 'STRIPE' in name:
                categories['Stripe'].append(name)
            elif 'CELERY' in name:
                categories['Celery'].append(name)
            elif 'DATABASE' in name or 'DB' in name:
                categories['Database'].append(name)
            elif 'SUPPORT' in name:
                categories['Support'].append(name)
            else:
                categories['Other'].append(name)
        
        for category, secret_names in categories.items():
            if secret_names:
                print(f"\n  {category}:")
                for name in sorted(secret_names):
                    print(f"    - {name}")
                    
    except Exception as e:
        print(f"❌ Failed to list secrets: {str(e)}")

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "check":
        check_current_keyvault_secrets()
    else:
        run_all_tests()
