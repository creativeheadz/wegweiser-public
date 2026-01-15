"""
Cryptography Manager - RSA key management and signature verification with key rotation support
"""

import logging
from typing import Tuple, List, Dict, Optional
import base64
import json
from pathlib import Path

from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.backends import default_backend

logger = logging.getLogger(__name__)


class CryptoManager:
    """Manage cryptographic operations with key rotation support"""

    KEY_SIZE = 4096  # Strong RSA key size
    PUBLIC_EXPONENT = 65537

    def __init__(self, keys_cache_dir: Optional[Path] = None):
        """Initialize crypto manager with optional key cache directory"""
        self.keys_cache_dir = keys_cache_dir or Path.home() / '.wegweiser' / 'keys'
        self.keys_cache_dir.mkdir(parents=True, exist_ok=True)

        # In-memory cache: {key_id: {'pem': str, 'key_obj': RSA_key}}
        self.key_cache: Dict[str, dict] = {}
        self.current_key_id = 'current'
        self.old_key_id = 'old'

        # Load cached keys from disk if available
        self.load_keys_from_cache()

    def load_keys_from_cache(self):
        """Load cached server keys from disk"""
        try:
            current_key_file = self.keys_cache_dir / 'current_key.pem'
            old_key_file = self.keys_cache_dir / 'old_key.pem'

            if current_key_file.exists():
                with open(current_key_file, 'r') as f:
                    current_pem = f.read()
                    self.key_cache[self.current_key_id] = {
                        'pem': current_pem,
                        'key_obj': self.load_public_key(current_pem)
                    }
                logger.info(f"Loaded current key from cache")

            if old_key_file.exists():
                with open(old_key_file, 'r') as f:
                    old_pem = f.read()
                    self.key_cache[self.old_key_id] = {
                        'pem': old_pem,
                        'key_obj': self.load_public_key(old_pem)
                    }
                logger.info(f"Loaded old key from cache")

        except Exception as e:
            logger.warning(f"Failed to load keys from cache: {e}")

    def update_server_key(self, key_pem: str, key_type: str = 'current'):
        """Update server key in cache and persist to disk

        Args:
            key_pem: PEM-formatted public key
            key_type: 'current' or 'old'
        """
        try:
            # Verify it's a valid key
            key_obj = self.load_public_key(key_pem)

            # Update in-memory cache
            self.key_cache[key_type] = {
                'pem': key_pem,
                'key_obj': key_obj
            }

            # Persist to disk
            key_file = self.keys_cache_dir / f'{key_type}_key.pem'
            with open(key_file, 'w') as f:
                f.write(key_pem)

            logger.info(f"Updated {key_type} server key and saved to cache")

        except Exception as e:
            logger.error(f"Failed to update {key_type} server key: {e}")
            raise

    def get_all_cached_keys(self) -> List[str]:
        """Get all cached key PEMs, in order of preference (current, then old)"""
        keys = []

        if self.current_key_id in self.key_cache:
            keys.append(self.key_cache[self.current_key_id]['pem'])

        if self.old_key_id in self.key_cache:
            keys.append(self.key_cache[self.old_key_id]['pem'])

        return keys

    @staticmethod
    def generate_keypair() -> Tuple[str, str]:
        """Generate 4096-bit RSA keypair"""
        logger.info("Generating 4096-bit RSA keypair...")

        try:
            private_key = rsa.generate_private_key(
                public_exponent=CryptoManager.PUBLIC_EXPONENT,
                key_size=CryptoManager.KEY_SIZE,
                backend=default_backend()
            )

            # Serialize private key
            private_pem = private_key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.TraditionalOpenSSL,
                encryption_algorithm=serialization.NoEncryption()
            ).decode('utf-8')

            # Serialize public key
            public_pem = private_key.public_key().public_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PublicFormat.SubjectPublicKeyInfo
            ).decode('utf-8')

            logger.info("Keypair generated successfully")
            return private_pem, public_pem

        except Exception as e:
            logger.error(f"Failed to generate keypair: {e}")
            raise

    @staticmethod
    def load_public_key(pem_string: str):
        """Load public key from PEM string"""
        try:
            return serialization.load_pem_public_key(
                pem_string.encode(),
                backend=default_backend()
            )
        except Exception as e:
            logger.error(f"Failed to load public key: {e}")
            raise

    @staticmethod
    def verify_signature(message: str, signature_b64: str, public_key) -> bool:
        """Verify base64-encoded signature"""
        try:
            signature = base64.b64decode(signature_b64)
            public_key.verify(
                signature,
                message.encode(),
                padding.PKCS1v15(),
                hashes.SHA256()
            )
            logger.debug("Signature verified successfully")
            return True

        except Exception as e:
            logger.error(f"Signature verification failed: {e}")
            return False

    def verify_base64_payload_signature(
        self,
        payload_json,
        public_key=None,
        try_all_keys: bool = True
    ) -> Tuple[bool, Optional[str]]:
        """Verify signature from base64-encoded payload structure

        Supports key rotation by trying multiple keys if verification fails.

        Args:
            payload_json: Either a JSON string or a parsed dict
            public_key: RSA public key object (optional, will try cached keys if not provided)
            try_all_keys: If True and initial verification fails, try all cached keys

        Returns:
            Tuple[bool, Optional[str]]: (verification_success, which_key_worked)
                - which_key_worked is None if verification failed or public_key was provided
                - which_key_worked is 'current' or 'old' if verification succeeded with cached key
        """
        try:
            # Handle both dict and JSON string inputs
            if isinstance(payload_json, dict):
                payload_dict = payload_json
            elif isinstance(payload_json, str):
                payload_dict = json.loads(payload_json)
            else:
                logger.error(f"Invalid payload type: {type(payload_json)}")
                return False, None

            # Extract payload and signature
            try:
                # Try nested structure first: data.payload.payloadb64
                payload_b64 = payload_dict['data']['payload']['payloadb64']
                signature_b64 = payload_dict['data']['payload']['payloadsig']
            except (KeyError, TypeError):
                # Fall back to flat structure: payload.payloadb64
                payload_b64 = payload_dict['payload']['payloadb64']
                signature_b64 = payload_dict['payload']['payloadsig']

            # Decode
            payload = base64.b64decode(payload_b64)
            signature = base64.b64decode(signature_b64)

            # If specific key provided, use only that
            if public_key:
                try:
                    public_key.verify(
                        signature,
                        payload,
                        padding.PKCS1v15(),
                        hashes.SHA256()
                    )
                    logger.debug("Payload signature verified successfully with provided key")
                    return True, None
                except Exception as e:
                    logger.error(f"Signature verification failed with provided key: {e}")
                    return False, None

            # Try all cached keys (current first, then old)
            if try_all_keys:
                keys_to_try = [
                    (self.current_key_id, self.key_cache[self.current_key_id]['key_obj'])
                    for _ in [None] if self.current_key_id in self.key_cache
                ] + [
                    (self.old_key_id, self.key_cache[self.old_key_id]['key_obj'])
                    for _ in [None] if self.old_key_id in self.key_cache
                ]

                for key_id, key_obj in keys_to_try:
                    try:
                        key_obj.verify(
                            signature,
                            payload,
                            padding.PKCS1v15(),
                            hashes.SHA256()
                        )
                        logger.info(f"Payload signature verified successfully with {key_id} key")
                        return True, key_id
                    except Exception:
                        continue

                logger.error(f"Payload signature verification failed with all cached keys")
                return False, None

            return False, None

        except json.JSONDecodeError as je:
            logger.error(f"JSON decode error: {je}")
            return False, None
        except Exception as e:
            logger.error(f"Payload signature verification error: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return False, None
