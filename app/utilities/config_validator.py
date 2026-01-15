# Filepath: app/utilities/config_validator.py
"""
Configuration Validator - Validates Wegweiser configuration at startup

Checks for:
- Required environment variables
- Database connectivity
- Redis connectivity
- Secret backend accessibility
- AI provider configuration
- Service dependencies
"""

import os
import sys
import logging
from typing import Dict, List, Tuple, Optional
import json

logger = logging.getLogger(__name__)


class ConfigValidator:
    """Validates Wegweiser configuration"""

    def __init__(self):
        self.errors: List[str] = []
        self.warnings: List[str] = []
        self.info: List[str] = []

    def validate_all(self) -> bool:
        """Run all validation checks"""
        self.validate_database_config()
        self.validate_redis_config()
        self.validate_secret_storage_config()
        self.validate_ai_provider_config()
        self.validate_required_directories()

        return len(self.errors) == 0

    def validate_database_config(self) -> bool:
        """Validate database configuration"""
        logger.info("Validating database configuration...")

        # Check for database URL
        db_url = os.getenv("DATABASE_URL") or os.getenv("SQLALCHEMY_DATABASE_URI")
        if not db_url:
            self.errors.append(
                "DATABASE_URL or SQLALCHEMY_DATABASE_URI not set. "
                "Database connectivity will fail."
            )
            return False

        # Validate URL format
        if not db_url.startswith(("postgresql://", "postgres://")):
            self.warnings.append(
                f"Unusual database URL format: {db_url[:30]}... "
                "Ensure it's a valid PostgreSQL connection string."
            )

        self.info.append("Database URL configured")
        return True

    def validate_redis_config(self) -> bool:
        """Validate Redis configuration"""
        logger.info("Validating Redis configuration...")

        redis_host = os.getenv("REDIS_HOST", "localhost")
        redis_port = os.getenv("REDIS_PORT", "6379")

        # Try to import redis
        try:
            import redis
            try:
                client = redis.Redis(
                    host=redis_host,
                    port=int(redis_port),
                    socket_timeout=5,
                    socket_connect_timeout=5
                )
                client.ping()
                self.info.append(f"Redis connectivity verified ({redis_host}:{redis_port})")
                return True
            except Exception as e:
                self.warnings.append(
                    f"Could not connect to Redis at {redis_host}:{redis_port}. "
                    f"Sessions and Celery will use fallback mechanisms. Error: {str(e)}"
                )
                return True  # Warnings only, Redis has fallbacks
        except ImportError:
            self.warnings.append("redis package not installed. Sessions will use filesystem backend.")
            return True

    def validate_secret_storage_config(self) -> bool:
        """Validate secret storage configuration"""
        logger.info("Validating secret storage configuration...")

        from app.utilities.secret_manager import get_secret_manager

        manager = get_secret_manager()
        health = manager.health_check()

        available_backends = [name for name, status in health.items() if status]

        if not available_backends:
            self.warnings.append(
                "No secret backends are currently available. "
                "Ensure Azure Key Vault, OpenBao, or environment variables are properly configured."
            )
            return True

        self.info.append(f"Secret backends available: {', '.join(available_backends)}")
        return True

    def validate_ai_provider_config(self) -> bool:
        """Validate AI provider configuration"""
        logger.info("Validating AI provider configuration...")

        from app.utilities.secret_manager import get_secret

        ai_provider = os.getenv("AI_PROVIDER", "openai").lower()

        if ai_provider == "azure":
            api_key = get_secret("AZURE_OPENAI_API_KEY")
            endpoint = get_secret("AZURE_OPENAI_ENDPOINT")

            if not api_key:
                self.warnings.append("Azure OpenAI API Key not configured")
            if not endpoint:
                self.warnings.append("Azure OpenAI Endpoint not configured")

            if api_key and endpoint:
                self.info.append(f"Azure OpenAI configured (provider: {ai_provider})")

        elif ai_provider == "openai":
            api_key = get_secret("OPENAI_API_KEY")
            if not api_key:
                self.warnings.append("OpenAI API Key not configured")
            else:
                self.info.append(f"OpenAI configured (provider: {ai_provider})")

        elif ai_provider == "anthropic":
            api_key = get_secret("ANTHROPIC_API_KEY")
            if not api_key:
                self.warnings.append("Anthropic API Key not configured")
            else:
                self.info.append(f"Anthropic Claude configured (provider: {ai_provider})")

        elif ai_provider == "ollama":
            host = os.getenv("OLLAMA_HOST", "http://localhost:11434")
            self.info.append(f"Ollama configured (host: {host})")

        else:
            self.warnings.append(f"Unknown AI provider: {ai_provider}")

        return True

    def validate_required_directories(self) -> bool:
        """Validate and create required directories"""
        logger.info("Validating required directories...")

        required_dirs = [
            "logs",
            "flask_session",
            "app/static/images/profilepictures",
            "app/static/images/tenantprofile",
            "app/data/ip_blocker",
        ]

        for dir_path in required_dirs:
            if not os.path.exists(dir_path):
                try:
                    os.makedirs(dir_path, mode=0o755)
                    self.info.append(f"Created directory: {dir_path}")
                except Exception as e:
                    self.errors.append(f"Failed to create directory {dir_path}: {str(e)}")
                    return False
            else:
                self.info.append(f"Directory exists: {dir_path}")

        return True

    def print_report(self):
        """Print validation report"""
        if self.info:
            print("\n✓ Configuration Information:")
            for msg in self.info:
                print(f"  ✓ {msg}")

        if self.warnings:
            print("\n⚠ Configuration Warnings:")
            for msg in self.warnings:
                print(f"  ⚠ {msg}")

        if self.errors:
            print("\n✗ Configuration Errors:")
            for msg in self.errors:
                print(f"  ✗ {msg}")

        if not self.errors and not self.warnings:
            print("\n✓ All configuration checks passed!")

    def get_summary(self) -> Dict[str, any]:
        """Get validation summary as dictionary"""
        return {
            "valid": len(self.errors) == 0,
            "errors": self.errors,
            "warnings": self.warnings,
            "info": self.info,
        }


def validate_config() -> bool:
    """
    Validate configuration and return status

    Used during application startup to verify critical configuration items.
    Returns True if all errors are resolved (warnings are acceptable).
    """
    validator = ConfigValidator()
    is_valid = validator.validate_all()
    validator.print_report()
    return is_valid


if __name__ == "__main__":
    # Allow running this script directly for validation
    validator = ConfigValidator()
    validator.validate_all()
    validator.print_report()

    summary = validator.get_summary()
    print(f"\n{json.dumps(summary, indent=2)}")

    sys.exit(0 if validator.validate_all() else 1)
