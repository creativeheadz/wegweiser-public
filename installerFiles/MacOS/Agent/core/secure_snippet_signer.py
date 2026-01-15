"""
Secure Snippet Signer - Uses Azure Key Vault for private key storage
Never exposes private keys to disk or memory beyond signing operation
"""

import logging
import base64
import json
import uuid
import time
import os
from typing import Tuple, Optional

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives.serialization import load_pem_private_key
from cryptography.hazmat.backends import default_backend

logger = logging.getLogger(__name__)


class SecureSnippetSigner:
    """Sign snippets using Key Vault-stored private keys"""

    @staticmethod
    def sign_snippet_with_key_vault(
        script_path: str,
        key_vault_client,
        private_key_secret_name: str,
        output_dir: str
    ) -> Tuple[str, str]:
        """Sign a snippet using private key from Azure Key Vault

        Args:
            script_path: Path to the script file to sign
            key_vault_client: Azure KeyVault client
            private_key_secret_name: Name of the secret containing private key
            output_dir: Directory to save signed snippet JSON

        Returns:
            Tuple[snippet_uuid, output_path]: UUID and path of signed snippet

        Security:
            - Private key never touched by disk
            - Private key loaded directly from Azure Key Vault
            - Signing happens in-memory
            - Private key is immediately discarded after signing
        """
        snippet_uuid = str(uuid.uuid4())

        try:
            # Retrieve private key from Key Vault (never touches disk)
            logger.info(f"Retrieving private key from Key Vault: {private_key_secret_name}")
            private_key_secret = key_vault_client.get_secret(private_key_secret_name)
            private_key_pem = private_key_secret.value

            # Load private key object in-memory
            private_key = load_pem_private_key(
                private_key_pem.encode(),
                password=None,
                backend=default_backend()
            )
            logger.debug("Private key loaded into memory from Key Vault")

            # Read and encode script
            with open(script_path, 'rb') as f:
                script_content = f.read()
                encoded_content = base64.b64encode(script_content)

            # Sign content
            logger.info(f"Signing snippet: {os.path.basename(script_path)}")
            signature = private_key.sign(
                encoded_content,
                padding.PKCS1v15(),
                hashes.SHA256()
            )
            encoded_signature = base64.b64encode(signature).decode()

            # Create snippet JSON with nested structure
            snippet_json = {
                'data': {
                    'settings': {
                        'snippetUuid': snippet_uuid,
                        'snippetname': os.path.splitext(os.path.basename(script_path))[0],
                        'snippettype': '.py',
                        'created_at': int(time.time())
                    },
                    'payload': {
                        'payloadsig': encoded_signature,
                        'payloadb64': encoded_content.decode()
                    }
                },
                'status': 'signed'
            }

            # Save signed snippet to file
            output_path = os.path.join(output_dir, f'{snippet_uuid}.json')
            with open(output_path, 'w') as f:
                json.dump(snippet_json, f)

            logger.info(f"Snippet signed and saved: {output_path}")

            # Private key is now out of scope and will be garbage collected
            # (Python doesn't guarantee immediate memory clearing, but key is no longer accessible)
            del private_key

            return snippet_uuid, output_path

        except Exception as e:
            logger.error(f"Failed to sign snippet: {e}")
            raise

    @staticmethod
    def sign_snippet_with_file(
        script_path: str,
        key_file_path: str,
        output_dir: str,
        key_password: Optional[str] = None
    ) -> Tuple[str, str]:
        """Sign a snippet using a file-based private key (for testing/offline)

        WARNING: File-based keys should only be used in secure environments.
        Production should use Key Vault via sign_snippet_with_key_vault()

        Args:
            script_path: Path to the script file to sign
            key_file_path: Path to PEM-encoded private key file
            output_dir: Directory to save signed snippet JSON
            key_password: Optional password for encrypted key

        Returns:
            Tuple[snippet_uuid, output_path]: UUID and path of signed snippet
        """
        snippet_uuid = str(uuid.uuid4())

        try:
            # Verify key file exists
            if not os.path.exists(key_file_path):
                raise FileNotFoundError(f"Key file not found: {key_file_path}")

            # Read private key from file
            with open(key_file_path, 'rb') as f:
                private_key_pem = f.read()

            # Load private key object in-memory
            private_key = load_pem_private_key(
                private_key_pem,
                password=key_password.encode() if key_password else None,
                backend=default_backend()
            )
            logger.debug("Private key loaded into memory from file")

            # Read and encode script
            with open(script_path, 'rb') as f:
                script_content = f.read()
                encoded_content = base64.b64encode(script_content)

            # Sign content
            logger.info(f"Signing snippet: {os.path.basename(script_path)}")
            signature = private_key.sign(
                encoded_content,
                padding.PKCS1v15(),
                hashes.SHA256()
            )
            encoded_signature = base64.b64encode(signature).decode()

            # Create snippet JSON with nested structure
            snippet_json = {
                'data': {
                    'settings': {
                        'snippetUuid': snippet_uuid,
                        'snippetname': os.path.splitext(os.path.basename(script_path))[0],
                        'snippettype': '.py',
                        'created_at': int(time.time())
                    },
                    'payload': {
                        'payloadsig': encoded_signature,
                        'payloadb64': encoded_content.decode()
                    }
                },
                'status': 'signed'
            }

            # Save signed snippet to file
            output_path = os.path.join(output_dir, f'{snippet_uuid}.json')
            with open(output_path, 'w') as f:
                json.dump(snippet_json, f)

            logger.info(f"Snippet signed and saved: {output_path}")

            # Clean up: securely erase key file if it's temporary
            # (can be controlled by calling code if needed)

            del private_key

            return snippet_uuid, output_path

        except Exception as e:
            logger.error(f"Failed to sign snippet: {e}")
            raise

    @staticmethod
    def bulk_resign_snippets(
        snippet_uuids: list,
        key_vault_client,
        private_key_secret_name: str,
        snippet_repo_path: str
    ) -> Tuple[int, int]:
        """Re-sign multiple snippets after key rotation

        Args:
            snippet_uuids: List of snippet UUIDs to resign
            key_vault_client: Azure KeyVault client
            private_key_secret_name: Name of the secret containing private key
            snippet_repo_path: Base path to snippet repository

        Returns:
            Tuple[success_count, failure_count]
        """
        success_count = 0
        failure_count = 0

        logger.info(f"Starting bulk re-signing of {len(snippet_uuids)} snippets")

        for snippet_uuid in snippet_uuids:
            try:
                snippet_json_path = os.path.join(
                    snippet_repo_path,
                    '00000000-0000-0000-0000-000000000000',
                    f'{snippet_uuid}.json'
                )

                if not os.path.exists(snippet_json_path):
                    logger.warning(f"Snippet not found: {snippet_json_path}")
                    failure_count += 1
                    continue

                # Load existing snippet to get script content
                with open(snippet_json_path, 'r') as f:
                    snippet_data = json.load(f)

                # Retrieve private key from Key Vault
                private_key_secret = key_vault_client.get_secret(private_key_secret_name)
                private_key_pem = private_key_secret.value

                private_key = load_pem_private_key(
                    private_key_pem.encode(),
                    password=None,
                    backend=default_backend()
                )

                # Re-sign the payload
                payload_b64 = snippet_data['data']['payload']['payloadb64']
                payload = base64.b64decode(payload_b64)

                signature = private_key.sign(
                    payload,
                    padding.PKCS1v15(),
                    hashes.SHA256()
                )
                encoded_signature = base64.b64encode(signature).decode()

                # Update snippet with new signature
                snippet_data['data']['payload']['payloadsig'] = encoded_signature
                snippet_data['resigned_at'] = int(time.time())

                # Save updated snippet
                with open(snippet_json_path, 'w') as f:
                    json.dump(snippet_data, f)

                logger.info(f"Re-signed snippet: {snippet_uuid}")
                success_count += 1

                del private_key

            except Exception as e:
                logger.error(f"Failed to re-sign snippet {snippet_uuid}: {e}")
                failure_count += 1

        logger.info(f"Bulk re-signing complete: {success_count} success, {failure_count} failed")
        return success_count, failure_count
