# Filepath: app/utilities/secret_manager.py
"""
Secret Manager - Abstraction layer for multiple secret backends

Supports:
- Local .env files (development)
- Azure Key Vault (production Azure)
- OpenBao (self-hosted alternative, compatible with HashiCorp Vault API)
- Environment variables (fallback)

Implements automatic fallback chain with health checks.
"""

import os
import logging
from functools import lru_cache
from typing import Optional, Dict, Any
from abc import ABC, abstractmethod
from contextlib import contextmanager

logger = logging.getLogger(__name__)


class SecretBackendError(Exception):
    """Custom exception for secret backend errors"""
    pass


class SecretBackend(ABC):
    """Abstract base class for secret backends"""

    @abstractmethod
    def get_secret(self, secret_name: str) -> Optional[str]:
        """Retrieve a secret. Return None if not found."""
        pass

    @abstractmethod
    def health_check(self) -> bool:
        """Check if backend is available and functional"""
        pass

    @abstractmethod
    def get_backend_name(self) -> str:
        """Return human-readable backend name"""
        pass


class LocalEnvBackend(SecretBackend):
    """Local .env file backend"""

    def __init__(self, env_dict: Dict[str, str] = None):
        """Initialize with optional env dict (for testing)"""
        self.env_dict = env_dict or os.environ

    def get_secret(self, secret_name: str) -> Optional[str]:
        """Get secret from environment variables"""
        value = self.env_dict.get(secret_name.upper())
        if value:
            logger.debug(f"Retrieved {secret_name} from local environment")
        return value

    def health_check(self) -> bool:
        """Local env is always available"""
        return True

    def get_backend_name(self) -> str:
        return "Local Environment Variables"


class AzureKeyVaultBackend(SecretBackend):
    """Azure Key Vault backend"""

    def __init__(self):
        """Initialize Azure Key Vault client"""
        self._client = None
        self._vault_url = os.getenv("AZURE_KEY_VAULT_ENDPOINT", "https://wegweiserkv.vault.azure.net/")
        self._initialized = False
        self._health_status = False

    def _init_client(self):
        """Lazy initialize Azure Key Vault client"""
        if self._initialized:
            return

        try:
            from azure.identity import ManagedIdentityCredential
            from azure.keyvault.secrets import SecretClient

            credential = ManagedIdentityCredential()
            self._client = SecretClient(vault_url=self._vault_url, credential=credential)
            self._initialized = True
            self._health_status = True
            logger.info(f"Azure Key Vault client initialized: {self._vault_url}")
        except ImportError:
            logger.error("Azure SDK packages not installed (azure-identity, azure-keyvault-secrets)")
            self._health_status = False
            self._initialized = True
        except Exception as e:
            logger.warning(f"Failed to initialize Azure Key Vault: {str(e)}")
            self._health_status = False
            self._initialized = True

    def get_secret(self, secret_name: str) -> Optional[str]:
        """Get secret from Azure Key Vault"""
        if not self._initialized:
            self._init_client()

        if not self._client:
            return None

        try:
            secret = self._client.get_secret(secret_name)
            logger.debug(f"Retrieved {secret_name} from Azure Key Vault")
            return secret.value
        except Exception as e:
            logger.warning(f"Failed to retrieve {secret_name} from Azure Key Vault: {str(e)}")
            return None

    def health_check(self) -> bool:
        """Check Azure Key Vault availability"""
        if not self._initialized:
            self._init_client()

        if not self._client:
            return False

        try:
            # Try to get properties to verify connectivity
            self._client.get_key_vault_properties()
            return True
        except Exception as e:
            logger.warning(f"Azure Key Vault health check failed: {str(e)}")
            return False

    def get_backend_name(self) -> str:
        return f"Azure Key Vault ({self._vault_url})"


class OpenBaoBackend(SecretBackend):
    """OpenBao/HashiCorp Vault compatible backend"""

    def __init__(self):
        """Initialize OpenBao client"""
        self._client = None
        self._vault_addr = os.getenv("OPENBAO_ADDR", "http://localhost:8200")
        self._token = os.getenv("OPENBAO_TOKEN")
        self._secret_path = os.getenv("OPENBAO_SECRET_PATH", "secret/wegweiser")
        self._initialized = False
        self._health_status = False

    def _init_client(self):
        """Lazy initialize OpenBao client"""
        if self._initialized:
            return

        try:
            import hvac

            if not self._token:
                logger.error("OPENBAO_TOKEN environment variable not set")
                self._initialized = True
                self._health_status = False
                return

            self._client = hvac.Client(
                url=self._vault_addr,
                token=self._token,
                verify=os.getenv("OPENBAO_VERIFY_SSL", "true").lower() in ['true', '1']
            )
            self._initialized = True
            self._health_status = True
            logger.info(f"OpenBao client initialized: {self._vault_addr}/{self._secret_path}")
        except ImportError:
            logger.error("hvac package not installed for OpenBao support")
            self._health_status = False
            self._initialized = True
        except Exception as e:
            logger.warning(f"Failed to initialize OpenBao client: {str(e)}")
            self._health_status = False
            self._initialized = True

    def get_secret(self, secret_name: str) -> Optional[str]:
        """Get secret from OpenBao"""
        if not self._initialized:
            self._init_client()

        if not self._client:
            return None

        try:
            # Try direct secret first (v2 KV engine)
            path = f"{self._secret_path}/{secret_name.lower()}"
            response = self._client.secrets.kv.v2.read_secret_version(path=secret_name.lower())
            value = response['data']['data'].get('value')
            if value:
                logger.debug(f"Retrieved {secret_name} from OpenBao ({path})")
                return value
        except Exception as e:
            logger.debug(f"Could not retrieve {secret_name} from OpenBao: {str(e)}")

        return None

    def health_check(self) -> bool:
        """Check OpenBao availability"""
        if not self._initialized:
            self._init_client()

        if not self._client:
            return False

        try:
            self._client.sys.is_sealed()
            return True
        except Exception as e:
            logger.warning(f"OpenBao health check failed: {str(e)}")
            return False

    def get_backend_name(self) -> str:
        return f"OpenBao ({self._vault_addr})"


class SecretManager:
    """
    Unified secret manager with fallback chain

    Default chain:
    1. Azure Key Vault (if configured and available)
    2. OpenBao (if configured and available)
    3. Local environment variables (always available)

    Custom chains can be specified via constructor.
    """

    def __init__(self, backends: list = None, cache_enabled: bool = True):
        """
        Initialize SecretManager

        Args:
            backends: List of SecretBackend instances in fallback order
            cache_enabled: Enable LRU caching of secrets (default: True)
        """
        self.cache_enabled = cache_enabled
        self._secret_cache = {}
        self._health_cache = {}

        if backends is None:
            # Build default fallback chain
            self.backends = self._build_default_chain()
        else:
            self.backends = backends

        logger.info(f"SecretManager initialized with {len(self.backends)} backend(s)")
        for backend in self.backends:
            logger.info(f"  - {backend.get_backend_name()}")

    def _build_default_chain(self) -> list:
        """Build default backend chain"""
        backends = []

        # Try Azure Key Vault first (if environment suggests it)
        if os.getenv("AZURE_KEY_VAULT_ENDPOINT") or os.getenv("AZURE_USE_KEYVAULT", "").lower() == "true":
            backends.append(AzureKeyVaultBackend())
            logger.info("Azure Key Vault added to backend chain")

        # Try OpenBao if configured
        if os.getenv("OPENBAO_ADDR") or os.getenv("OPENBAO_TOKEN"):
            backends.append(OpenBaoBackend())
            logger.info("OpenBao added to backend chain")

        # Always add local environment as fallback
        backends.append(LocalEnvBackend())

        return backends if backends else [LocalEnvBackend()]

    def get_secret(self, secret_name: str, default: str = None, required: bool = False) -> Optional[str]:
        """
        Retrieve a secret from the fallback chain

        Args:
            secret_name: Name of the secret to retrieve
            default: Default value if not found
            required: Raise error if secret not found

        Returns:
            Secret value or default

        Raises:
            SecretBackendError: If required=True and secret not found
        """
        # Check cache first
        if self.cache_enabled and secret_name in self._secret_cache:
            logger.debug(f"Retrieved {secret_name} from cache")
            return self._secret_cache[secret_name]

        # Try each backend in order
        for backend in self.backends:
            try:
                value = backend.get_secret(secret_name)
                if value is not None:
                    # Cache the result
                    if self.cache_enabled:
                        self._secret_cache[secret_name] = value
                    logger.info(f"Retrieved {secret_name} from {backend.get_backend_name()}")
                    return value
            except Exception as e:
                logger.warning(f"Error retrieving {secret_name} from {backend.get_backend_name()}: {str(e)}")
                continue

        # Secret not found in any backend
        if required:
            raise SecretBackendError(f"Required secret '{secret_name}' not found in any backend")

        logger.warning(f"Secret {secret_name} not found in any backend, using default")
        return default

    def get_secrets_dict(self, secret_names: list, required: bool = False) -> Dict[str, Optional[str]]:
        """
        Retrieve multiple secrets at once

        Args:
            secret_names: List of secret names to retrieve
            required: Raise error if any secret not found

        Returns:
            Dictionary of secret_name -> value
        """
        return {
            name: self.get_secret(name, required=required)
            for name in secret_names
        }

    def health_check(self) -> Dict[str, bool]:
        """
        Check health of all backends

        Returns:
            Dictionary of backend_name -> health_status
        """
        results = {}
        for backend in self.backends:
            try:
                status = backend.health_check()
                results[backend.get_backend_name()] = status
            except Exception as e:
                logger.error(f"Health check failed for {backend.get_backend_name()}: {str(e)}")
                results[backend.get_backend_name()] = False
        return results

    def get_available_backends(self) -> list:
        """Get list of currently available backends"""
        available = []
        for backend in self.backends:
            if backend.health_check():
                available.append(backend.get_backend_name())
        return available

    def clear_cache(self):
        """Clear the secret cache"""
        self._secret_cache.clear()
        logger.info("Secret cache cleared")


# Global instance - lazy loaded
_secret_manager = None


def get_secret_manager() -> SecretManager:
    """Get or create the global SecretManager instance"""
    global _secret_manager
    if _secret_manager is None:
        _secret_manager = SecretManager()
    return _secret_manager


# Convenience functions for Flask integration
def get_secret(secret_name: str, default: str = None, required: bool = False) -> Optional[str]:
    """Convenience function to get a secret from the global manager"""
    manager = get_secret_manager()
    return manager.get_secret(secret_name, default=default, required=required)


def get_secrets(secret_names: list, required: bool = False) -> Dict[str, Optional[str]]:
    """Convenience function to get multiple secrets from the global manager"""
    manager = get_secret_manager()
    return manager.get_secrets_dict(secret_names, required=required)
