import pytest
import uuid
import json
from unittest.mock import patch, MagicMock

from app.routes.ai.chat.routes import (
    entity_chat,
    get_entity_chat_history
)
from app.models import Messages

class TestChatRoutes:
    """Tests for the chat/routes.py module."""

    def test_entity_chat(self, logged_in_client):
        """Test the entity_chat route."""
        # Mock the necessary functions
        with patch('app.routes.ai.chat.routes.get_entity') as mock_get_entity, \
             patch('app.routes.ai.chat.routes.get_or_create_conversation') as mock_get_conversation, \
             patch('app.routes.ai.chat.routes.KnowledgeGraph') as mock_kg_class, \
             patch('app.routes.ai.chat.routes.get_entity_context') as mock_get_context, \
             patch('app.routes.ai.chat.routes.Tenants.query.get') as mock_get_tenant, \
             patch('app.routes.ai.chat.routes.get_tenant_profile') as mock_get_profile, \
             patch('app.routes.ai.chat.routes.Messages.query.filter_by') as mock_messages_query, \
             patch('app.routes.ai.chat.routes.create_langchain_conversation') as mock_create_conv, \
             patch('app.routes.ai.chat.routes.get_ai_response') as mock_get_response, \
             patch('app.routes.ai.chat.routes.adapt_response_style') as mock_adapt_style, \
             patch('app.routes.ai.chat.routes.store_conversation') as mock_store_conv:
            
            # Set up the mocks
            entity_uuid = uuid.uuid4()
            mock_entity = MagicMock()
            mock_entity.tenantuuid = 'tenant_uuid'
            mock_get_entity.return_value = mock_entity
            
            mock_conversation = MagicMock()
            mock_conversation.conversationuuid = 'conv_uuid'
            mock_get_conversation.return_value = mock_conversation
            
            mock_kg = MagicMock()
            mock_kg_class.return_value = mock_kg
            mock_kg.query.return_value = {'status': 'healthy'}
            
            mock_get_context.return_value = 'Entity context'
            
            mock_tenant = MagicMock()
            mock_tenant.preferred_communication_style = 'friendly'
            mock_tenant.deduct_wegcoins.return_value = True
            mock_get_tenant.return_value = mock_tenant
            
            mock_get_profile.return_value = 'Tenant profile'
            
            mock_messages = []
            mock_messages_query.return_value.order_by.return_value.limit.return_value.all.return_value = mock_messages
            
            mock_conv_chain = MagicMock()
            mock_create_conv.return_value = mock_conv_chain
            
            mock_ai_response = MagicMock()
            mock_ai_response.content = 'AI response content'
            mock_ai_response.token_usage = 500
            mock_get_response.return_value = mock_ai_response
            
            mock_adapt_style.return_value = 'Styled AI response'
            
            # Call the route
            response = logged_in_client.post(
                f'/ai/device/{entity_uuid}/chat',
                json={'message': 'Test message'}
            )
            
            # Check the response
            assert response.status_code == 200
            data = json.loads(response.data)
            assert data['response'] == 'Styled AI response'
            assert data['conversation_uuid'] == 'conv_uuid'
            assert data['token_usage'] == 500
            assert data['wegcoin_cost'] == 1  # Base cost
            assert data['is_formatted'] is True
            
            # Check that the functions were called with the correct arguments
            mock_get_entity.assert_called_once_with('device', entity_uuid)
            mock_get_conversation.assert_called_once_with('device', entity_uuid)
            mock_kg_class.assert_called_once_with(str(entity_uuid))
            mock_get_context.assert_called_once()
            mock_get_tenant.assert_called_once_with('tenant_uuid')
            mock_get_profile.assert_called_once_with(mock_tenant)
            mock_create_conv.assert_called_once()
            mock_get_response.assert_called_once_with(mock_conv_chain, 'Test message', 'device_' + str(entity_uuid))
            mock_adapt_style.assert_called_once_with('AI response content', 'friendly')
            mock_store_conv.assert_called_once_with(
                mock_conversation, 
                logged_in_client.session['user_id'], 
                entity_uuid, 
                mock_tenant.tenantuuid, 
                'Test message', 
                'Styled AI response', 
                'device'
            )

    def test_get_entity_chat_history_no_conversation(self, client):
        """Test the get_entity_chat_history route when no conversation exists."""
        # Mock the query.filter_by method
        with patch('app.routes.ai.chat.routes.LegacyConversationModel.query') as mock_query:
            # Set up the mock
            mock_query.filter_by.return_value.order_by.return_value.first.return_value = None
            
            # Call the route
            entity_uuid = uuid.uuid4()
            response = client.get(f'/ai/device/{entity_uuid}/chat_history')
            
            # Check the response
            assert response.status_code == 200
            data = json.loads(response.data)
            assert data['messages'] == []
            
            # Check that the function was called with the correct arguments
            mock_query.filter_by.assert_called_once_with(
                entityuuid=entity_uuid,
                entity_type='device'
            )

    def test_get_entity_chat_history_with_messages(self, client):
        """Test the get_entity_chat_history route when messages exist."""
        # Mock the necessary functions
        with patch('app.routes.ai.chat.routes.LegacyConversationModel.query') as mock_conv_query, \
             patch('app.routes.ai.chat.routes.Messages.query.filter_by') as mock_msg_query:
            
            # Set up the mocks
            mock_conversation = MagicMock()
            mock_conversation.conversationuuid = 'conv_uuid'
            mock_conv_query.filter_by.return_value.order_by.return_value.first.return_value = mock_conversation
            
            # Create mock messages
            mock_user_msg = MagicMock(spec=Messages)
            mock_user_msg.content = 'User message'
            mock_user_msg.useruuid = 'user_uuid'
            mock_user_msg.created_at = 1000
            
            mock_ai_msg = MagicMock(spec=Messages)
            mock_ai_msg.content = 'AI message'
            mock_ai_msg.useruuid = None
            mock_ai_msg.created_at = 1001
            
            mock_msg_query.return_value.order_by.return_value.limit.return_value.all.return_value = [
                mock_ai_msg, mock_user_msg
            ]
            
            # Call the route
            entity_uuid = uuid.uuid4()
            response = client.get(f'/ai/organisation/{entity_uuid}/chat_history')
            
            # Check the response
            assert response.status_code == 200
            data = json.loads(response.data)
            assert len(data['messages']) == 2
            
            # Messages should be in chronological order (reversed from the query)
            assert data['messages'][0]['content'] == 'User message'
            assert data['messages'][0]['is_ai'] is False
            assert data['messages'][0]['timestamp'] == 1000
            
            assert data['messages'][1]['content'] == 'AI message'
            assert data['messages'][1]['is_ai'] is True
            assert data['messages'][1]['timestamp'] == 1001
            
            # Check that the functions were called with the correct arguments
            mock_conv_query.filter_by.assert_called_once_with(
                entityuuid=entity_uuid,
                entity_type='organisation'
            )
            mock_msg_query.assert_called_once_with(
                conversationuuid='conv_uuid',
                message_type='chat'
            )
