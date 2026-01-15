import pytest
import json
from unittest.mock import patch, MagicMock

from app.routes.ai.health.routes import memory_health

class TestHealthRoutes:
    """Tests for the health/routes.py module."""

    def test_memory_health_success(self, logged_in_client):
        """Test the memory_health route when successful."""
        # Mock the MemoryStore class
        with patch('app.routes.ai.health.routes.MemoryStore') as mock_memory_store_class:
            # Set up the mock
            mock_memory_store = MagicMock()
            mock_memory_store.health_check.return_value = {
                'status': 'healthy',
                'memory_count': 100,
                'last_updated': '2023-01-01T00:00:00Z'
            }
            mock_memory_store_class.return_value = mock_memory_store
            
            # Call the route
            response = logged_in_client.get('/ai/memory/health')
            
            # Check the response
            assert response.status_code == 200
            data = json.loads(response.data)
            assert data['status'] == 'healthy'
            assert data['memory_count'] == 100
            assert data['last_updated'] == '2023-01-01T00:00:00Z'
            
            # Check that the function was called
            mock_memory_store.health_check.assert_called_once()

    def test_memory_health_import_error(self, logged_in_client):
        """Test the memory_health route when there's an import error."""
        # Mock the import to raise an ImportError
        with patch('app.routes.ai.health.routes.MemoryStore', side_effect=ImportError('Module not found')):
            # Call the route
            response = logged_in_client.get('/ai/memory/health')
            
            # Check the response
            assert response.status_code == 500
            data = json.loads(response.data)
            assert data['error'] == 'Memory store not available'

    def test_memory_health_exception(self, logged_in_client):
        """Test the memory_health route when there's an exception."""
        # Mock the MemoryStore class to raise an exception
        with patch('app.routes.ai.health.routes.MemoryStore') as mock_memory_store_class:
            # Set up the mock
            mock_memory_store = MagicMock()
            mock_memory_store.health_check.side_effect = Exception('Test exception')
            mock_memory_store_class.return_value = mock_memory_store
            
            # Call the route
            response = logged_in_client.get('/ai/memory/health')
            
            # Check the response
            assert response.status_code == 500
            data = json.loads(response.data)
            assert data['error'] == 'Failed to check memory health'
