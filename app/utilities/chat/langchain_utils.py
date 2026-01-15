from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain_openai import AzureChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables.history import RunnableWithMessageHistory
from langchain_core.messages import BaseMessage
from langchain_core.tools import StructuredTool
from flask import current_app
from app.models import (
    db, AIMemory, Devices, Groups, Organisations, Tenants,
    TenantMetadata, Conversations, Messages, DeviceMetadata,
    HealthScoreHistory
)
from app.utilities.app_logging_helper import log_with_route
from .knowledge_graph import KnowledgeGraph

import json
import time
import uuid
import logging
import tiktoken
import backoff
import re
from typing import List, Dict, Any, Union, Optional
from pydantic import Field, BaseModel
from uuid import UUID
from datetime import datetime, timedelta
from app.utilities.chat.mspconversationguide import MSPConversationGuide
from app.utilities.chat.mspbusinessimpactanalyzer import MSPBusinessImpactAnalyzer
from app.utilities.chat.custommemory import CustomMemory


# Constants
MEMORY_WINDOW_SIZE = 5  # Number of recent conversations to keep in memory
MAX_TOKENS_PER_MEMORY = 300  # Maximum number of tokens per memory item
DEFAULT_COMPLIANCE_STANDARDS = ["HIPAA", "PCI DSS", "GDPR", "SOC 2", "ISO 27001"]
MSP_CONVERSATION_TOPICS = [
    "device_performance", "security_issues", "network_monitoring",
    "client_reporting", "resource_planning", "compliance_checks",
    "business_continuity", "cost_optimization", "user_support",
    "proactive_maintenance"
]

@backoff.on_exception(backoff.expo, Exception, max_tries=3)
def retry_on_error():
    pass

class MSPBusinessImpact(BaseModel):
    """Model for business impact assessment for MSPs"""
    severity: str = Field(description="Impact severity (Critical, High, Medium, Low)")
    client_impact: str = Field(description="How this affects the client's business")
    revenue_risk: str = Field(description="Potential revenue impact for the MSP")
    mitigation_time: str = Field(description="Estimated time to mitigate")
    resources_needed: list = Field(description="Resources needed for resolution")




class EntityMemoryManager:
    def __init__(self):
        self.memories = {}

    def get_memory(self, entity_uuid: str | UUID, entity_type: str, tenant_uuid: str | UUID) -> CustomMemory:
        # Convert UUIDs to strings for consistent key handling
        key = (str(entity_uuid), entity_type, str(tenant_uuid))
        if key not in self.memories:
            self.memories[key] = CustomMemory(str(entity_uuid), entity_type, str(tenant_uuid))
        return self.memories[key]

    def clear_memory(self, entity_uuid: str, entity_type: str, tenant_uuid: str) -> None:
        key = (entity_uuid, entity_type, tenant_uuid)
        if key in self.memories:
            self.memories[key].clear()
            del self.memories[key]

    def save_memory(self, entity_uuid: str, entity_type: str, tenant_uuid: str) -> None:
        memory = self.get_memory(entity_uuid, entity_type, tenant_uuid)
        # Get the most recent conversation content
        recent_messages = memory.messages[-2:]
        if len(recent_messages) == 2:
            inputs = {"input": recent_messages[0].content}
            outputs = {"output": recent_messages[1].content}
        else:
            inputs, outputs = {}, {}
        memory._save_long_term_memory(inputs, outputs)

entity_memory_manager = EntityMemoryManager()

class MSPToolsGenerator:
    """Generate relevant MSP tool recommendations and usage guidance"""

    @staticmethod
    def get_tool_recommendations(tenant_profile: Dict[str, Any], issues: List[str]) -> Dict[str, Any]:
        """Generate MSP tool recommendations based on tenant profile and issues"""
        recommendations = {
            "current_tools": [],
            "missing_tools": [],
            "suggested_tools": []
        }

        # Map issues to tool categories
        issue_to_tool_map = {
            "security": ["endpoint_protection", "email_security", "security_suites", "dns_filtering"],
            "performance": ["rmm_type", "network_monitoring"],
            "compliance": ["security_suites", "it_documentation"],
            "documentation": ["it_documentation"],
            "resource_management": ["psa_service_desk"],
            "backup": ["bdr"],
            "communication": ["communication_collaboration"]
        }

        # Get current tools
        for category, value in tenant_profile.items():
            if value and value != "none":
                recommendations["current_tools"].append({
                    "category": category,
                    "tool": value
                })

        # Find missing tools based on issues
        for issue in issues:
            for category in issue_to_tool_map.get(issue, []):
                tool_value = tenant_profile.get(category)
                if not tool_value or tool_value == "none":
                    if category not in [item["category"] for item in recommendations["missing_tools"]]:
                        recommendations["missing_tools"].append({
                            "category": category,
                            "related_issue": issue
                        })

        # Generate suggestions for missing tools
        for missing in recommendations["missing_tools"]:
            category = missing["category"]
            issue = missing["related_issue"]

            # Common tool suggestions by category
            suggestions = {
                "endpoint_protection": ["SentinelOne", "CrowdStrike", "Sophos", "Bitdefender"],
                "email_security": ["Mimecast", "Proofpoint", "Barracuda"],
                "security_suites": ["ConnectWise Fortify", "Huntress", "Arctic Wolf"],
                "dns_filtering": ["Cisco Umbrella", "WebTitan", "DNSFilter"],
                "rmm_type": ["ConnectWise Automate", "NinjaRMM", "Datto RMM", "Atera"],
                "network_monitoring": ["Auvik", "PRTG", "SolarWinds"],
                "it_documentation": ["IT Glue", "Passportal", "Hudu"],
                "psa_service_desk": ["ConnectWise Manage", "Autotask", "HaloPSA"],
                "bdr": ["Datto", "Veeam", "Acronis"],
                "communication_collaboration": ["Microsoft Teams", "Slack", "Discord"]
            }

            if category in suggestions:
                recommendations["suggested_tools"].append({
                    "category": category,
                    "options": suggestions[category],
                    "related_issue": issue,
                    "integration_note": f"Look for tools that integrate with your existing systems like {', '.join([tool['tool'] for tool in recommendations['current_tools'][:2]])}" if recommendations["current_tools"] else "Consider your future integration needs when selecting tools"
                })

        return recommendations



def create_langchain_conversation(entity_uuid: str, entity_type: str, tenant_profile: str,
                                entity_context: str, user_context: str,
                                current_history: Optional[List] = None,
                                knowledge_graph: Optional[KnowledgeGraph] = None) -> Any:

    # Get entity object based on type
    if entity_type == 'device':
        entity = Devices.query.get(entity_uuid)
    elif entity_type == 'group':
        entity = Groups.query.get(entity_uuid)
    elif entity_type == 'organisation':
        entity = Organisations.query.get(entity_uuid)
    elif entity_type == 'tenant':
        entity = Tenants.query.get(entity_uuid)
    else:
        entity = None

    # Define base system prompt with MSP-specific guidance
    base_prompt = """You are a technical assistant for an MSP (Managed Service Provider) supporting IT infrastructure.

When assisting MSP staff:
1. Be proactive in identifying client impact of technical issues
2. Suggest specific tools and approaches relevant to MSPs
3. Consider SLAs and business implications in your responses
4. Provide actionable, specific recommendations
5. Format responses in a way that's easy to include in client documentation
6. When discussing device information, use the get_device_info tool for real-time data
7. For security and compliance issues, highlight business risks
8. Suggest relevant documentation and client communication approaches
"""

    system_prompt = base_prompt

    # Add MSP-specific context to prompts
    if entity_type == 'device':
        # Find group and org for this device to provide customer context
        device_group = None
        device_org = None

        if entity:
            device_group = Groups.query.get(entity.groupuuid) if entity.groupuuid else None
            if device_group and device_group.orguuid:
                device_org = Organisations.query.get(device_group.orguuid)

        system_prompt += f"""
Current device context:
{entity_context}

Device customer context: {device_org.orgname if device_org else 'Unknown client'} > {device_group.groupname if device_group else 'Unknown group'}
"""
    elif entity_type == 'group':
        # Count devices in group for context
        device_count = Devices.query.filter_by(groupuuid=entity_uuid).count() if entity else 0

        # Get organization info if available
        group_org = None
        if entity and entity.orguuid:
            group_org = Organisations.query.get(entity.orguuid)

        system_prompt += f"""
Current group context:
{entity_context}

Group contains {device_count} devices
Client: {group_org.orgname if group_org else 'Unknown client'}
"""
    elif entity_type == 'organisation':
        # Count groups and devices in org for context
        group_count = Groups.query.filter_by(orguuid=entity_uuid).count() if entity else 0

        # Get group UUIDs to count devices
        group_uuids = [g.groupuuid for g in Groups.query.filter_by(orguuid=entity_uuid).all()] if entity else []
        device_count = Devices.query.filter(Devices.groupuuid.in_(group_uuids)).count() if group_uuids else 0

        system_prompt += f"""
Current organisation context:
{entity_context}

Client overview: {group_count} groups, {device_count} devices
"""
    elif entity_type == 'tenant':
        # Add MSP-focused tenant context
        org_count = Organisations.query.filter_by(tenantuuid=entity_uuid).count() if entity else 0
        device_count = Devices.query.filter_by(tenantuuid=entity_uuid).count() if entity else 0

        system_prompt += f"""
Current MSP context:
{entity_context}

MSP overview: {org_count} clients, {device_count} managed devices
"""

    # Get tenant UUID for memory management
    tenant_uuid = get_tenant_uuid_for_entity(entity_uuid, entity_type)
    memory = entity_memory_manager.get_memory(entity_uuid, entity_type, tenant_uuid)

    # Add current history to memory if provided
    if current_history:
        for msg in current_history:
            if msg.useruuid:
                memory.messages.append(HumanMessage(content=msg.content))
            else:
                memory.messages.append(AIMessage(content=msg.content))

    # Get recent chat history
    recent_messages = memory.chat_memory_messages()
    recent_history = ""
    if recent_messages:
        last_exchanges = recent_messages[-MEMORY_WINDOW_SIZE*2:]  # Get last N exchanges (each exchange has 2 messages)
        recent_history = "\n".join([
            f"{'User' if i%2==0 else 'Assistant'}: {msg.content}"
            for i, msg in enumerate(last_exchanges)
        ])

    # Extract conversation topics for better context
    conversation_topics = []
    if hasattr(memory, 'conversation_topics'):
        conversation_topics = memory.conversation_topics

    # Get MSP-specific context
    msp_context = ""
    if hasattr(memory, '_get_msp_context'):
        msp_data = memory._get_msp_context()
        if msp_data.get('business_impact'):
            impact = msp_data['business_impact']
            msp_context += f"""
Business Impact Assessment:
- Severity: {impact.get('severity', 'Unknown')}
- Client Impact: {impact.get('client_impact', 'Unknown')}
- Recommended Priority: {impact.get('recommended_priority', 'Unknown')}
"""

# Update prompt template with MSP-specific structure
    prompt = ChatPromptTemplate.from_messages([
        ("system", """You are an AI assistant for an MSP (Managed Service Provider).

Entity Type: {entity_type}
Entity Profile: {entity_profile}
Context: {context}
User Context: {user_context}
Long-term Context: {long_term_context}
MSP Context: {msp_context}
Current Conversation Topics: {conversation_topics}

Recent Conversation History:
{recent_history}

When helping MSP staff:
1. Focus on business impact and client experience
2. Provide specific technical guidance with real-time device data
3. Connect technical issues to business outcomes
4. Be proactive about suggesting maintenance, security checks, and opportunities

When asked about device information (storage, GPU, memory, network, etc),
ALWAYS use the get_device_info tool with the appropriate query type.

Valid query types:
- storage (for disk information)
- gpu (for graphics card details)
- memory (for RAM information)
- network (for network interfaces)
- system (for CPU and system information)
- health (for health score and status information)

When asking about health scores, status, or current metrics, always use force_refresh=True to get the most current data.
""")
    ])

    llm = AzureChatOpenAI(
        openai_api_key=current_app.config['AZURE_OPENAI_API_KEY'],
        azure_endpoint=current_app.config['AZURE_OPENAI_ENDPOINT'],
        azure_deployment="wegweiser",
        openai_api_version=current_app.config['AZURE_OPENAI_API_VERSION'],
    )

    tools = []
    tool_names = []

    if (entity_type == 'device' and knowledge_graph):
        # Use the existing KnowledgeGraph instance
        device_info_tool = StructuredTool.from_function(
            func=knowledge_graph.query,
            name="get_device_info",
            description="Get device information. Input should be what type of information you want (storage, gpu, memory, network, system)"
        )
        tools.append(device_info_tool)
        tool_names.append(device_info_tool.name)

    # Create chain
    chain = (
        {
            "input": lambda x: x["input"],
            "entity_type": lambda _: entity_type,
            "entity_profile": lambda _: tenant_profile,
            "context": lambda _: entity_context,
            "user_context": lambda _: user_context,
            "long_term_context": lambda x: memory.load_memory_variables(x)["long_term_context"],
            "recent_history": lambda _: recent_history,
            "conversation_topics": lambda _: conversation_topics,
            "msp_context": lambda x: memory.load_memory_variables(x).get("msp_context", {}),
            "history": lambda x: memory.chat_memory_messages(),
            "tools": lambda _: tools,
            "tool_names": lambda _: tool_names,
        }
        | prompt
        | llm
    )

    # Wrap with message history
    chain_with_history = RunnableWithMessageHistory(
        chain,
        lambda session_id: memory,
        input_messages_key="input",
        history_messages_key="history"
    )

    return chain_with_history

def get_tenant_uuid_for_entity(entity_uuid, entity_type):
    if entity_type == 'tenant':
        return entity_uuid
    elif entity_type == 'organisation':
        org = Organisations.query.get(entity_uuid)
        return org.tenantuuid if org else None
    elif entity_type == 'group':
        group = Groups.query.get(entity_uuid)
        return group.tenantuuid if group else None
    elif entity_type == 'device':
        device = Devices.query.get(entity_uuid)
        return device.tenantuuid if device else None
    return None

def _parse_thoughts_and_actions(ai_text: str):
    lines = ai_text.splitlines()
    thoughts = []
    result_lines = []
    capturing = False

    for line in lines:
        if line.strip().lower().startswith("thought:"):
            thoughts.append(line)
            capturing = True
        elif line.strip().lower().startswith("answer:"):
            capturing = False
            result_lines.append(line)
        elif capturing or line.strip().lower().startswith(("action:", "observation:")):
            thoughts.append(line)
        else:
            result_lines.append(line)

    return "\n".join(thoughts), "\n".join(result_lines)

def get_ai_response(conversation, user_input, session_id):
    """Get AI response with token tracking"""
    try:
        # Get response from conversation chain
        # Convert the string input to a dictionary with 'input' key
        # as required by RunnablePassthrough.assign()
        response = conversation.invoke(
            {"input": user_input},  # Wrap user_input in a dictionary
            config={
                'configurable': {
                    'session_id': session_id
                }
            }
        )

        # Attempt to extract token usage from different model providers
        token_usage = 0
        if hasattr(response, 'token_usage'):
            token_usage = sum(response.token_usage.values()) if isinstance(response.token_usage, dict) else response.token_usage

        # Add token usage to response if not present
        if not hasattr(response, 'token_usage'):
            # Estimate tokens based on message length
            # This is a fallback method, not very accurate
            estimated_tokens = len(user_input.split()) + len(response.content.split())
            response.token_usage = estimated_tokens

        return response
    except Exception as e:
        # Log error and return basic response
        logging.error(f"Error in get_ai_response for {session_id}: {str(e)}")
        class SimpleResponse:
            def __init__(self, text):
                self.content = text
                self.token_usage = 0

        return SimpleResponse(f"I encountered an issue processing your request. Please try again or rephrase your question.")

def adapt_response_style(response, communication_style):
    """Adapt response based on preferred communication style"""
    response = response.replace("Best regards,", "").replace("[Your AI Assistant]", "").strip()

    if not communication_style or communication_style == 'standard':
        return response

    if communication_style == 'formal':
        # More formal language
        response = response.replace("you're", "you are").replace("don't", "do not")
        response = response.replace("can't", "cannot").replace("won't", "will not")
        response = response.replace("let's", "let us").replace("it's", "it is")

        # Remove casual phrases
        casual_phrases = ["just", "basically", "actually", "you know", "like", "pretty", "really"]
        for phrase in casual_phrases:
            response = re.sub(rf'\b{phrase}\b', '', response)

        # Make sure there are no contractions left
        response = re.sub(r'\b(\w+)\'(\w+)\b', r'\1\2', response)

        # Remove multiple exclamation marks
        response = re.sub(r'!+', '.', response)

    elif communication_style == 'casual':
        # More casual, friendly language
        response = response.replace("Hello", "Hi").replace("Goodbye", "Bye")
        response = response.replace("Greetings", "Hey there").replace("Dear", "Hi")

        # Add MSP-friendly casual tone
        response = response.replace("Please note that", "Just FYI,")
        response = response.replace("It is recommended", "I'd recommend")
        response = response.replace("You should consider", "You might want to")

    elif communication_style == 'technical':
        # More technical, precise language
        response = response.replace("problem", "issue").replace("fix", "resolve")
        response = response.replace("check", "verify").replace("use", "utilize")

        # Make sure technical terms are used consistently
        response = response.replace("computer", "system").replace("program", "application")
        response = response.replace("internet", "network").replace("speed", "performance")

    elif communication_style == 'simplified':
        # Simpler language, shorter sentences
        response = re.sub(r'(\. )([A-Z])', r'.\n\n\2', response)  # Add paragraph breaks
        response = re.sub(r',\s*(\w+\s+){5,}', '.\n', response)  # Break long sentences

        # Replace complex terms
        response = response.replace("utilize", "use").replace("implementation", "setup")
        response = response.replace("configuration", "setup").replace("infrastructure", "systems")
        response = response.replace("initiate", "start").replace("terminate", "end")

    # Remove repeated spaces
    response = re.sub(r' +', ' ', response)

    return response.strip()

def generate_health_score_analysis(entity_type, entity_uuid):
    """Generate health score analysis with MSP-specific insights"""
    llm = AzureChatOpenAI(
        openai_api_key=current_app.config['AZURE_OPENAI_API_KEY'],
        azure_endpoint=current_app.config['AZURE_OPENAI_ENDPOINT'],
        azure_deployment="wegweiser",
        openai_api_version=current_app.config['AZURE_OPENAI_API_VERSION'],
    )

    if entity_type == 'device':
        entity = Devices.query.get(entity_uuid)
        entity_name = entity.devicename if entity else "Unknown device"

        # Get additional context for better analysis
        device_group = None
        client_name = "Unknown client"
        if entity and entity.groupuuid:
            device_group = Groups.query.get(entity.groupuuid)
            if device_group and device_group.orguuid:
                org = Organisations.query.get(device_group.orguuid)
                if org:
                    client_name = org.orgname

    elif entity_type == 'group':
        entity = Groups.query.get(entity_uuid)
        entity_name = entity.groupname if entity else "Unknown group"

        # Get client name
        client_name = "Unknown client"
        if entity and entity.orguuid:
            org = Organisations.query.get(entity.orguuid)
            if org:
                client_name = org.orgname

        # Count devices in group
        device_count = Devices.query.filter_by(groupuuid=entity_uuid).count() if entity else 0

    elif entity_type == 'organisation':
        entity = Organisations.query.get(entity_uuid)
        entity_name = entity.orgname if entity else "Unknown organisation"
        client_name = entity_name

        # Count groups and devices
        group_count = Groups.query.filter_by(orguuid=entity_uuid).count() if entity else 0
        group_uuids = [g.groupuuid for g in Groups.query.filter_by(orguuid=entity_uuid).all()] if entity else []
        device_count = Devices.query.filter(Devices.groupuuid.in_(group_uuids)).count() if group_uuids else 0

    elif entity_type == 'tenant':
        entity = Tenants.query.get(entity_uuid)
        entity_name = entity.tenantname if entity else "Unknown tenant"

        # Count clients and devices
        org_count = Organisations.query.filter_by(tenantuuid=entity_uuid).count() if entity else 0
        device_count = Devices.query.filter_by(tenantuuid=entity_uuid).count() if entity else 0
    else:
        return "Invalid entity type"

    if not entity:
        return "Entity not found"

    # Create MSP-focused prompt for health score analysis
    prompt = f"""
    As an MSP analyst, analyze the health score for the following {entity_type}:

    Name: {entity_name}
    Type: {entity_type}
    Health Score: {entity.health_score}

    {"Client: " + client_name if entity_type != 'tenant' else ""}
    {"Number of devices: " + str(device_count) if entity_type in ['group', 'organisation'] else ""}
    {"Number of clients: " + str(org_count) if entity_type == 'tenant' else ""}

    Provide a detailed MSP-focused analysis including:

    ## Health Score Assessment
    [Provide a clear assessment of the current score and its business implications]

    ## Technical Findings
    [Outline the technical issues that are likely affecting the score]

    ## Business Impact
    [Explain how these issues affect the client's operations and productivity]

    ## Recommended Actions
    [Prioritized list of actions to improve the score, with timeframes]

    ## SLA Considerations
    [How this affects any SLAs and what should be communicated to the client]

    ## Resource Planning
    [Staff and time resources needed to address the issues]

    Format your response as a professional MSP internal report with clear sections and prioritized recommendations.
    """

    response = llm.invoke(prompt)
    return response.content

def generate_entity_suggestions(entity_type, entity_uuid):
    """Generate MSP-focused entity suggestions"""
    llm = AzureChatOpenAI(
        openai_api_key=current_app.config['AZURE_OPENAI_API_KEY'],
        azure_endpoint=current_app.config['AZURE_OPENAI_ENDPOINT'],
        azure_deployment="wegweiser",
        openai_api_version=current_app.config['AZURE_OPENAI_API_VERSION'],
    )

    if entity_type == 'group':
        entity = Groups.query.get(entity_uuid)
        entity_name = entity.groupname if entity else "Unknown group"
        devices = Devices.query.filter_by(groupuuid=entity_uuid).all() if entity else []
    elif entity_type == 'organisation':
        entity = Organisations.query.get(entity_uuid)
        entity_name = entity.orgname if entity else "Unknown organisation"
        groups = Groups.query.filter_by(orguuid=entity_uuid).all() if entity else []
        group_uuids = [g.groupuuid for g in groups]
        devices = Devices.query.filter(Devices.groupuuid.in_(group_uuids)).all() if group_uuids else []
    elif entity_type == 'tenant':
        entity = Tenants.query.get(entity_uuid)
        entity_name = entity.tenantname if entity else "Unknown tenant"
        devices = Devices.query.filter_by(tenantuuid=entity_uuid).all() if entity else []
    else:
        return "Invalid entity type"

    if not entity:
        return "Entity not found"

    # Get device health summary
    healthy_devices = sum(1 for d in devices if d.health_score and d.health_score >= 85)
    warning_devices = sum(1 for d in devices if d.health_score and 70 <= d.health_score < 85)
    at_risk_devices = sum(1 for d in devices if d.health_score and 50 <= d.health_score < 70)
    critical_devices = sum(1 for d in devices if d.health_score and d.health_score < 50)

    device_info = [f"Device: {d.devicename}, Health Score: {d.health_score}" for d in devices[:10]]  # Limit to 10

    # Create a more MSP-focused prompt
    prompt = f"""
    # MSP Strategic Analysis for {entity_name}

    ## Entity Overview
    - Type: {entity_type.title()}
    - Name: {entity_name}
    - Health Score: {entity.health_score}
    - Total Devices: {len(devices)}

    ## Device Health Distribution
    - Healthy devices (85-100): {healthy_devices}
    - Warning devices (70-84): {warning_devices}
    - At-risk devices (50-69): {at_risk_devices}
    - Critical devices (0-49): {critical_devices}

    ## Sample Devices
    {' '.join(device_info)}

    As an MSP consultant, create a comprehensive analysis with the following sections:

    ## Executive Summary
    [Brief overview of status and key recommendations for MSP management]

    ## Technical Assessment
    [Objective analysis of current state with focus on risks and opportunities]

    ## Client Impact Analysis
    [How current technical status affects client operations and satisfaction]

    ## Action Plan
    ### Immediate Actions (Next 24-48 hours)
    [Critical issues requiring immediate attention]

    ### Short-term Projects (1-2 weeks)
    [Important issues to address soon]

    ### Strategic Initiatives (1-3 months)
    [Longer-term improvements]

    ## Resource Requirements
    [Staff time, skills, and tools needed]

    ## Revenue Opportunities
    [Potential upsell and service expansion opportunities]

    ## Client Communication Strategy
    [How to discuss these findings with the client]

    Your analysis should be pragmatic, focused on both technical excellence and business outcomes, with clear prioritization of efforts. Format in clean markdown with appropriate headings.
    """

    response = llm.invoke(prompt)
    return response.content

def generate_tool_recommendations(tenant_uuid):
    """Generate MSP tool recommendations"""
    llm = AzureChatOpenAI(
        openai_api_key=current_app.config['AZURE_OPENAI_API_KEY'],
        azure_endpoint=current_app.config['AZURE_OPENAI_ENDPOINT'],
        azure_deployment="wegweiser",
        openai_api_version=current_app.config['AZURE_OPENAI_API_VERSION'],
    )

    tenant = Tenants.query.get(tenant_uuid)
    if not tenant:
        return "Tenant not found"

    profile_data = tenant.profile_data or {}

    # Identify missing and existing tools
    missing_tools = []
    existing_tools = []

    for tool, value in profile_data.items():
        if value == 'none':
            missing_tools.append(tool)
        else:
            existing_tools.append(f"{tool}: {value}")

    if not missing_tools:
        return "All tools are already in use."

    # Get client and device counts for context
    org_count = Organisations.query.filter_by(tenantuuid=tenant_uuid).count()
    device_count = Devices.query.filter_by(tenantuuid=tenant_uuid).count()

    tenant_info = f"""
    # MSP Profile
    - Tenant Name: {tenant.tenantname}
    - Company Size: {tenant.company_size or "Unknown"}
    - Industry Focus: {tenant.industry or "General IT Services"}
    - Primary Service Area: {tenant.primary_focus or "Technology Support"}
    - Clients: {org_count}
    - Managed Devices: {device_count}

    # Current Tool Stack
    {chr(10).join(existing_tools) if existing_tools else "No tools currently configured"}

    # Missing Tool Categories
    {chr(10).join(missing_tools) if missing_tools else "All tool categories filled"}
    """

    prompt = f"""
    You are an MSP technology consultant specializing in tool selection and integration. Based on the following MSP profile, provide recommendations for their technology stack:

    {tenant_info}

    Create a detailed MSP technology roadmap with these sections:

    ## Tool Stack Assessment
    [Analysis of current tool stack, strengths, and gaps]

    ## Critical Gaps and Business Impact
    [Analysis of how missing tools are affecting operations and profitability]

    ## Recommendations by Category

    For each missing tool category, provide:

    ### [Category Name]

    **Business Case:**
    [How this technology improves operations and profitability]

    **Recommended Solutions:**
    - **Enterprise Option:** [Name, key features, typical pricing model]
    - **Mid-Market Option:** [Name, key features, typical pricing model]
    - **Budget-Friendly Option:** [Name, key features, typical pricing model]

    **Integration Considerations:**
    [How this integrates with existing tools]

    **Implementation Timeline:**
    [Typical implementation effort and timeline]

    **ROI Expectations:**
    [Typical ROI and payback period]

    ## Implementation Roadmap
    [Prioritized order for implementing these tools with timeline]

    ## Competitive Advantage
    [How these improvements position the MSP competitively]

    Make recommendations practical, with a focus on operational efficiency, technician productivity, and client service quality. Include approximate pricing models where possible.
    """

    response = llm.invoke(prompt)
    recommendations = response.content

    # Save the recommendations in the TenantMetadata table
    try:
        new_metadata = TenantMetadata(
            tenantuuid=tenant_uuid,
            metalogos_type='ai_recommendations',
            metalogos={'recommendations': recommendations},
            processing_status='processed'
        )
        db.session.add(new_metadata)
        db.session.commit()
    except Exception as e:
        log_with_route(logging.ERROR, f"Error saving tool recommendations: {str(e)}")
        db.session.rollback()

    # Return the recommendations for display
    return recommendations

class MSPConversationAnalyzer:
    """Analyzes conversations to identify business opportunities and trends"""

    @staticmethod
    def extract_insights(tenant_uuid: str, days: int = 30) -> Dict[str, Any]:
        """Extract business insights from recent conversations"""
        insights = {
            "common_issues": [],
            "trending_topics": {},
            "client_satisfaction": {},
            "knowledge_gaps": [],
            "upsell_opportunities": []
        }

        try:
            # Get recent messages across all conversations for this tenant
            cutoff_time = int(time.time()) - (days * 86400)  # Convert days to seconds

            recent_messages = Messages.query.join(
                Conversations, Messages.conversationuuid == Conversations.conversationuuid
            ).filter(
                Conversations.tenantuuid == tenant_uuid,
                Messages.created_at > cutoff_time
            ).order_by(Messages.created_at.desc()).all()

            if not recent_messages:
                return insights

            # Extract text for analysis
            all_text = " ".join([msg.content for msg in recent_messages if not msg.useruuid])

            # Find common technical issues
            issue_patterns = [
                r"error|issue|problem|failure|crash|bug",
                r"slow|performance|speed|lag",
                r"security|breach|vulnerability|attack|malware|virus",
                r"backup|restore|recovery",
                r"network|connection|internet|wifi",
                r"login|password|access|authentication",
                r"update|patch|upgrade|version",
                r"printer|printing|scan"
            ]

            for pattern in issue_patterns:
                matches = re.findall(pattern, all_text, re.IGNORECASE)
                if matches:
                    issue_type = pattern.split("|")[0]
                    insights["common_issues"].append({
                        "type": issue_type,
                        "count": len(matches),
                        "examples": matches[:5]  # Limit to 5 examples
                    })

            # Sort by count
            insights["common_issues"].sort(key=lambda x: x["count"], reverse=True)

            # Identify trending topics (increasing frequency over time)
            # Group messages by week
            weeks = {}
            for msg in recent_messages:
                # Convert timestamp to week number
                week = (msg.created_at - cutoff_time) // (7 * 86400)
                if week not in weeks:
                    weeks[week] = []
                weeks[week].append(msg.content)

            # Check frequency of key topics by week
            topics = ["security", "compliance", "cloud", "backup", "remote", "mobile", "license"]

            for topic in topics:
                topic_trend = []
                for week, messages in sorted(weeks.items()):
                    week_text = " ".join(messages)
                    count = len(re.findall(r'\b' + topic + r'\b', week_text, re.IGNORECASE))
                    topic_trend.append({"week": week, "count": count})

                # Check if topic is trending up
                if len(topic_trend) >= 2:
                    is_trending = topic_trend[-1]["count"] > topic_trend[0]["count"]
                    if is_trending:
                        insights["trending_topics"][topic] = topic_trend

            # Identify upsell opportunities from conversations
            upsell_patterns = [
                r"need\s+(?:better|improved|more)\s+(backup|security|monitoring|support)",
                r"(interested|looking)\s+(?:in|at|for)\s+(cloud|migration|upgrade)",
                r"problem\s+with\s+(current|existing)\s+(provider|service|vendor)",
                r"(considering|evaluating)\s+(change|switch|upgrade)"
            ]

            for pattern in upsell_patterns:
                matches = re.findall(pattern, all_text, re.IGNORECASE)
                for match in matches:
                    if isinstance(match, tuple):
                        opportunity = match[1]
                    else:
                        opportunity = match

                    if opportunity not in [o["opportunity"] for o in insights["upsell_opportunities"]]:
                        insights["upsell_opportunities"].append({
                            "opportunity": opportunity,
                            "context": re.findall(r'[^.!?]*' + re.escape(opportunity) + r'[^.!?]*', all_text, re.IGNORECASE)[:3]
                        })

        except Exception as e:
            log_with_route(logging.ERROR, f"Error in conversation analysis: {str(e)}")

        return insights