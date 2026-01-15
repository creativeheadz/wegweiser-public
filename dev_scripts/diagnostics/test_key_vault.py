# Filepath: app/test_key_vault.py

import os
from azure.identity import ManagedIdentityCredential
from azure.keyvault.secrets import SecretClient
import logging
from app.utilities.app_logging_helper import log_with_route

# Azure Key Vault configuration
key_vault_url = "https://wegweiserkv.vault.azure.net/"

def get_secret(secret_name):
    try:
        log_with_route(logging.INFO, f"Attempting to retrieve secret '{secret_name}' using ManagedIdentityCredential", 
                      source_type="KeyVault")
        
        credential = ManagedIdentityCredential()
        client = SecretClient(vault_url=key_vault_url, credential=credential)
        secret_value = client.get_secret(secret_name).value
        
        log_with_route(logging.INFO, f"Successfully retrieved secret '{secret_name}'", 
                      source_type="KeyVault")
        return secret_value
    except Exception as e:
        log_with_route(logging.ERROR, f"Failed to retrieve secret '{secret_name}': {str(e)}", 
                      source_type="KeyVault")
        raise

if __name__ == "__main__":
    try:
        database_url = get_secret("DatabaseUrl")
        log_with_route(logging.INFO, 
                      f"Successfully retrieved DatabaseUrl: {database_url[:10]}...", 
                      source_type="KeyVault")  # Only log first 10 chars for security
    except Exception as e:
        log_with_route(logging.ERROR, 
                      f"Failed to retrieve DatabaseUrl: {str(e)}", 
                      source_type="KeyVault")