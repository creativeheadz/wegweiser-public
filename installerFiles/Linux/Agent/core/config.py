"""
Configuration Manager - Centralized configuration handling
"""

import os
import json
import platform
import logging
from pathlib import Path
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


class ConfigManager:
    """Centralized configuration management with validation"""
    
    def __init__(self, config_path: Optional[str] = None):
        """Initialize config manager"""
        self.config_path = config_path or self._get_default_config_path()
        self.config: Dict[str, Any] = {}
        self.base_dir = self._get_base_dir()
        self._ensure_directories()
    
    def _get_base_dir(self) -> Path:
        """Get base installation directory (cross-platform)"""
        system = platform.system()
        
        if system == 'Windows':
            base = Path('C:/Program Files (x86)/Wegweiser')
            if not base.exists():
                base = Path('C:/Program Files/Wegweiser')
            if not base.exists():
                base = Path('C:/Wegweiser')
        else:  # Linux, macOS
            base = Path('/opt/Wegweiser')
        
        return base
    
    def _get_default_config_path(self) -> str:
        """Get default config file path"""
        base = self._get_base_dir()
        return str(base / 'Config' / 'agent.config')
    
    def _ensure_directories(self):
        """Ensure all required directories exist"""
        dirs = [
            self.base_dir,
            self.base_dir / 'Config',
            self.base_dir / 'Logs',
            self.base_dir / 'Snippets',
            self.base_dir / 'Files'
        ]

        for dir_path in dirs:
            try:
                dir_path.mkdir(parents=True, exist_ok=True)
                logger.debug(f"Ensured directory exists: {dir_path}")
            except PermissionError:
                logger.warning(f"Permission denied creating directory: {dir_path}")
                # Try to create in config file's parent directory instead
                if dir_path == self.base_dir / 'Config':
                    config_parent = Path(self.config_path).parent
                    try:
                        config_parent.mkdir(parents=True, exist_ok=True)
                        logger.debug(f"Created config directory: {config_parent}")
                    except PermissionError as e:
                        logger.error(f"Cannot create config directory: {e}")
                        raise
    
    def load(self) -> bool:
        """Load configuration from file"""
        try:
            config_file = Path(self.config_path)
            
            if not config_file.exists():
                logger.warning(f"Config file not found: {self.config_path}")
                return False
            
            with open(config_file, 'r') as f:
                self.config = json.load(f)
            
            logger.info(f"Configuration loaded from {self.config_path}")
            return True
        
        except Exception as e:
            logger.error(f"Failed to load configuration: {e}")
            return False
    
    def save(self) -> bool:
        """Save configuration to file"""
        try:
            config_file = Path(self.config_path)
            config_file.parent.mkdir(parents=True, exist_ok=True)
            
            with open(config_file, 'w') as f:
                json.dump(self.config, f, indent=4)
            
            logger.info(f"Configuration saved to {self.config_path}")
            return True
        
        except Exception as e:
            logger.error(f"Failed to save configuration: {e}")
            return False
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value"""
        return self.config.get(key, default)
    
    def set(self, key: str, value: Any):
        """Set configuration value"""
        self.config[key] = value
    
    def validate(self) -> bool:
        """Validate required configuration fields"""
        required_fields = ['deviceuuid', 'agentprivpem', 'agentpubpem', 'serverpubpem']
        
        for field in required_fields:
            if field not in self.config:
                logger.error(f"Missing required config field: {field}")
                return False
        
        return True
    
    @property
    def device_uuid(self) -> str:
        """Get device UUID"""
        return self.config.get('deviceuuid', '')
    
    @property
    def server_addr(self) -> str:
        """Get server address"""
        return self.config.get('serverAddr', 'app.wegweiser.tech')
    
    @property
    def log_dir(self) -> Path:
        """Get log directory"""
        return self.base_dir / 'Logs'
    
    @property
    def snippets_dir(self) -> Path:
        """Get snippets directory"""
        return self.base_dir / 'Snippets'
    
    @property
    def files_dir(self) -> Path:
        """Get files directory"""
        return self.base_dir / 'Files'

