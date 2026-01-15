#!/usr/bin/env python3
"""
Azure Key Vault Secret Migration Utility

This script helps migrate secrets from .env files to Azure Key Vault
with testing and rollback capabilities.
"""

import os
import sys
import json
import logging
from typing import Dict, List, Optional, Tuple
from azure.identity import ManagedIdentityCredential
from azure.keyvault.secrets import SecretClient
from azure.core.exceptions import ResourceNotFoundError, HttpResponseError
from dotenv import load_dotenv, dotenv_values

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class KeyVaultMigrator:
    """Handles migration of secrets to Azure Key Vault"""
    
    def __init__(self, key_vault_url: str = "https://wegweiserkv.vault.azure.net/"):
        self.key_vault_url = key_vault_url
        self.credential = ManagedIdentityCredential()
        self.client = SecretClient(vault_url=key_vault_url, credential=self.credential)
        self.backup_file = "keyvault_migration_backup.json"
        
    def test_connection(self) -> bool:
        """Test connection to Key Vault"""
        try:
            # Try to list secrets (this requires minimal permissions)
            list(self.client.list_properties_of_secrets())
            logger.info("✅ Successfully connected to Key Vault")
            return True
        except Exception as e:
            logger.error(f"❌ Failed to connect to Key Vault: {str(e)}")
            return False
    
    def set_secret(self, secret_name: str, secret_value: str) -> bool:
        """Set a secret in Key Vault"""
        try:
            self.client.set_secret(secret_name, secret_value)
            logger.info(f"✅ Successfully set secret: {secret_name}")
            return True
        except Exception as e:
            logger.error(f"❌ Failed to set secret {secret_name}: {str(e)}")
            return False
    
    def get_secret(self, secret_name: str) -> Optional[str]:
        """Get a secret from Key Vault"""
        try:
            secret = self.client.get_secret(secret_name)
            logger.info(f"✅ Successfully retrieved secret: {secret_name}")
            return secret.value
        except ResourceNotFoundError:
            logger.warning(f"⚠️  Secret not found: {secret_name}")
            return None
        except Exception as e:
            logger.error(f"❌ Failed to retrieve secret {secret_name}: {str(e)}")
            return None
    
    def delete_secret(self, secret_name: str) -> bool:
        """Delete a secret from Key Vault"""
        try:
            self.client.begin_delete_secret(secret_name)
            logger.info(f"✅ Successfully deleted secret: {secret_name}")
            return True
        except ResourceNotFoundError:
            logger.warning(f"⚠️  Secret not found for deletion: {secret_name}")
            return True  # Consider this success since it's already gone
        except Exception as e:
            logger.error(f"❌ Failed to delete secret {secret_name}: {str(e)}")
            return False
    
    def backup_current_secrets(self, secret_names: List[str]) -> Dict[str, str]:
        """Backup current secrets from Key Vault"""
        backup = {}
        for secret_name in secret_names:
            value = self.get_secret(secret_name)
            if value:
                backup[secret_name] = value
        
        # Save backup to file
        with open(self.backup_file, 'w') as f:
            json.dump(backup, f, indent=2)
        
        logger.info(f"✅ Backup saved to {self.backup_file}")
        return backup
    
    def restore_from_backup(self) -> bool:
        """Restore secrets from backup file"""
        try:
            if not os.path.exists(self.backup_file):
                logger.error(f"❌ Backup file {self.backup_file} not found")
                return False
            
            with open(self.backup_file, 'r') as f:
                backup = json.load(f)
            
            success = True
            for secret_name, secret_value in backup.items():
                if not self.set_secret(secret_name, secret_value):
                    success = False
            
            return success
        except Exception as e:
            logger.error(f"❌ Failed to restore from backup: {str(e)}")
            return False

def load_env_secrets() -> Dict[str, str]:
    """Load secrets from .env file"""
    env_path = os.path.join(os.path.dirname(__file__), '..', '.env')
    load_dotenv(env_path)
    env_vars = dotenv_values(env_path)
    
    # Define which secrets should be migrated
    secrets_to_migrate = {
        'SECRET_KEY': 'SECRETKEY',
        'API_KEY': 'APIKEY', 
        'RECAPTCHA_PUBLIC_KEY': 'RECAPTCHAPUBLICKEY',
        'RECAPTCHA_PRIVATE_KEY': 'RECAPTCHAPRIVATEKEY',
        'MAIL_SERVER': 'MAILSERVER',
        'MAIL_USERNAME': 'MAILUSERNAME',
        'MAIL_PASSWORD': 'MAILPASSWORD',
        'MAIL_DEFAULT_SENDER': 'MAILDEFAULTSENDER',
        'REMOTE_LOGGING_PASSWORD': 'REMOTELOGGINGPASSWORD',
        'IP_BLOCKER_REDIS_PASSWORD': 'IPBLOCKERREDISPASSWORD',
        'ADMIN_REDIS_PASSWORD': 'ADMINREDISPASSWORD',
        'BRAVE_SEARCH_API_KEY': 'BRAVESEARCHAPIKEY'
    }
    
    result = {}
    for env_key, kv_key in secrets_to_migrate.items():
        if env_key in env_vars and env_vars[env_key]:
            result[kv_key] = env_vars[env_key]
    
    return result

def migrate_secret(migrator: KeyVaultMigrator, env_key: str, kv_key: str, env_value: str) -> bool:
    """Migrate a single secret with testing"""
    logger.info(f"🔄 Migrating {env_key} -> {kv_key}")
    
    # Backup existing value if it exists
    existing_value = migrator.get_secret(kv_key)
    
    # Set the new secret
    if not migrator.set_secret(kv_key, env_value):
        return False
    
    # Test retrieval
    retrieved_value = migrator.get_secret(kv_key)
    if retrieved_value != env_value:
        logger.error(f"❌ Value mismatch for {kv_key}. Expected: {env_value[:10]}..., Got: {retrieved_value[:10] if retrieved_value else 'None'}...")
        return False
    
    logger.info(f"✅ Successfully migrated and verified {env_key}")
    return True

def main():
    """Main migration function"""
    print("🚀 Azure Key Vault Secret Migration Utility")
    print("=" * 50)
    
    # Initialize migrator
    migrator = KeyVaultMigrator()
    
    # Test connection
    if not migrator.test_connection():
        print("❌ Cannot connect to Key Vault. Exiting.")
        sys.exit(1)
    
    # Load secrets from .env
    env_secrets = load_env_secrets()
    if not env_secrets:
        print("⚠️  No secrets found to migrate")
        return
    
    print(f"📋 Found {len(env_secrets)} secrets to migrate:")
    for kv_key in env_secrets.keys():
        print(f"  - {kv_key}")
    
    # Ask for confirmation
    response = input("\n🤔 Do you want to proceed with migration? (y/N): ")
    if response.lower() != 'y':
        print("❌ Migration cancelled")
        return
    
    # Backup existing secrets
    print("\n💾 Creating backup of existing secrets...")
    migrator.backup_current_secrets(list(env_secrets.keys()))
    
    # Migrate secrets one by one
    print("\n🔄 Starting migration...")
    success_count = 0
    
    for env_key, kv_key in [
        ('SECRET_KEY', 'SECRETKEY'),
        ('API_KEY', 'APIKEY'),
        ('RECAPTCHA_PUBLIC_KEY', 'RECAPTCHAPUBLICKEY'),
        ('RECAPTCHA_PRIVATE_KEY', 'RECAPTCHAPRIVATEKEY'),
        ('MAIL_SERVER', 'MAILSERVER'),
        ('MAIL_USERNAME', 'MAILUSERNAME'),
        ('MAIL_PASSWORD', 'MAILPASSWORD'),
        ('MAIL_DEFAULT_SENDER', 'MAILDEFAULTSENDER'),
        ('REMOTE_LOGGING_PASSWORD', 'REMOTELOGGINGPASSWORD'),
        ('IP_BLOCKER_REDIS_PASSWORD', 'IPBLOCKERREDISPASSWORD'),
        ('ADMIN_REDIS_PASSWORD', 'ADMINREDISPASSWORD'),
        ('BRAVE_SEARCH_API_KEY', 'BRAVESEARCHAPIKEY')
    ]:
        if kv_key in env_secrets:
            if migrate_secret(migrator, env_key, kv_key, env_secrets[kv_key]):
                success_count += 1
            else:
                print(f"❌ Failed to migrate {env_key}")
                break
    
    print(f"\n📊 Migration Summary:")
    print(f"  ✅ Successfully migrated: {success_count}/{len(env_secrets)}")
    
    if success_count == len(env_secrets):
        print("\n🎉 All secrets migrated successfully!")
        print("📝 Next steps:")
        print("  1. Update app/__init__.py to use get_secret() for migrated secrets")
        print("  2. Test application functionality")
        print("  3. Remove secrets from .env file")
    else:
        print("\n⚠️  Some secrets failed to migrate. Check logs above.")
        print("💡 You can restore from backup using the restore function if needed.")

def test_single_secret(secret_name: str):
    """Test retrieval of a single secret"""
    migrator = KeyVaultMigrator()

    if not migrator.test_connection():
        print("❌ Cannot connect to Key Vault")
        return False

    value = migrator.get_secret(secret_name)
    if value:
        print(f"✅ Secret {secret_name} retrieved successfully: {value[:10]}...")
        return True
    else:
        print(f"❌ Failed to retrieve secret {secret_name}")
        return False

def list_all_secrets():
    """List all secrets in Key Vault"""
    migrator = KeyVaultMigrator()

    if not migrator.test_connection():
        print("❌ Cannot connect to Key Vault")
        return

    try:
        secrets = list(migrator.client.list_properties_of_secrets())
        print(f"📋 Found {len(secrets)} secrets in Key Vault:")
        for secret in secrets:
            print(f"  - {secret.name}")
    except Exception as e:
        print(f"❌ Failed to list secrets: {str(e)}")

def interactive_mode():
    """Interactive mode for individual secret operations"""
    migrator = KeyVaultMigrator()

    if not migrator.test_connection():
        print("❌ Cannot connect to Key Vault. Exiting.")
        return

    while True:
        print("\n🔧 Interactive Key Vault Operations")
        print("1. Test secret retrieval")
        print("2. Set a secret")
        print("3. List all secrets")
        print("4. Delete a secret")
        print("5. Run full migration")
        print("6. Restore from backup")
        print("0. Exit")

        choice = input("\nSelect an option (0-6): ")

        if choice == "0":
            break
        elif choice == "1":
            secret_name = input("Enter secret name: ")
            test_single_secret(secret_name)
        elif choice == "2":
            secret_name = input("Enter secret name: ")
            secret_value = input("Enter secret value: ")
            migrator.set_secret(secret_name, secret_value)
        elif choice == "3":
            list_all_secrets()
        elif choice == "4":
            secret_name = input("Enter secret name to delete: ")
            confirm = input(f"Are you sure you want to delete '{secret_name}'? (y/N): ")
            if confirm.lower() == 'y':
                migrator.delete_secret(secret_name)
        elif choice == "5":
            main()
        elif choice == "6":
            migrator.restore_from_backup()
        else:
            print("❌ Invalid option")

if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        if sys.argv[1] == "interactive":
            interactive_mode()
        elif sys.argv[1] == "test" and len(sys.argv) > 2:
            test_single_secret(sys.argv[2])
        elif sys.argv[1] == "list":
            list_all_secrets()
        else:
            print("Usage: python keyvault_migration.py [interactive|test <secret_name>|list]")
    else:
        main()
