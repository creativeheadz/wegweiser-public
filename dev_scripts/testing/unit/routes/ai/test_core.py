import pytest
import os
import uuid
from unittest.mock import patch, MagicMock

from app.routes.ai.core import (
    checkDir,
    get_entity,
    get_or_create_conversation,
    store_conversation,
    get_tenant_profile
)
from app.models import (
    Devices,
    Groups,
    Organisations,
    Tenants,
    Conversations,
    Messages
)

class TestCore:
    """Tests for the core.py module."""

    def test_check_dir(self, tmpdir):
        """Test the checkDir function."""
        # Create a temporary directory path
        test_dir = os.path.join(tmpdir, 'test_dir')
        
        # Call the function
        checkDir(test_dir)
        
        # Check that the directory was created
        assert os.path.isdir(test_dir)
        
        # Call the function again to test the case where the directory already exists
        checkDir(test_dir)
        
        # Check that the directory still exists
        assert os.path.isdir(test_dir)

    @pytest.mark.parametrize('entity_type, entity_class', [
        ('device', Devices),
        ('group', Groups),
        ('organisation', Organisations),
        ('tenant', Tenants),
        ('invalid', None)
    ])
    def test_get_entity(self, entity_type, entity_class, session):
        """Test the get_entity function."""
        # Mock the query.get method
        with patch.object(entity_class, 'query') if entity_class else patch('app.routes.ai.core.Devices.query') as mock_query:
            mock_query.get.return_value = 'mock_entity' if entity_class else None
            
            # Call the function
            entity_uuid = uuid.uuid4()
            result = get_entity(entity_type, entity_uuid)
            
            # Check the result
            if entity_class:
                assert result == 'mock_entity'
                mock_query.get.assert_called_once_with(entity_uuid)
            else:
                assert result is None

    def test_get_or_create_conversation_existing(self, session):
        """Test the get_or_create_conversation function when a conversation exists."""
        # Mock the query.filter_by method
        with patch('app.routes.ai.core.LegacyConversationModel.query') as mock_query:
            mock_conversation = MagicMock()
            mock_query.filter_by.return_value.order_by.return_value.first.return_value = mock_conversation
            
            # Call the function
            entity_uuid = uuid.uuid4()
            result = get_or_create_conversation('device', entity_uuid)
            
            # Check the result
            assert result == mock_conversation
            mock_query.filter_by.assert_called_once_with(
                entityuuid=entity_uuid,
                entity_type='device'
            )

    def test_get_or_create_conversation_new_device(self, session):
        """Test the get_or_create_conversation function when creating a new device conversation."""
        # Mock the query.filter_by method
        with patch('app.routes.ai.core.LegacyConversationModel.query') as mock_query, \
             patch('app.routes.ai.core.get_tenant_uuid_for_entity') as mock_get_tenant_uuid, \
             patch('app.routes.ai.core.db.session.add') as mock_add, \
             patch('app.routes.ai.core.db.session.commit') as mock_commit:
            
            # Set up the mocks
            mock_query.filter_by.return_value.order_by.return_value.first.return_value = None
            mock_get_tenant_uuid.return_value = 'tenant_uuid'
            
            # Call the function
            entity_uuid = uuid.uuid4()
            result = get_or_create_conversation('device', entity_uuid)
            
            # Check the result
            assert isinstance(result, Conversations)
            assert result.entityuuid == entity_uuid
            assert result.entity_type == 'device'
            assert result.tenantuuid == 'tenant_uuid'
            mock_add.assert_called_once_with(result)
            mock_commit.assert_called_once()

    def test_get_tenant_profile(self):
        """Test the get_tenant_profile function."""
        # Create a mock tenant
        tenant = MagicMock()
        tenant.specializations = 'Test Specializations'
        tenant.sla_details = 'Test SLA Details'
        tenant.industry = 'Test Industry'
        tenant.preferred_communication_style = 'Test Style'
        
        # Call the function
        result = get_tenant_profile(tenant)
        
        # Check the result
        assert 'Specializations: Test Specializations' in result
        assert 'SLA Details: Test SLA Details' in result
        assert 'Industry: Test Industry' in result
        assert 'Preferred Communication Style: Test Style' in result
