import pytest
import json
from unittest.mock import patch, MagicMock

from app.routes.ai.wegcoin.routes import get_wegcoin_balance

class TestWegcoinRoutes:
    """Tests for the wegcoin/routes.py module."""

    def test_get_wegcoin_balance_no_tenant_in_session(self, client):
        """Test the get_wegcoin_balance route when no tenant is in the session."""
        # Call the route with an empty session
        response = client.get('/ai/tenant/wegcoin_balance')
        
        # Check the response
        assert response.status_code == 401  # Unauthorized due to @login_required

    def test_get_wegcoin_balance_tenant_not_found(self, logged_in_client):
        """Test the get_wegcoin_balance route when the tenant is not found."""
        # Mock the Tenants.query.get method
        with patch('app.routes.ai.wegcoin.routes.Tenants.query.get') as mock_get:
            # Set up the mock
            mock_get.return_value = None
            
            # Call the route
            response = logged_in_client.get('/ai/tenant/wegcoin_balance')
            
            # Check the response
            assert response.status_code == 404
            data = json.loads(response.data)
            assert data['error'] == 'Tenant not found'
            
            # Check that the function was called with the correct arguments
            mock_get.assert_called_once_with(logged_in_client.session['tenant_uuid'])

    def test_get_wegcoin_balance_success(self, logged_in_client):
        """Test the get_wegcoin_balance route when successful."""
        # Mock the Tenants.query.get method
        with patch('app.routes.ai.wegcoin.routes.Tenants.query.get') as mock_get:
            # Set up the mock
            mock_tenant = MagicMock()
            mock_tenant.available_wegcoins = 100
            mock_tenant.calculate_total_spent.return_value = 50
            mock_get.return_value = mock_tenant
            
            # Call the route
            response = logged_in_client.get('/ai/tenant/wegcoin_balance')
            
            # Check the response
            assert response.status_code == 200
            data = json.loads(response.data)
            assert data['balance'] == 100
            assert data['total_spent'] == 50
            
            # Check that the functions were called with the correct arguments
            mock_get.assert_called_once_with(logged_in_client.session['tenant_uuid'])
            mock_tenant.calculate_total_spent.assert_called_once()
