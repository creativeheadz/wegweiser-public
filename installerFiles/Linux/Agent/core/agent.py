"""
Wegweiser Agent - Main orchestrator
"""

import logging
import sys
import socket
import platform
import argparse
import os
import random
import signal
import time
try:
    import fcntl
    _FCNTL_AVAILABLE = True
except Exception:
    fcntl = None
    _FCNTL_AVAILABLE = False
from contextlib import contextmanager
import asyncio
from pathlib import Path

from .config import ConfigManager
from .crypto import CryptoManager
from .api_client import APIClient
from .nats_service import NATSService
from .tool_manager import ToolManager

# Try to import MCP handler (optional)
try:
    from .mcp_handler import MCPHandler
    MCP_AVAILABLE = True
except ImportError:
    MCP_AVAILABLE = False
    MCPHandler = None

# Try relative imports first (for package mode), fall back to absolute (for deployment)
try:
    from ..execution.executor import SnippetExecutor
    from ..monitoring.health import HealthMonitor
except ImportError:
    from execution.executor import SnippetExecutor
    from monitoring.health import HealthMonitor

logger = logging.getLogger(__name__)


class StructuredLogFormatter(logging.Formatter):
    """Custom formatter with structured aligned columns"""

    LEVEL_WIDTH = 8
    MODULE_WIDTH = 30

    def format(self, record):
        """Format log record with structured aligned columns"""
        timestamp = self.formatTime(record, "%Y-%m-%d %H:%M:%S")
        level = record.levelname

        # Pad level to fixed width for column alignment
        formatted_level = f"{level:<{self.LEVEL_WIDTH}}"

        module = record.name
        formatted_module = f"{module:<{self.MODULE_WIDTH}}"
        message = record.getMessage()

        if record.exc_info:
            message += f"\n{self.formatException(record.exc_info)}"

        log_line = (
            f"{timestamp} | "
            f"{formatted_level} | "
            f"{formatted_module} | "
            f"{message}"
        )

        return log_line


class WegweiserAgent:
    """Main agent orchestrator"""
    
    VERSION = "3.0.1"
    
    def __init__(self, config_path: str = None, debug: bool = False, enable_nats: bool = False):
        """Initialize agent"""
        self.debug = debug
        self.enable_nats = enable_nats
        self.config = ConfigManager(config_path)
        self.crypto = CryptoManager()
        self.api = None
        self.executor = None
        self.health = None
        self.nats = None
        self.mcp = None
        self.tool_manager = None
        self._lock_file_handle = None
        self._setup_logging()

    def _setup_logging(self):
        """Setup logging with structured columnar format"""
        log_level = logging.DEBUG if self.debug else logging.INFO

        # Console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(log_level)

        # File handler
        log_file = self.config.log_dir / 'agent.log'
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(log_level)

        # Formatter - use StructuredLogFormatter for aligned columns
        formatter = StructuredLogFormatter()
        console_handler.setFormatter(formatter)
        file_handler.setFormatter(formatter)

        # Root logger
        root_logger = logging.getLogger()
        root_logger.setLevel(log_level)
        root_logger.addHandler(console_handler)
        root_logger.addHandler(file_handler)
        
        logger.info(f"Wegweiser Agent {self.VERSION} started")
        logger.info(f"Platform: {platform.system()} {platform.release()}")
    
    async def initialize(self) -> bool:
        """Initialize agent"""
        logger.info("Initializing agent...")

        # Load config
        if not self.config.load():
            logger.warning("Config not found, will attempt registration")
            return self._register_device()

        # Validate config
        if not self.config.validate():
            logger.error("Invalid configuration")
            return False

        # Initialize components
        self.api = APIClient(self.config.server_addr)
        self.executor = SnippetExecutor(self.config.snippets_dir)
        self.health = HealthMonitor(self.config.device_uuid, self.VERSION)
        self.tool_manager = ToolManager(str(self.config.base_dir), self.config.server_addr)

        # Initialize crypto manager and load server key into cache
        try:
            server_pub_pem = self.config.get('serverpubpem')
            if server_pub_pem:
                self.crypto.update_server_key(server_pub_pem, key_type='current')
                logger.info("Loaded server public key into crypto cache")
        except Exception as e:
            logger.warning(f"Failed to load initial server key into cache: {e}")

        # Track last known key hash for rotation detection
        self.last_key_hash = self._compute_key_hash(server_pub_pem) if server_pub_pem else None

        # Initialize MCP handler if available
        agent_dir = Path(__file__).parent.parent
        if MCP_AVAILABLE:
            self.mcp = MCPHandler(mcp_dir=agent_dir / "mcp")
            if not await self.mcp.initialize():
                logger.warning("Failed to initialize MCP handler, continuing without MCP tools")
                self.mcp = None
        else:
            logger.debug("MCP handler not available, skipping initialization")
            self.mcp = None

        # Initialize NATS if enabled
        if self.enable_nats:
            # Create NATS service (tenant_uuid will be fetched from server)
            self.nats = NATSService(
                device_uuid=self.config.device_uuid,
                tenant_uuid=None,  # Will be fetched from server
                server_url=self.config.server_addr
            )

            # Get tenant info from server
            if not await self.nats.get_tenant_info(self.api):
                logger.error("Failed to get tenant information from server")
                return False

            # Register MCP command handler with NATS if MCP is available
            if self.mcp:
                self.nats.register_command_handler("mcp_execute", self.mcp.handle_mcp_request)
                logger.info("MCP command handler registered with NATS")

            logger.info("NATS service initialized")

        logger.info("Agent initialized successfully")
        return True
    
    def _register_device(self, group_uuid: str = None, server_addr: str = None) -> bool:
        """Register device with server"""
        logger.info("Registering device...")

        # If not provided as arguments, try to get from command line
        if not group_uuid or not server_addr:
            parser = argparse.ArgumentParser(add_help=False)
            parser.add_argument('-g', '--groupUuid', required=False, help='Group UUID')
            parser.add_argument('-s', '--serverAddr', required=False, help='Server address')
            # Parse only known args to avoid conflicts with other parsers
            args, _ = parser.parse_known_args()
            group_uuid = group_uuid or args.groupUuid
            server_addr = server_addr or args.serverAddr

        if not group_uuid or not server_addr:
            logger.error("Group UUID and server address are required for registration")
            return False

        try:
            logger.info(f"Starting registration with group_uuid={group_uuid}, server_addr={server_addr}")

            # Initialize API
            logger.info(f"Initializing API client with server: {server_addr}")
            self.api = APIClient(server_addr)

            # Generate keypair
            logger.info("Generating keypair...")
            private_pem, public_pem = self.crypto.generate_keypair()
            logger.info("Keypair generated successfully")

            # Get server public key
            logger.info("Fetching server public key...")
            server_pub_pem = self.api.get_server_public_key()
            logger.info("Server public key fetched successfully")

            # Register device
            logger.info(f"Registering device with hostname: {socket.gethostname()}")
            device_uuid = self.api.register_device(
                group_uuid=group_uuid,
                device_name=socket.gethostname(),
                hardware_info=platform.system(),
                agent_pub_pem=public_pem
            )
            logger.info(f"Device registered with UUID: {device_uuid}")

            # Save config
            logger.info(f"Saving configuration to {self.config.config_path}")
            self.config.set('deviceuuid', device_uuid)
            self.config.set('agentprivpem', private_pem)
            self.config.set('agentpubpem', public_pem)
            self.config.set('serverpubpem', server_pub_pem)
            self.config.set('serverAddr', server_addr)

            if not self.config.save():
                logger.error("Failed to save configuration")
                return False

            logger.info(f"Configuration saved successfully")
            logger.info(f"Device registered: {device_uuid}")

            # Initialize components
            self.executor = SnippetExecutor(self.config.snippets_dir)
            self.health = HealthMonitor(device_uuid, self.VERSION)
            self.tool_manager = ToolManager(str(self.config.base_dir), self.config.server_addr)

            return True

        except Exception as e:
            logger.error(f"Registration failed: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return False
    
    @staticmethod
    def _compute_key_hash(key_pem: str) -> str:
        """Compute SHA256 hash of public key PEM for rotation detection"""
        if not key_pem:
            return None
        import hashlib
        return hashlib.sha256(key_pem.encode()).hexdigest()

    def _initialize_sync(self) -> bool:
        """Synchronous initialization for scheduled agents"""
        logger.info("Initializing agent (synchronous mode)...")

        # Load config
        if not self.config.load():
            logger.warning("Config not found, will attempt registration")
            return self._register_device()

        # Validate config
        if not self.config.validate():
            logger.error("Invalid configuration")
            return False

        # Initialize components
        self.api = APIClient(self.config.server_addr)
        self.executor = SnippetExecutor(self.config.snippets_dir)
        self.health = HealthMonitor(self.config.device_uuid, self.VERSION)

        # Initialize crypto manager and load server key into cache
        try:
            server_pub_pem = self.config.get('serverpubpem')
            if server_pub_pem:
                self.crypto.update_server_key(server_pub_pem, key_type='current')
                logger.info("Loaded server public key into crypto cache")
        except Exception as e:
            logger.warning(f"Failed to load initial server key into cache: {e}")

        # Track last known key hash for rotation detection
        self.last_key_hash = self._compute_key_hash(server_pub_pem) if server_pub_pem else None

        logger.info("Agent initialized successfully (synchronous mode)")
        return True

    def _handle_heartbeat_response(self, response_data: dict):
        """Handle heartbeat response and check for key rotation

        Args:
            response_data: Heartbeat response from server
        """
        try:
            if not response_data:
                return

            # Check if keys have rotated
            server_key_hash = response_data.get('current_key_hash')
            if server_key_hash and server_key_hash != self.last_key_hash:
                logger.warning(f"Key rotation detected! Old hash: {self.last_key_hash[:8]}..., New: {server_key_hash[:8]}...")

                # Fetch updated keys
                try:
                    new_key_pem = self.api.get_server_public_key()
                    if new_key_pem:
                        # Save old key before updating
                        current_key = self.config.get('serverpubpem')
                        if current_key:
                            self.crypto.update_server_key(current_key, key_type='old')

                        # Update current key
                        self.crypto.update_server_key(new_key_pem, key_type='current')
                        self.config.set('serverpubpem', new_key_pem)
                        self.config.save()

                        self.last_key_hash = self._compute_key_hash(new_key_pem)
                        logger.info("Successfully updated to new server public key")
                    else:
                        logger.warning("Failed to fetch updated server key from heartbeat notification")

                except Exception as e:
                    logger.error(f"Error handling key rotation from heartbeat: {e}")

        except Exception as e:
            logger.error(f"Error processing heartbeat response: {e}")

    def run(self):
        """Main agent loop"""
        logger.info("Starting main loop...")

        # Initialize agent (synchronous for scheduled agents)
        try:
            if not self._initialize_sync():
                logger.error("Failed to initialize agent")
                sys.exit(1)
        except Exception as e:
            logger.error(f"Initialization error: {e}")
            import traceback
            logger.error(traceback.format_exc())
            sys.exit(1)

        # Install signal handlers to gracefully release locks
        self._install_signal_handlers()

        # Acquire single-instance lock to avoid concurrent snippet execution on the same host
        if not self._acquire_snippet_lock(nonblocking=False):
            logger.error("Failed to acquire snippet execution lock")
            sys.exit(1)

        try:
            while True:
                self._process_pending_snippets()
                
                # Sleep before next check
                time.sleep(60)
        
        except KeyboardInterrupt:
            logger.info("Agent stopped by user")
        except Exception as e:
            logger.error(f"Agent error: {e}")
            self.health.record_error(str(e))
        finally:
            self._release_snippet_lock()
            logger.info("Agent shutdown")
    
    def _process_pending_snippets(self):
        """Process pending snippets"""
        try:
            # Get pending snippets
            schedule_list = self.api.get_pending_snippets(self.config.device_uuid)
            
            if not schedule_list:
                logger.debug("No pending snippets")
                return
            
            logger.info(f"Processing {len(schedule_list)} pending snippets")
            
            # Process each snippet
            for schedule_uuid in schedule_list:
                # If APIClient provides claim_snippet, use it to avoid races (optional)
                claim_fn = getattr(self.api, "claim_snippet", None)
                if callable(claim_fn):
                    try:
                        claimed = bool(claim_fn(schedule_uuid))
                        if not claimed:
                            logger.debug(f"Schedule {schedule_uuid} not claimed (already in progress). Skipping.")
                            continue
                    except Exception as e:
                        logger.warning(f"claim_snippet failed for {schedule_uuid}: {e}. Continuing without claim.")
                self._process_snippet(schedule_uuid)
        
        except Exception as e:
            logger.error(f"Failed to process snippets: {e}")
            self.health.record_error(str(e))
    
    def _process_snippet(self, schedule_uuid: str):
        """Process single snippet with multi-key verification and automatic key rotation handling"""
        try:
            # Download snippet
            response = self.api.get_snippet(schedule_uuid)
            snippet_code, snippet_name, parameters = self.executor.decode_snippet(
                response
            )

            # Verify signature with multi-key fallback
            verified, which_key = self.crypto.verify_base64_payload_signature(
                response,
                public_key=None,  # Will use cached keys
                try_all_keys=True  # Try current, then old
            )

            if not verified:
                logger.warning(f"Signature verification failed with cached keys for {snippet_name}. Attempting to fetch updated keys from server...")

                # Try to fetch updated keys from server
                try:
                    new_key_pem = self.api.get_server_public_key()
                    if new_key_pem:
                        # Update cache with new key
                        self.crypto.update_server_key(new_key_pem, key_type='current')
                        logger.info("Updated server public key from server")

                        # Retry verification with new key
                        verified, which_key = self.crypto.verify_base64_payload_signature(
                            response,
                            public_key=None,
                            try_all_keys=True
                        )

                        if verified:
                            logger.info(f"Signature verified after key update using {which_key} key")
                        else:
                            logger.error(f"Signature verification still failed after key update for {snippet_name}")
                            self.api.report_snippet_execution(schedule_uuid, 'SIGFAIL')
                            return
                    else:
                        logger.error("Failed to fetch updated server key")
                        self.api.report_snippet_execution(schedule_uuid, 'SIGFAIL')
                        return

                except Exception as e:
                    logger.error(f"Error fetching updated server key: {e}")
                    self.api.report_snippet_execution(schedule_uuid, 'SIGFAIL')
                    return
            else:
                if which_key:
                    logger.debug(f"Signature verified using {which_key} key")

            # Execute snippet (async method - use asyncio.run for non-async context)
            result = asyncio.run(self.executor.execute(
                snippet_code,
                snippet_name,
                schedule_uuid,
                parameters
            ))

            # Record metrics
            self.health.record_execution(result.status, result.duration_ms)

            # Report result
            status = 'SUCCESS' if result.status == 'success' else 'EXECFAIL'
            self.api.report_snippet_execution(
                schedule_uuid,
                status,
                result.duration_ms,
                result.exit_code
            )

            logger.info(f"Snippet processed: {snippet_name} - {status}")

        except Exception as e:
            logger.error(f"Failed to process snippet {schedule_uuid}: {e}")
            self.health.record_error(str(e))
            try:
                self.api.report_snippet_execution(schedule_uuid, 'EXECFAIL')
            except:
                pass

    def run_once(self) -> int:
        """Process pending snippets once and exit (for systemd timer oneshot). Returns exit code."""
        logger.info("Running single execution cycle (oneshot mode)...")

        try:
            if not self._initialize_sync():
                logger.error("Failed to initialize agent")
                return 1
        except Exception as e:
            logger.error(f"Initialization error: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return 1

        # Install signal handlers to gracefully release locks
        self._install_signal_handlers()

        # Optional jitter to avoid thundering herd on timer tick
        max_jitter = self._get_max_jitter_seconds()
        if max_jitter > 0:
            delay = random.uniform(0, max_jitter)
            logger.debug(f"Applying startup jitter: sleeping {delay:.2f}s")
            time.sleep(delay)

        # Try to acquire lock non-blocking. If another instance is running, just exit quietly.
        if not self._acquire_snippet_lock(nonblocking=True):
            logger.info("Another snippet execution is in progress; skipping this cycle.")
            return 0

        try:
            self._process_pending_snippets()
            return 0
        except Exception as e:
            logger.error(f"Error during oneshot processing: {e}")
            return 1
        finally:
            self._release_snippet_lock()

    @contextmanager
    def _locked_execution(self, nonblocking: bool = True):
        """Context manager for snippet execution lock."""
        acquired = self._acquire_snippet_lock(nonblocking=nonblocking)
        try:
            yield acquired
        finally:
            if acquired:
                self._release_snippet_lock()

    def _candidate_lock_paths(self) -> list:
        """Return candidate lock directories in order of preference."""
        return [
            self.config.files_dir,
            Path("/run/wegweiser"),
            Path("/var/lock"),
            Path("/tmp"),
        ]

    def _acquire_snippet_lock(self, nonblocking: bool = True) -> bool:
        """Acquire an inter-process lock to prevent parallel snippet execution on this host."""
        # If fcntl is not available (e.g., Windows), skip locking gracefully
        if not _FCNTL_AVAILABLE:
            logger.debug("fcntl not available; skipping snippet lock")
            return True
        try:
            # Find first writable lock directory
            lock_dir = None
            for cand in self._candidate_lock_paths():
                try:
                    cand.mkdir(parents=True, exist_ok=True)
                    test_file = cand / ".writable"
                    with open(test_file, "a"):
                        pass
                    try:
                        os.remove(test_file)
                    except Exception:
                        pass
                    lock_dir = cand
                    break
                except Exception:
                    continue
            if lock_dir is None:
                logger.error("No writable directory available for lock file")
                return False

            lock_path = lock_dir / 'snippets.lock'
            self._lock_path = lock_path
            # Open or create the lock file
            self._lock_file_handle = open(lock_path, 'a')
            flags = fcntl.LOCK_EX | (fcntl.LOCK_NB if nonblocking else 0)
            fcntl.flock(self._lock_file_handle.fileno(), flags)
            logger.debug(f"Acquired snippet lock at {lock_path}")
            return True
        except BlockingIOError:
            logger.debug("Snippet lock is already held by another process")
            return False
        except Exception as e:
            logger.error(f"Failed to acquire snippet lock: {e}")
            return False

    def _release_snippet_lock(self):
        """Release snippet execution lock if held."""
        if not _FCNTL_AVAILABLE:
            return
        try:
            if self._lock_file_handle:
                fcntl.flock(self._lock_file_handle.fileno(), fcntl.LOCK_UN)
                try:
                    self._lock_file_handle.close()
                finally:
                    self._lock_file_handle = None
                logger.debug(f"Released snippet lock{f' at {self._lock_path}' if getattr(self, '_lock_path', None) else ''}")
        except Exception as e:
            logger.warning(f"Failed to release snippet lock: {e}")

    def _install_signal_handlers(self):
        """Install SIGTERM/SIGINT handlers to ensure clean shutdown and lock release."""
        def _graceful_exit(signum, frame):
            logger.info(f"Received signal {signum}; shutting down gracefully.")
            try:
                self._release_snippet_lock()
            finally:
                sys.exit(0)
        try:
            signal.signal(signal.SIGTERM, _graceful_exit)
            signal.signal(signal.SIGINT, _graceful_exit)
        except Exception:
            # Not fatal on platforms that don't support signal in this context
            pass

    def _get_max_jitter_seconds(self) -> float:
        """Read max jitter seconds from env WEGWEISER_ONESHOT_JITTER or default to 0."""
        val = os.environ.get("WEGWEISER_ONESHOT_JITTER", "").strip()
        if not val:
            return 0.0
        try:
            v = float(val)
            return max(0.0, v)
        except Exception:
            logger.warning(f"Invalid WEGWEISER_ONESHOT_JITTER value: {val!r}. Ignoring.")
            return 0.0


def main():
    """Entry point"""
    try:
        parser = argparse.ArgumentParser(description='Wegweiser Agent')
        parser.add_argument('-v', '--version', action='store_true', help='Show version')
        parser.add_argument('-d', '--debug', action='store_true', help='Debug mode')
        parser.add_argument('-c', '--config', help='Config file path')
        parser.add_argument('-g', '--groupUuid', help='Group UUID (for registration)')
        parser.add_argument('-s', '--serverAddr', help='Server address (for registration)')
        parser.add_argument('--once', action='store_true', help='Process pending snippets once and exit')
        parser.add_argument('--jitter', type=float, default=None, help='Max startup jitter in seconds (overrides env)')

        args = parser.parse_args()

        if args.version:
            print(f"Wegweiser Agent {WegweiserAgent.VERSION}")
            sys.exit(0)

        agent = WegweiserAgent(config_path=args.config, debug=args.debug)

        # CLI override for jitter (optional)
        if args.jitter is not None:
            os.environ["WEGWEISER_ONESHOT_JITTER"] = str(max(0.0, args.jitter))

        # Check if this is a registration call
        if args.groupUuid and args.serverAddr:
            logger.info("Registration mode detected")
            logger.info(f"Group UUID: {args.groupUuid}")
            logger.info(f"Server Address: {args.serverAddr}")
            if agent._register_device(args.groupUuid, args.serverAddr):
                logger.info("Registration successful")
                sys.exit(0)
            else:
                logger.error("Registration failed")
                sys.exit(1)

        # Normal operation mode
        if args.once:
            sys.exit(agent.run_once())
        else:
            agent.run()

    except Exception as e:
        print(f"FATAL ERROR: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc(file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()

