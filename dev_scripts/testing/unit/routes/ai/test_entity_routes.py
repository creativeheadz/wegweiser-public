import pytest
import uuid
import json
from unittest.mock import patch, MagicMock

from app.routes.ai.entity.routes import (
    get_health_score_analysis,
    get_entity_suggestions
)

class TestEntityRoutes:
    """Tests for the entity/routes.py module."""

    def test_get_health_score_analysis(self, logged_in_client):
        """Test the get_health_score_analysis route."""
        # Mock the generate_health_score_analysis function
        with patch('app.routes.ai.entity.routes.generate_health_score_analysis') as mock_generate:
            # Set up the mock
            mock_generate.return_value = 'Test health score analysis'
            
            # Call the route
            entity_uuid = uuid.uuid4()
            response = logged_in_client.get(f'/ai/device/{entity_uuid}/health_score_analysis')
            
            # Check the response
            assert response.status_code == 200
            data = json.loads(response.data)
            assert data['analysis'] == 'Test health score analysis'
            
            # Check that the function was called with the correct arguments
            mock_generate.assert_called_once_with('device', entity_uuid)

    def test_get_entity_suggestions(self, logged_in_client):
        """Test the get_entity_suggestions route."""
        # Mock the generate_entity_suggestions function
        with patch('app.routes.ai.entity.routes.generate_entity_suggestions') as mock_generate:
            # Set up the mock
            mock_generate.return_value = ['Suggestion 1', 'Suggestion 2']
            
            # Call the route
            entity_uuid = uuid.uuid4()
            response = logged_in_client.get(f'/ai/group/{entity_uuid}/suggestions')
            
            # Check the response
            assert response.status_code == 200
            data = json.loads(response.data)
            assert data['suggestions'] == ['Suggestion 1', 'Suggestion 2']
            
            # Check that the function was called with the correct arguments
            mock_generate.assert_called_once_with('group', entity_uuid)
