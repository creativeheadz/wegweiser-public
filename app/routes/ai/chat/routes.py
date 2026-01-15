# Filepath: app/routes/ai/chat/routes.py
# Chat-related endpoints

from flask import Blueprint, request, jsonify, session
import logging
from uuid import UUID
import time

from app.models import (
    db,
    Devices,
    DeviceMetadata,
    Tenants,
    Messages
)
from app.models import Conversations as LegacyConversationModel

from app.utilities.app_logging_helper import log_with_route
from app.utilities.app_access_login_required import login_required
from app.utilities.langchain_utils import (
    create_langchain_conversation,
    get_ai_response,
    adapt_response_style,
    MEMORY_WINDOW_SIZE
)
from app.utilities.knowledge_graph import KnowledgeGraph

from app.routes.ai import ai_bp
from app.routes.ai.core import (
    get_entity,
    get_or_create_conversation,
    store_conversation,
    get_tenant_profile,
    _extract_top_events
)
from app.routes.ai.entity.utils import get_entity_context

CHAT_HISTORY_LIMIT = 10  # Limit chat history to last 10 messages

@ai_bp.route('/<entity_type>/<uuid:entity_uuid>/chat', methods=['POST'])
@login_required
def entity_chat(entity_type, entity_uuid):
    user_id = session.get('user_id')
    user_firstname = session.get('userfirstname', 'User')
    log_with_route(logging.INFO, f'Initiating chat for {entity_type} UUID {entity_uuid} by user ID {user_id}.')

    try:
        entity = get_entity(entity_type, entity_uuid)
        if not entity:
            return jsonify({"error": f"{entity_type.capitalize()} not found"}), 404

        user_message = request.json.get('message')
        user_message_lower = user_message.lower()

        conversation = get_or_create_conversation(entity_type, entity_uuid)

        # Initialize knowledge_graph and get device info
        device_info = {}
        knowledge_graph = None
        if entity_type == 'device':
            knowledge_graph = KnowledgeGraph(str(entity_uuid))

            # Always force refresh for queries about current status
            force_refresh = any(term in user_message_lower for term in [
                'health', 'score', 'status', 'current', 'now', 'journal', 'log',
                'temperature', 'usage', 'performance', 'memory', 'storage', 'network'
            ])



            # Get all relevant device information based on the query
            try:
                if 'health' in user_message_lower or 'score' in user_message_lower or 'status' in user_message_lower:
                    device_info['health'] = knowledge_graph.query("health", force_refresh=force_refresh)

                if 'memory' in user_message_lower or 'ram' in user_message_lower:
                    device_info['memory'] = knowledge_graph.query("memory", force_refresh=force_refresh)

                if 'network' in user_message_lower:
                    device_info['network'] = knowledge_graph.query("network", force_refresh=force_refresh)

                if 'storage' in user_message_lower or 'disk' in user_message_lower or 'drive' in user_message_lower:
                    device_info['storage'] = knowledge_graph.query("storage", force_refresh=force_refresh)

                if 'gpu' in user_message_lower or 'graphics' in user_message_lower:
                    device_info['gpu'] = knowledge_graph.query("gpu", force_refresh=force_refresh)

                if 'cpu' in user_message_lower or 'processor' in user_message_lower or 'system' in user_message_lower:
                    device_info['system'] = knowledge_graph.query("system", force_refresh=force_refresh)

                # NEW CODE: Check if this is a web search query
                # Detect phrases like "search web for X", "look up X online", "find X on the internet"
                web_search_patterns = [
                    'search web', 'search the web', 'search online', 'search internet',
                    'look up online', 'find online', 'web search', 'google',
                    'search for', 'find information about', 'search about'
                ]

                if any(pattern in user_message_lower for pattern in web_search_patterns):
                    # Extract the search query from the user message
                    search_query = None
                    for pattern in web_search_patterns:
                        if pattern in user_message_lower:
                            parts = user_message.split(pattern, 1)
                            if len(parts) > 1:
                                search_query = parts[1].strip()
                                break

                    # If we couldn't parse it this way, just use everything after "search"
                    if not search_query and 'search' in user_message_lower:
                        search_query = user_message.split('search', 1)[1].strip()

                    # If we still don't have a search query, use the entire message
                    if not search_query:
                        search_query = user_message

                    log_with_route(logging.INFO, f"Web search detected: '{search_query}'")

                    # Perform the web search using knowledge graph
                    if knowledge_graph:
                        web_result = knowledge_graph.query(f"web:{search_query}", force_refresh=True)

                        if 'error' not in web_result:
                            # Format the response
                            ai_response_html = f"<p>Here's what I found online about '{search_query}':</p>"
                            ai_response_html += f"<p>{web_result.get('summary', 'No summary available.')}</p>"

                            if 'sources' in web_result and web_result['sources']:
                                ai_response_html += "<p>Sources:</p><ul>"
                                for source in web_result['sources']:
                                    ai_response_html += f"<li><a href='{source['url']}'>{source['title']}</a></li>"
                                ai_response_html += "</ul>"

                            # Calculate cost - less than normal AI responses since we're not using the LLM as much
                            web_search_cost = 1  # Base cost for any interaction

                            # Save conversation and return response
                            store_conversation(conversation, user_id, entity_uuid, entity.tenantuuid, user_message, ai_response_html, entity_type)
                            return jsonify({
                                "response": ai_response_html,
                                "conversation_uuid": str(conversation.conversationuuid),
                                "token_usage": 0,  # Web search doesn't use tokens like LLM does
                                "wegcoin_cost": web_search_cost,
                                "conversation_context": {
                                    "lastUserMessage": user_message,
                                    "lastAIMessage": ai_response_html,
                                    "entity_type": entity_type,
                                    "entity_uuid": str(entity_uuid)
                                },
                                "is_formatted": True
                            })

                # If we get here, either we don't have a knowledge graph or the web search failed
                # Continue with normal processing

                # If there's a reference to logs or journals, fetch specific log data
                if 'journal' in user_message_lower or 'log' in user_message_lower:
                    # Get the latest journal logs metadata
                    journal_logs = DeviceMetadata.query.filter(
                        DeviceMetadata.deviceuuid == entity_uuid,
                        DeviceMetadata.metalogos_type.like('journal%')
                    ).order_by(DeviceMetadata.created_at.desc()).first()

                    if journal_logs:
                        device_info['journal_logs'] = {
                            'metadata': {
                                'created_at': journal_logs.created_at,
                                'analyzed_at': journal_logs.analyzed_at,
                                'score': journal_logs.score
                            },
                            'analysis': journal_logs.ai_analysis,
                            'top_events': _extract_top_events(journal_logs.metalogos)
                        }

                # If there's a reference to security, audit, lynis, or hardening, fetch Lynis audit data
                if any(term in user_message_lower for term in ['security', 'audit', 'lynis', 'hardening', 'vulnerability', 'vulnerabilities']):
                    # Get the latest Lynis security audit
                    lynis_audit = DeviceMetadata.query.filter(
                        DeviceMetadata.deviceuuid == entity_uuid,
                        DeviceMetadata.metalogos_type == 'lynis_audit',
                        DeviceMetadata.processing_status == 'processed'
                    ).order_by(DeviceMetadata.created_at.desc()).first()

                    if lynis_audit:
                        # Use the parser to get AI-optimized payload
                        from app.utilities.lynis_parser import LynisResultParser
                        parser = LynisResultParser(json_data=lynis_audit.metalogos)
                        ai_payload = parser.get_ai_summary_payload()

                        device_info['security_audit'] = {
                            'metadata': {
                                'created_at': lynis_audit.created_at,
                                'analyzed_at': lynis_audit.analyzed_at,
                                'hardening_score': lynis_audit.score
                            },
                            'audit_summary': ai_payload,
                            'report_available': True
                        }
            except Exception as e:
                log_with_route(logging.ERROR, f"Error querying device info: {str(e)}")
                # Continue with whatever info we have

        # Get entity context with device info
        entity_context = get_entity_context(entity_type, entity_uuid, device_info)
        tenant = Tenants.query.get(entity.tenantuuid)
        tenant_profile = get_tenant_profile(tenant)
        user_context = f"User's name: {user_firstname}"

        # Get history before creating conversation chain
        current_history = []
        if conversation.conversationuuid:
            # Use sequence_id for guaranteed chronological order
            all_messages = Messages.query.filter_by(
                conversationuuid=conversation.conversationuuid,
                message_type='chat'
            ).order_by(Messages.sequence_id.asc()).all()

            # Take the most recent messages for memory window
            current_history = all_messages[-(MEMORY_WINDOW_SIZE*2):] if len(all_messages) > MEMORY_WINDOW_SIZE*2 else all_messages

        # Clear conversation history for memory-specific queries to ensure fresh data
        if any(term in user_message_lower for term in ['current memory', 'memory now', 'ram usage now']):
            current_history = []

        # Create conversation chain and get response
        conversation_chain = create_langchain_conversation(
            str(entity_uuid),
            entity_type,
            tenant_profile,
            entity_context,
            user_context,
            current_history,
            knowledge_graph
        )

        # Get AI response and track token usage
        ai_response = get_ai_response(conversation_chain, user_message, f"{entity_type}_{entity_uuid}")

        # Extract token usage from response
        token_usage = 0
        if hasattr(ai_response, 'token_usage'):
            token_usage = ai_response.token_usage
        elif hasattr(ai_response, '_token_usage'):
            token_usage = ai_response._token_usage

        # Calculate Wegcoin cost - base cost is 1 Wegcoin per chat message
        # Plus additional cost based on tokens (1 Wegcoin per 1000 tokens)
        base_cost = 1
        token_cost = token_usage // 1000 if token_usage > 0 else 0
        total_cost = base_cost + token_cost

        ai_response_content = ai_response.content if hasattr(ai_response, 'content') else str(ai_response)
        ai_response_content = adapt_response_style(ai_response_content, tenant.preferred_communication_style)

        # DO NOT convert or escape, just store and return as-is
        ai_response_html = ai_response_content

        # Process billing
        if not tenant.deduct_wegcoins(total_cost, f"Chat interaction with {entity_type}"):
            return jsonify({"error": "Insufficient Wegcoins for this operation"}), 403

        store_conversation(conversation, user_id, entity_uuid, tenant.tenantuuid, user_message, ai_response_html, entity_type)
        return jsonify({
            "response": ai_response_html,
            "conversation_uuid": str(conversation.conversationuuid),
            "token_usage": token_usage,
            "wegcoin_cost": total_cost,
            "conversation_context": {
                "lastUserMessage": user_message,
                "lastAIMessage": ai_response_html,
                "entity_type": entity_type,
                "entity_uuid": str(entity_uuid)
            },
            "is_formatted": True  # Indicate this is HTML/markup
        })
    except Exception as e:
        log_with_route(logging.ERROR, f'Error in entity_chat: {str(e)}', exc_info=True)
        return jsonify({"error": "An error occurred processing your request"}), 500

@ai_bp.route('/<entity_type>/<uuid:entity_uuid>/chat_history', methods=['GET'])
def get_entity_chat_history(entity_type, entity_uuid):
    """Get chat history for an entity"""
    conversation = LegacyConversationModel.query.filter_by(
        entityuuid=entity_uuid,
        entity_type=entity_type
    ).order_by(LegacyConversationModel.last_updated.desc()).first()

    if not conversation:
        log_with_route(logging.INFO, f'No conversation history found for {entity_type} UUID {entity_uuid}.')
        return jsonify({"messages": []})

    # Get messages ordered by sequence_id for guaranteed chronological order
    # This ensures proper conversation flow regardless of timestamp precision
    messages = Messages.query.filter_by(
        conversationuuid=conversation.conversationuuid,
        message_type='chat'
    ).order_by(Messages.sequence_id.asc()).all()

    # Take only the last CHAT_HISTORY_LIMIT messages (most recent)
    messages = messages[-CHAT_HISTORY_LIMIT:] if len(messages) > CHAT_HISTORY_LIMIT else messages

    chat_history = [
        {
            "content": message.content,  # DO NOT convert or escape, just return as-is
            "is_ai": message.useruuid is None,
            "timestamp": message.created_at,
            "is_formatted": True  # Always send as HTML/markup now
        }
        for message in messages  # No need to reverse since we're already in chronological order
    ]

    log_with_route(logging.INFO, f'Retrieved {len(chat_history)} messages from chat history.')
    return jsonify({"messages": chat_history})
