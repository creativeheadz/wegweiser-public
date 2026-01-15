"""
Tool Registry - Auto-discovers and manages MCP tools
"""

import json
import logging
import importlib
from pathlib import Path
from typing import Dict, Any, Optional
from .base_tool import MCPTool

logger = logging.getLogger(__name__)


class ToolRegistry:
    """Registry for auto-discovering and managing MCP tools"""

    def __init__(self, tools_dir: Path, config: Dict[str, Any] = None):
        """
        Initialize tool registry

        Args:
            tools_dir: Path to tools directory
            config: Configuration dict with enabled_tools list
        """
        self.tools_dir = Path(tools_dir)
        self.config = config or {}
        self.tools: Dict[str, MCPTool] = {}
        self.metadata: Dict[str, Any] = {}

    def discover_and_load(self) -> bool:
        """
        Discover and load all tools from tools directory

        Returns:
            bool: True if discovery successful, False otherwise
        """
        try:
            if not self.tools_dir.exists():
                logger.error(f"Tools directory not found: {self.tools_dir}")
                return False

            enabled_tools = self.config.get("enabled_tools", [])
            logger.info(f"Enabled tools: {enabled_tools}")

            # Iterate through tool directories
            for tool_dir in self.tools_dir.iterdir():
                if not tool_dir.is_dir() or tool_dir.name.startswith("_"):
                    continue

                tool_name = tool_dir.name

                # Check if tool is enabled
                if enabled_tools and tool_name not in enabled_tools:
                    logger.info(f"Skipping disabled tool: {tool_name}")
                    continue

                # Try to load manifest
                manifest_path = tool_dir / "manifest.json"
                if not manifest_path.exists():
                    logger.warning(f"No manifest found for tool: {tool_name}")
                    continue

                success = self._load_tool(tool_name, tool_dir, manifest_path)
                if success:
                    logger.info(f"✓ Loaded tool: {tool_name}")
                else:
                    logger.warning(f"✗ Failed to load tool: {tool_name}")

            logger.info(f"Tool discovery complete. Loaded {len(self.tools)} tools")
            return len(self.tools) > 0

        except Exception as e:
            logger.error(f"Error during tool discovery: {e}", exc_info=True)
            return False

    def _load_tool(
        self, tool_package_name: str, tool_dir: Path, manifest_path: Path
    ) -> bool:
        """
        Load tools from a package directory

        Args:
            tool_package_name: Name of the tool package
            tool_dir: Directory containing the tool
            manifest_path: Path to manifest.json

        Returns:
            bool: True if at least one tool loaded successfully
        """
        try:
            # Read manifest
            with open(manifest_path, "r") as f:
                manifest = json.load(f)

            logger.debug(f"Manifest for {tool_package_name}: {manifest}")

            # Get tools list
            tools_list = manifest.get("tools", [])
            if not tools_list:
                logger.warning(
                    f"No tools defined in manifest for {tool_package_name}"
                )
                return False

            # Add tool directory to sys.path for imports
            import sys
            if str(tool_dir) not in sys.path:
                sys.path.insert(0, str(tool_dir))

            loaded_count = 0

            # Load each tool
            for tool_spec in tools_list:
                try:
                    tool_name = tool_spec.get("name")
                    module_spec = tool_spec.get("module")

                    if not tool_name or not module_spec:
                        logger.warning(
                            f"Tool spec missing name or module in {tool_package_name}"
                        )
                        continue

                    module_name, class_name = module_spec.split(":")

                    # Import the module
                    try:
                        module = importlib.import_module(module_name)
                    except ImportError as e:
                        logger.error(
                            f"Failed to import {module_name} from {tool_dir}: {e}"
                        )
                        continue

                    # Get the class
                    if not hasattr(module, class_name):
                        logger.error(
                            f"Class {class_name} not found in {module.__name__}"
                        )
                        continue

                    tool_class = getattr(module, class_name)

                    # Instantiate the tool
                    tool_instance = tool_class()
                    if not isinstance(tool_instance, MCPTool):
                        logger.error(
                            f"{tool_name} does not inherit from MCPTool"
                        )
                        continue

                    # Store tool and metadata
                    self.tools[tool_name] = tool_instance

                    # Build metadata from manifest spec + tool metadata
                    tool_metadata = tool_instance.get_metadata()
                    tool_metadata.update(
                        {
                            "description": tool_spec.get("description"),
                            "parameters": tool_spec.get("parameters"),
                        }
                    )
                    self.metadata[tool_name] = tool_metadata

                    logger.debug(f"Loaded tool: {tool_name}")
                    loaded_count += 1

                except Exception as e:
                    logger.error(
                        f"Error loading tool from {tool_package_name}: {e}",
                        exc_info=True,
                    )
                    continue

            return loaded_count > 0

        except Exception as e:
            logger.error(
                f"Error loading tool package {tool_package_name}: {e}",
                exc_info=True,
            )
            return False

    def get_tool(self, tool_name: str) -> Optional[MCPTool]:
        """Get a tool by name"""
        return self.tools.get(tool_name)

    def list_tools(self) -> Dict[str, Any]:
        """Get metadata for all loaded tools"""
        return self.metadata

    def get_tool_metadata(self, tool_name: str) -> Optional[Dict[str, Any]]:
        """Get metadata for a specific tool"""
        return self.metadata.get(tool_name)

    def has_tool(self, tool_name: str) -> bool:
        """Check if a tool is loaded"""
        return tool_name in self.tools
