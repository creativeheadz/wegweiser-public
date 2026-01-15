"""
Tests for configuration manager
"""

import pytest
import json
import tempfile
from pathlib import Path
from agent_refactored.core.config import ConfigManager


class TestConfigManager:
    """Test configuration management"""
    
    def test_config_creation(self):
        """Test config manager creation"""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / 'agent.config'
            config = ConfigManager(str(config_path))
            assert config.config_path == str(config_path)
    
    def test_config_save_and_load(self):
        """Test saving and loading config"""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / 'agent.config'
            
            # Create and save
            config = ConfigManager(str(config_path))
            config.set('deviceuuid', 'test-uuid-123')
            config.set('serverAddr', 'test.server.com')
            assert config.save()
            
            # Load and verify
            config2 = ConfigManager(str(config_path))
            assert config2.load()
            assert config2.get('deviceuuid') == 'test-uuid-123'
            assert config2.get('serverAddr') == 'test.server.com'
    
    def test_config_validation(self):
        """Test config validation"""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / 'agent.config'
            config = ConfigManager(str(config_path))
            
            # Empty config should fail validation
            assert not config.validate()
            
            # Add required fields
            config.set('deviceuuid', 'test-uuid')
            config.set('agentprivpem', 'private-key')
            config.set('agentpubpem', 'public-key')
            config.set('serverpubpem', 'server-key')
            
            # Should pass validation
            assert config.validate()
    
    def test_config_properties(self):
        """Test config properties"""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / 'agent.config'
            config = ConfigManager(str(config_path))
            
            config.set('deviceuuid', 'test-uuid')
            config.set('serverAddr', 'test.server.com')
            
            assert config.device_uuid == 'test-uuid'
            assert config.server_addr == 'test.server.com'
            assert isinstance(config.log_dir, Path)
            assert isinstance(config.snippets_dir, Path)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])

