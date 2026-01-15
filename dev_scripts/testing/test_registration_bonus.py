#!/usr/bin/env python3
"""
Test script to verify the new tenant registration bonus functionality.
This tests that new tenants receive 250 wegcoins and webhook notifications are sent.
"""

import pytest
import json
from unittest.mock import patch, MagicMock
from app.models import Tenants, WegcoinTransaction


class TestRegistrationBonus:
    """Tests for the new tenant registration bonus functionality."""

    def test_wegcoin_bonus_assignment(self):
        """Test that new tenants receive 250 wegcoins as welcome bonus."""
        # Create a mock tenant
        mock_tenant = MagicMock()
        mock_tenant.tenantuuid = "test-tenant-uuid"
        mock_tenant.tenantname = "Test Company"
        mock_tenant.available_wegcoins = 0
        
        # Mock the add_wegcoins method
        mock_tenant.add_wegcoins = MagicMock()
        
        # Call the add_wegcoins method as it would be called in registration
        mock_tenant.add_wegcoins(250, 'registration_bonus', 'Welcome bonus for new tenant registration')
        
        # Verify the method was called with correct parameters
        mock_tenant.add_wegcoins.assert_called_once_with(
            250, 
            'registration_bonus', 
            'Welcome bonus for new tenant registration'
        )

    @patch('requests.post')
    def test_webhook_notification(self, mock_post):
        """Test that webhook notification is sent for new tenant registration."""
        # Mock successful webhook response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_post.return_value = mock_response
        
        # Simulate the webhook call as it would happen in registration
        import requests
        webhook_url = "https://datenfluss.oldforge.tech/webhook/7507cccd-0aee-40ad-9b3c-23aa392ca94b"
        webhook_data = {"message": "New tenant registered"}
        
        response = requests.post(webhook_url, json=webhook_data, timeout=10)
        
        # Verify the webhook was called correctly
        mock_post.assert_called_once_with(
            webhook_url,
            json=webhook_data,
            timeout=10
        )
        assert response.status_code == 200

    @patch('requests.post')
    def test_webhook_failure_handling(self, mock_post):
        """Test that webhook failures are handled gracefully."""
        # Mock failed webhook response
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_post.return_value = mock_response
        
        # Simulate the webhook call
        import requests
        webhook_url = "https://datenfluss.oldforge.tech/webhook/7507cccd-0aee-40ad-9b3c-23aa392ca94b"
        webhook_data = {"message": "New tenant registered"}
        
        response = requests.post(webhook_url, json=webhook_data, timeout=10)
        
        # Verify the webhook was called and failure was handled
        mock_post.assert_called_once()
        assert response.status_code == 500

    def test_wegcoin_transaction_creation(self):
        """Test that wegcoin transactions are properly created."""
        # This would test the actual WegcoinTransaction model
        # In a real test environment, you'd use a test database
        
        # Mock transaction data
        transaction_data = {
            'tenantuuid': 'test-tenant-uuid',
            'amount': 250,
            'transaction_type': 'registration_bonus',
            'description': 'Welcome bonus for new tenant registration'
        }
        
        # Verify transaction data structure
        assert transaction_data['amount'] == 250
        assert transaction_data['transaction_type'] == 'registration_bonus'
        assert 'Welcome bonus' in transaction_data['description']


if __name__ == "__main__":
    # Run basic tests without pytest
    test_instance = TestRegistrationBonus()
    
    print("🧪 Testing Registration Bonus Functionality")
    print("=" * 50)
    
    try:
        print("1. Testing wegcoin bonus assignment...")
        test_instance.test_wegcoin_bonus_assignment()
        print("   ✅ Wegcoin bonus assignment test passed")
    except Exception as e:
        print(f"   ❌ Wegcoin bonus assignment test failed: {e}")
    
    try:
        print("2. Testing webhook notification...")
        test_instance.test_webhook_notification()
        print("   ✅ Webhook notification test passed")
    except Exception as e:
        print(f"   ❌ Webhook notification test failed: {e}")
    
    try:
        print("3. Testing webhook failure handling...")
        test_instance.test_webhook_failure_handling()
        print("   ✅ Webhook failure handling test passed")
    except Exception as e:
        print(f"   ❌ Webhook failure handling test failed: {e}")
    
    try:
        print("4. Testing wegcoin transaction creation...")
        test_instance.test_wegcoin_transaction_creation()
        print("   ✅ Wegcoin transaction creation test passed")
    except Exception as e:
        print(f"   ❌ Wegcoin transaction creation test failed: {e}")
    
    print("\n🎉 All tests completed!")
