"""
Configuration Manager for MCP Framework
"""

import json
import logging
import yaml
from pathlib import Path
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


class ConfigManager:
    """Manages MCP framework configuration"""

    def __init__(self, config_dir: Path = None):
        """
        Initialize configuration manager

        Args:
            config_dir: Path to config directory (defaults to ../config/)
        """
        if config_dir is None:
            config_dir = Path(__file__).parent.parent / "config"

        self.config_dir = Path(config_dir)
        self.config: Dict[str, Any] = {}
        self._load_config()

    def _load_config(self) -> None:
        """Load configuration from YAML/JSON files"""
        try:
            # Load tools.yaml
            tools_config_path = self.config_dir / "tools.yaml"
            if tools_config_path.exists():
                with open(tools_config_path, "r") as f:
                    tools_config = yaml.safe_load(f) or {}
                self.config.update(tools_config)
                logger.info(f"Loaded tools config from {tools_config_path}")

            # Load server.yaml
            server_config_path = self.config_dir / "server.yaml"
            if server_config_path.exists():
                with open(server_config_path, "r") as f:
                    server_config = yaml.safe_load(f) or {}
                self.config["server"] = server_config
                logger.info(f"Loaded server config from {server_config_path}")

            logger.debug(f"Loaded configuration: {self.config}")

        except Exception as e:
            logger.error(f"Error loading configuration: {e}")

    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value"""
        return self.config.get(key, default)

    def get_tool_config(self, tool_name: str) -> Dict[str, Any]:
        """Get configuration for a specific tool"""
        return self.config.get(tool_name, {})

    def is_tool_enabled(self, tool_name: str) -> bool:
        """Check if a tool is enabled"""
        enabled_tools = self.config.get("enabled_tools", [])
        return tool_name in enabled_tools

    def __getitem__(self, key: str) -> Any:
        """Dict-like access"""
        return self.config[key]

    def __contains__(self, key: str) -> bool:
        """Support 'in' operator"""
        return key in self.config
