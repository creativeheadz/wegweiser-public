"""
Snippet Executor - Safe snippet execution with resource limits
"""

import subprocess
import sys
import logging
import time
import os
import base64
import json
import asyncio
from pathlib import Path
from typing import NamedTuple, Optional
from .validator import SnippetValidator

logger = logging.getLogger(__name__)


class ExecutionResult(NamedTuple):
    """Execution result"""
    status: str  # 'success', 'failed', 'timeout', 'error'
    stdout: str = ""
    stderr: str = ""
    exit_code: int = -1
    duration_ms: int = 0
    error: str = ""


class SnippetExecutor:
    """Execute snippets safely with resource limits"""

    def __init__(self, snippets_dir: Path, timeout: int = 600):
        """Initialize executor with 10 minute default timeout"""
        self.snippets_dir = snippets_dir
        self.timeout = timeout
        self.validator = SnippetValidator()

    async def execute(
        self,
        snippet_code: str,
        snippet_name: str,
        schedule_uuid: str,
        parameters: dict = None
    ) -> ExecutionResult:
        """Execute snippet asynchronously with validation and timeout"""
        start_time = time.time()

        logger.info(f"Executing snippet: {snippet_name} ({schedule_uuid[:8]}...)")
        if parameters:
            logger.debug(f"Snippet parameters: {list(parameters.keys())}")

        # 1. Validate
        validation = self.validator.validate(snippet_code)
        if not validation.valid:
            logger.error(f"Validation failed: {validation.error}")
            return ExecutionResult(
                status='validation_failed',
                error=validation.error,
                duration_ms=int((time.time() - start_time) * 1000)
            )

        # 2. Write to temp file
        snippet_path = self.snippets_dir / f"current-{schedule_uuid}.py"
        try:
            with open(snippet_path, 'w') as f:
                f.write(snippet_code)
            logger.debug(f"Snippet written to {snippet_path}")
        except Exception as e:
            logger.error(f"Failed to write snippet: {e}")
            return ExecutionResult(
                status='error',
                error=f"Failed to write snippet: {e}",
                duration_ms=int((time.time() - start_time) * 1000)
            )

        # 3. Execute asynchronously (non-blocking) with parameters as env vars
        try:
            # Prepare environment with parameters
            env = os.environ.copy()
            if parameters:
                for key, value in parameters.items():
                    env[key] = str(value)
                    logger.debug(f"Set env var: {key}={value}")

            process = await asyncio.create_subprocess_exec(
                sys.executable, str(snippet_path),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=env
            )

            # Wait for completion with timeout
            try:
                stdout_bytes, stderr_bytes = await asyncio.wait_for(
                    process.communicate(),
                    timeout=self.timeout
                )
                stdout = stdout_bytes.decode('utf-8', errors='replace')
                stderr = stderr_bytes.decode('utf-8', errors='replace')
                returncode = process.returncode

            except asyncio.TimeoutError:
                # Kill the process if it times out
                try:
                    process.kill()
                    await process.wait()
                except:
                    pass
                logger.error(f"Snippet execution timeout: {snippet_name}")
                return ExecutionResult(
                    status='timeout',
                    error=f"Execution exceeded {self.timeout}s limit",
                    duration_ms=int((time.time() - start_time) * 1000)
                )

            duration_ms = int((time.time() - start_time) * 1000)

            status = 'success' if returncode == 0 else 'failed'
            logger.info(f"Snippet execution {status}: {snippet_name}")

            # Log execution details for debugging
            if returncode != 0:
                logger.error(f"Snippet failed with exit code: {returncode}")
                if stderr:
                    # Log last 2000 chars of stderr (most recent errors)
                    logger.error(f"STDERR (last 2000 chars): {stderr[-2000:]}")
                if stdout:
                    logger.info(f"STDOUT (last 1000 chars): {stdout[-1000:]}")
            else:
                if stdout:
                    logger.debug(f"STDOUT: {stdout[:200]}")  # First 200 chars

            return ExecutionResult(
                status=status,
                stdout=stdout,
                stderr=stderr,
                exit_code=returncode,
                duration_ms=duration_ms
            )

        except Exception as e:
            logger.error(f"Snippet execution error: {e}")
            return ExecutionResult(
                status='error',
                error=str(e),
                duration_ms=int((time.time() - start_time) * 1000)
            )

        finally:
            # Cleanup
            try:
                if snippet_path.exists():
                    snippet_path.unlink()
                    logger.debug(f"Cleaned up {snippet_path}")
            except Exception as e:
                logger.warning(f"Failed to cleanup snippet: {e}")
    
    def decode_snippet(self, response_json: str) -> tuple:
        """Decode base64-encoded snippet and extract parameters"""
        try:
            # Log the raw response for debugging
            logger.debug(f"Raw response (first 200 chars): {str(response_json)[:200]}")

            # Handle case where response is already a dict (from API client)
            if isinstance(response_json, dict):
                payload_dict = response_json
            else:
                payload_dict = json.loads(response_json)

            # Handle both old and new response formats
            # Try new format first: data.payload.payloadb64
            try:
                snippet_code = base64.b64decode(
                    payload_dict['data']['payload']['payloadb64']
                ).decode('utf-8')
                snippet_name = payload_dict['data']['settings']['snippetname']
                # Extract parameters if present
                parameters = payload_dict['data'].get('parameters', {})
            except (KeyError, TypeError):
                # Try old format: payload.payloadb64 (direct response)
                snippet_code = base64.b64decode(
                    payload_dict['payload']['payloadb64']
                ).decode('utf-8')
                snippet_name = payload_dict['settings']['snippetname']
                # Extract parameters if present
                parameters = payload_dict.get('parameters', {})

            return snippet_code, snippet_name, parameters

        except Exception as e:
            logger.error(f"Failed to decode snippet: {e}")
            logger.error(f"Response type: {type(response_json)}")
            logger.error(f"Response content (first 500 chars): {str(response_json)[:500]}")
            raise

