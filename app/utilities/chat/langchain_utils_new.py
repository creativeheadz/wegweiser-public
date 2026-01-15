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

class MSPConversationGuide:
    """Guides conversations toward MSP-relevant topics"""

    @staticmethod
    def get_topic_suggestions(entity_type: str, entity_context: dict) -> List[Dict]:
        """Get conversation topic suggestions based on entity type and context"""
        suggestions = []

        # Device-specific topics
        if entity_type == 'device':
            health_score = entity_context.get('health_score', 100)

            if health_score < 70:
                suggestions.append({
                    'topic': 'performance_optimization',
                    'prompt': "I notice this device has performance issues. Would you like me to suggest optimization steps?",
                    'priority': 'high'
                })

            if 'security' in entity_context.get('recent_events', []):
                suggestions.append({
                    'topic': 'security_remediation',
                    'prompt': "There appear to be security events on this device. Should we investigate further?",
                    'priority': 'critical'
                })

            if entity_context.get('storage_usage', 0) > 85:
                suggestions.append({
                    'topic': 'storage_management',
                    'prompt': "Storage is running low. Would you like suggestions for freeing up space?",
                    'priority': 'medium'
                })

        # Group-specific topics
        elif entity_type == 'group':
            if entity_context.get('inactive_devices', 0) > 0:
                suggestions.append({
                    'topic': 'device_management',
                    'prompt': f"There are {entity_context.get('inactive_devices')} inactive devices in this group. Would you like to review them?",
                    'priority': 'medium'
                })

            if entity_context.get('avg_health_score', 100) < 80:
                suggestions.append({
                    'topic': 'group_health',
                    'prompt': "This group's average health score is below optimal. Would you like an analysis?",
                    'priority': 'high'
                })

        # Organisation-specific topics
        elif entity_type == 'organisation':
            if 'compliance' not in entity_context.get('recent_checks', []):
                suggestions.append({
                    'topic': 'compliance_check',
                    'prompt': "Would you like me to run a compliance assessment for this organization?",
                    'priority': 'medium'
                })

            if entity_context.get('security_risks', []):
                suggestions.append({
                    'topic': 'security_posture',
                    'prompt': "I've identified potential security risks. Would you like a security posture review?",
                    'priority': 'high'
                })

        # Tenant-specific topics
        elif entity_type == 'tenant':
            if entity_context.get('resource_utilization', 0) > 85:
                suggestions.append({
                    'topic': 'resource_planning',
                    'prompt': "Your resource utilization is high. Would you like help with capacity planning?",
                    'priority': 'medium'
                })

            if entity_context.get('clients_requiring_reporting', []):
                suggestions.append({
                    'topic': 'client_reporting',
                    'prompt': f"You have {len(entity_context.get('clients_requiring_reporting', []))} clients due for reports. Would you like me to help prepare them?",
                    'priority': 'high'
                })

            if entity_context.get('tool_gaps', []):
                suggestions.append({
                    'topic': 'tool_recommendations',
                    'prompt': "I've identified some gaps in your tool stack. Would you like recommendations?",
                    'priority': 'low'
                })

        # Add a few general MSP topics that are always relevant
        suggestions.append({
            'topic': 'cost_optimization',
            'prompt': "Would you like suggestions for optimizing your operational costs?",
            'priority': 'medium'
        })

        suggestions.append({
            'topic': 'knowledge_transfer',
            'prompt': "Would you like help documenting processes for your team?",
            'priority': 'low'
        })

        # Sort by priority
        priority_weights = {'critical': 0, 'high': 1, 'medium': 2, 'low': 3}
        suggestions.sort(key=lambda x: priority_weights.get(x['priority'], 4))

        return suggestions

    @staticmethod
    def generate_follow_up_questions(topic: str, entity_type: str) -> List[str]:
        """Generate follow-up questions for specific MSP topics"""
        question_map = {
            'performance_optimization': [
                "What performance benchmarks do you have for this device?",
                "Are there specific applications causing issues?",
                "Would you like me to recommend hardware upgrades?"
            ],
            'security_remediation': [
                "Have you implemented multi-factor authentication?",
                "Would you like me to check for common vulnerabilities?",
                "Do you need help with security policy enforcement?"
            ],
            'resource_planning': [
                "What are your growth projections for the next quarter?",
                "Are there seasonal patterns in your resource needs?",
                "Would you like me to analyze historical usage patterns?"
            ],
            'cost_optimization': [
                "Which area of your operations has the highest costs?",
                "Would you like to review your licensing efficiency?",
                "Have you considered automating any manual processes?"
            ],
            'compliance_check': [
                "Which compliance standards are most important for your clients?",
                "Would you like a gap analysis against specific frameworks?",
                "Do you need documentation to satisfy audit requirements?"
            ]
        }

        # Get default questions for the topic or use generic ones
        questions = question_map.get(topic, [
            "Would you like more details about this?",
            "Is there a specific aspect you'd like to focus on?",
            "Would you like actionable recommendations?"
        ])

        # Add entity-specific questions
        if entity_type == 'device':
            questions.append("Would you like to compare this device with others in the same group?")
        elif entity_type == 'group':
            questions.append("Would you like to see how this group compares to others in the organization?")
        elif entity_type == 'organisation':
            questions.append("Would you like a summary report for the entire organization?")
        elif entity_type == 'tenant':
            questions.append("Would you like to review your client-specific performance metrics?")

        return questions

class CustomMemory(BaseModel):
    entity_uuid: str = Field(description="UUID of the entity")
    entity_type: str = Field(description="Type of entity")
    tenant_uuid: str = Field(description="UUID of the tenant")
    k: int = Field(default=MEMORY_WINDOW_SIZE, description="Window size for memory")
    messages: List[BaseMessage] = Field(default_factory=list)
    return_messages: bool = Field(default=True)
    conversation_uuid: Optional[str] = Field(default=None)
    last_user_message: Optional[str] = Field(default=None)
    last_ai_message: Optional[str] = Field(default=None)
    conversation: Optional[Any] = Field(default=None)
    llm: Optional[Any] = Field(default=None, description="Language model instance")
    tokenizer: Optional[Any] = Field(default=None, description="Tokenizer instance")
    conversation_topics: List[str] = Field(default_factory=list, description="List of conversation topics")
    msp_customer_context: Dict[str, Any] = Field(default_factory=dict, description="MSP customer context")

    def __init__(self, entity_uuid: str, entity_type: str, tenant_uuid: str | UUID, k: int = MEMORY_WINDOW_SIZE):
        # Initialize with required fields first
        super().__init__(
            entity_uuid=str(entity_uuid),
            entity_type=entity_type,
            tenant_uuid=str(tenant_uuid),
            k=k
        )

        # Set up LLM and tokenizer after parent initialization
        self._setup_llm_and_tokenizer()

        # Add conversation tracking
        self._setup_conversation()

        # Add MSP-specific fields
        self._initialize_msp_context()

    def _initialize_msp_context(self):
        """Initialize MSP-specific context"""
        # Get tenant info for MSP context
        tenant = Tenants.query.get(self.tenant_uuid)
        if not tenant:
            return

        # Get customer info if we're dealing with a customer-specific entity
        customer_context = {}
        if self.entity_type in ['organisation', 'group', 'device']:
            if self.entity_type == 'organisation':
                org = Organisations.query.get(self.entity_uuid)
                if org:
                    customer_context['name'] = org.orgname
                    customer_context['type'] = 'organisation'
                    # Get SLA info if available
                    customer_context['sla'] = tenant.get_customer_sla(org.orguuid)
            elif self.entity_type == 'group':
                group = Groups.query.get(self.entity_uuid)
                if group:
                    customer_context['name'] = group.groupname
                    customer_context['type'] = 'group'
                    # Get org for this group
                    org = Organisations.query.get(group.orguuid)
                    if org:
                        customer_context['organisation'] = org.orgname
                        customer_context['sla'] = tenant.get_customer_sla(org.orguuid)
            elif self.entity_type == 'device':
                device = Devices.query.get(self.entity_uuid)
                if device:
                    customer_context['name'] = device.devicename
                    customer_context['type'] = 'device'
                    # Get group and org for this device
                    group = Groups.query.get(device.groupuuid)
                    if group:
                        customer_context['group'] = group.groupname
                        org = Organisations.query.get(group.orguuid)
                        if org:
                            customer_context['organisation'] = org.orgname
                            customer_context['sla'] = tenant.get_customer_sla(org.orguuid)

        self.msp_customer_context = customer_context

        # Initialize conversation topics list
        self.conversation_topics = []

    def _setup_llm_and_tokenizer(self):
        """Initialize LLM and tokenizer"""
        self.llm = AzureChatOpenAI(
            openai_api_key=current_app.config['AZURE_OPENAI_API_KEY'],
            azure_endpoint=current_app.config['AZURE_OPENAI_ENDPOINT'],
            azure_deployment="wegweiser",
            openai_api_version=current_app.config['AZURE_OPENAI_API_VERSION'],
        )
        self.tokenizer = tiktoken.get_encoding("cl100k_base")

    def _setup_conversation(self):
        """Initialize conversation tracking"""
        self.conversation = Conversations.get_or_create_conversation(
            self.tenant_uuid, self.entity_uuid, self.entity_type
        )
        self.conversation_uuid = str(self.conversation.conversationuuid)

    @property
    def memory_variables(self) -> List[str]:
        """Return the memory variables."""
        return ["chat_history", "history", "long_term_context", "msp_context"]

    def load_memory_variables(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        # Load recent messages from database
        recent_messages = Messages.query.filter_by(
            conversationuuid=self.conversation_uuid
        ).order_by(Messages.created_at.desc()).limit(self.k * 2).all()

        # Convert to LangChain message format
        messages = []
        for msg in reversed(recent_messages):
            if msg.useruuid:
                messages.append(HumanMessage(content=msg.content))
            else:
                messages.append(AIMessage(content=msg.content))

        self.messages = messages

        # Extract conversation topics if they exist
        self._extract_conversation_topics()

        # Get MSP-specific context
        msp_context = self._get_msp_context()

        return {
            "chat_history": self.messages,
            "history": self.messages,  # For backward compatibility
            "long_term_context": self._load_long_term_memories(),
            "msp_context": msp_context
        }

    def _extract_conversation_topics(self):
        """Extract conversation topics from message history"""
        if not self.messages:
            return

        # Extract major topics from the last few messages
        all_text = " ".join([msg.content for msg in self.messages[-6:]])

        # Check for common MSP topics
        topic_keywords = {
            "performance": ["slow", "speed", "performance", "optimization", "cpu", "memory", "utilization"],
            "security": ["security", "breach", "virus", "malware", "attack", "protect", "firewall", "vulnerability"],
            "compliance": ["compliance", "regulation", "audit", "gdpr", "hipaa", "pci", "iso"],
            "cost": ["cost", "budget", "expense", "saving", "license", "subscription", "pricing"],
            "reporting": ["report", "metrics", "dashboard", "analytics", "visibility", "track", "monitor"],
            "planning": ["planning", "forecast", "roadmap", "strategy", "capacity", "growth", "resource"]
        }

        detected_topics = []
        for topic, keywords in topic_keywords.items():
            if any(keyword in all_text.lower() for keyword in keywords):
                detected_topics.append(topic)

        self.conversation_topics = detected_topics

    def _get_msp_context(self) -> Dict[str, Any]:
        """Get MSP-specific context for the conversation"""
        context = {
            "entity_type": self.entity_type,
            "conversation_topics": self.conversation_topics,
            "customer_context": self.msp_customer_context
        }

        # Add relevant MSP tools based on the conversation topics
        if self.conversation_topics:
            context["relevant_tools"] = self._get_relevant_msp_tools()

        # Add business impact info if we're discussing problems
        if any(topic in self.conversation_topics for topic in ["performance", "security"]):
            context["business_impact"] = self._assess_business_impact()

        # Add compliance info if relevant
        if "compliance" in self.conversation_topics:
            context["compliance_info"] = self._get_compliance_context()

        return context

    def _get_relevant_msp_tools(self) -> List[Dict[str, str]]:
        """Get relevant MSP tools based on conversation topics"""
        tools = []

        tenant = Tenants.query.get(self.tenant_uuid)
        if not tenant:
            return tools

        tenant_profile = tenant.profile_data or {}

        # Map conversation topics to tool categories
        topic_to_tool_map = {
            "performance": ["rmm_type", "network_monitoring"],
            "security": ["endpoint_protection", "dns_filtering", "email_security", "security_suites"],
            "compliance": ["compliance_management", "documentation"],
            "cost": ["psa_service_desk", "license_management"],
            "reporting": ["it_documentation", "psa_service_desk"],
            "planning": ["resource_planning", "business_management"]
        }

        # Add relevant tools
        for topic in self.conversation_topics:
            tool_categories = topic_to_tool_map.get(topic, [])
            for category in tool_categories:
                if category in tenant_profile and tenant_profile[category] != "none":
                    tools.append({
                        "category": category,
                        "tool": tenant_profile[category],
                        "relevant_to": topic
                    })

        return tools

    def _assess_business_impact(self) -> Dict[str, Any]:
        """Assess business impact of issues being discussed"""
        impact = {
            "severity": "Unknown",
            "client_impact": "Unknown",
            "recommended_priority": "Unknown"
        }

        if not self.entity_uuid:
            return impact

        # Different logic based on entity type
        if self.entity_type == "device":
            device = Devices.query.get(self.entity_uuid)
            if not device:
                return impact

            # Check health score
            if device.health_score is not None:
                if device.health_score < 50:
                    impact["severity"] = "Critical"
                    impact["recommended_priority"] = "Immediate action required"
                elif device.health_score < 70:
                    impact["severity"] = "High"
                    impact["recommended_priority"] = "Address within 24 hours"
                elif device.health_score < 85:
                    impact["severity"] = "Medium"
                    impact["recommended_priority"] = "Schedule remediation"
                else:
                    impact["severity"] = "Low"
                    impact["recommended_priority"] = "Monitor"

            # Check for security issues in metadata
            security_metadata = DeviceMetadata.query.filter_by(
                deviceuuid=self.entity_uuid,
                metalogos_type='eventsFiltered-Security'
            ).order_by(DeviceMetadata.created_at.desc()).first()

            if security_metadata and security_metadata.ai_analysis:
                if "critical" in security_metadata.ai_analysis.lower():
                    impact["severity"] = "Critical"
                    impact["client_impact"] = "Potential security breach in progress"
                    impact["recommended_priority"] = "Immediate action required"

            # Assess client impact based on context
            if self.msp_customer_context.get("sla"):
                sla_info = self.msp_customer_context.get("sla", {})
                impact["client_impact"] = f"Client has {sla_info.get('type', 'unknown')} SLA with response time of {sla_info.get('response_time', 'unknown')}"

        elif self.entity_type in ["group", "organisation"]:
            # For groups/orgs, assess impact based on number of affected devices
            if self.entity_type == "group":
                devices = Devices.query.filter_by(groupuuid=self.entity_uuid).all()
                entity = Groups.query.get(self.entity_uuid)
            else:
                # For organization, get all devices across all groups
                groups = Groups.query.filter_by(orguuid=self.entity_uuid).all()
                group_ids = [group.groupuuid for group in groups]
                devices = Devices.query.filter(Devices.groupuuid.in_(group_ids)).all()
                entity = Organisations.query.get(self.entity_uuid)

            if not devices:
                return impact

            # Count devices with health issues
            critical_devices = sum(1 for d in devices if d.health_score is not None and d.health_score < 50)
            high_risk_devices = sum(1 for d in devices if d.health_score is not None and 50 <= d.health_score < 70)

            if critical_devices > 0:
                impact["severity"] = "Critical"
                impact["client_impact"] = f"{critical_devices} critical devices affected"
                impact["recommended_priority"] = "Immediate action required"
            elif high_risk_devices > len(devices) * 0.25:  # More than 25% of devices
                impact["severity"] = "High"
                impact["client_impact"] = f"{high_risk_devices} high-risk devices affected"
                impact["recommended_priority"] = "Address within 24 hours"
            else:
                impact["severity"] = "Medium"
                impact["client_impact"] = "Limited impact to client operations"
                impact["recommended_priority"] = "Schedule remediation"

        return impact

    def _get_compliance_context(self) -> Dict[str, Any]:
        """Get compliance context for conversation"""
        compliance_info = {
            "standards": DEFAULT_COMPLIANCE_STANDARDS,
            "recent_checks": [],
            "issues": []
        }

        # Get tenant compliance preferences
        tenant = Tenants.query.get(self.tenant_uuid)
        if tenant and tenant.compliance_standards:
            compliance_info["standards"] = tenant.compliance_standards

        # For device-level compliance
        if self.entity_type == "device":
            device = Devices.query.get(self.entity_uuid)
            if not device:
                return compliance_info

            # Check for compliance-related metadata
            compliance_metadata = DeviceMetadata.query.filter_by(
                deviceuuid=self.entity_uuid,
                metalogos_type='compliance'
            ).order_by(DeviceMetadata.created_at.desc()).first()

            if compliance_metadata:
                compliance_info["recent_checks"].append({
                    "date": datetime.fromtimestamp(compliance_metadata.created_at).strftime("%Y-%m-%d"),
                    "score": compliance_metadata.score,
                    "issues": compliance_metadata.metalogos.get("issues", []) if isinstance(compliance_metadata.metalogos, dict) else []
                })

            # Basic compliance checks based on device metadata
            security_metadata = DeviceMetadata.query.filter_by(
                deviceuuid=self.entity_uuid,
                metalogos_type='eventsFiltered-Security'
            ).order_by(DeviceMetadata.created_at.desc()).first()

            if security_metadata:
                # Check for common compliance issues in security logs
                if security_metadata.ai_analysis:
                    if "password" in security_metadata.ai_analysis.lower():
                        compliance_info["issues"].append("Password policy violations may affect compliance")
                    if "firewall" in security_metadata.ai_analysis.lower():
                        compliance_info["issues"].append("Firewall configuration issues detected")
                    if "access" in security_metadata.ai_analysis.lower():
                        compliance_info["issues"].append("Unusual access patterns detected")

        return compliance_info

    def save_context(self, inputs: Dict[str, Any], outputs: Dict[str, str]) -> None:
        # Add messages to memory list
        if inputs.get('input'):
            self.messages.append(HumanMessage(content=inputs['input']))
            self.last_user_message = inputs['input']

        if outputs.get('output'):
            self.messages.append(AIMessage(content=outputs['output']))
            self.last_ai_message = outputs['output']

        # Trim to window size
        if len(self.messages) > self.k * 2:
            self.messages = self.messages[-self.k * 2:]

        # Update conversation topics
        self._extract_conversation_topics()

        # Save to database
        self._save_long_term_memory(inputs, outputs)

    @property
    def memory_keys(self) -> List[str]:
        """Return memory keys."""
        return self.memory_variables

    def clear(self) -> None:
        self.messages = []
        AIMemory.query.filter_by(entity_uuid=self.entity_uuid, entity_type=self.entity_type).delete()
        db.session.commit()

    def add_messages(self, messages: List[Dict[str, str]]) -> None:
        for message in messages:
            if message['type'] == 'human':
                self.messages.append(HumanMessage(content=message['content']))
            elif message['type'] == 'ai':
                self.messages.append(AIMessage(content=message['content']))

    def _load_long_term_memories(self) -> List[str]:
        memories = AIMemory.query.filter_by(
            entity_uuid=self.entity_uuid,
            entity_type=self.entity_type,
            tenantuuid=self.tenant_uuid
        ).order_by(AIMemory.importance_score.desc(), AIMemory.last_accessed.desc()).limit(5).all()
        return [self._detokenize_memory(memory.content) for memory in memories]

    def _save_long_term_memory(self, inputs: Dict[str, Any], outputs: Dict[str, str]) -> None:
        if not inputs or not outputs:
            recent_messages = self.messages[-2:]
            if len(recent_messages) == 2:
                content = {
                    'user_message': recent_messages[0].content,
                    'ai_message': recent_messages[1].content,
                    'conversation_uuid': self.conversation_uuid,
                    'topics': self.conversation_topics
                }
            else:
                return

        else:
            content = {
                'user_message': inputs.get('input', 'N/A'),
                'ai_message': outputs.get('output', 'N/A'),
                'conversation_uuid': self.conversation_uuid,
                'topics': self.conversation_topics
            }

        condensed_memory = self._condense_memory(content)
        importance_score = self._calculate_importance(condensed_memory)

        if importance_score > 0.7:  # Only save memories with high importance
            tokenized_memory = self._tokenize_memory(condensed_memory)
            new_memory = AIMemory(
                memoryuuid=uuid.uuid4(),
                entity_uuid=self.entity_uuid,
                entity_type=self.entity_type,
                tenantuuid=self.tenant_uuid,
                content=tokenized_memory,
                created_at=int(time.time()),
                last_accessed=int(time.time()),
                importance_score=importance_score,
                memory_type='conversation',  # Add memory type
                topics=','.join(self.conversation_topics) if self.conversation_topics else 'general'  # Add topics
            )
            db.session.add(new_memory)
            db.session.commit()

            self._trickle_up_memory(new_memory)

    def _condense_memory(self, content: Dict[str, Any]) -> str:
        # Create a more MSP-focused memory condensation prompt
        topics_text = ', '.join(content.get('topics', [])) if content.get('topics') else 'general conversation'

        prompt = f"""
        Condense the following MSP support conversation into a brief, informative summary focused on:
        1. Core technical or business issues discussed
        2. Decisions made or actions recommended
        3. Important client information revealed
        4. Follow-up items or pending issues

        Conversation topics: {topics_text}

        User: {content.get('user_message', '')}

        Assistant: {content.get('ai_message', '')}

        Create a concise summary that would be useful for an MSP technician reviewing this case later:
        """
        response = self.llm.invoke(prompt)
        return response.content

    def _tokenize_memory(self, content: str) -> str:
        tokens = self.tokenizer.encode(content)
        # Limit tokens to prevent excessive storage
        if len(tokens) > MAX_TOKENS_PER_MEMORY:
            tokens = tokens[:MAX_TOKENS_PER_MEMORY]
        return json.dumps(tokens)

    def _detokenize_memory(self, tokenized_content: str) -> str:
        tokens = json.loads(tokenized_content)
        return self.tokenizer.decode(tokens)

    def _calculate_importance(self, content: str) -> float:
        # Add MSP-specific important keywords
        msp_keywords = [
            'SLA', 'breach', 'critical', 'urgent', 'compliance', 'audit',
            'security', 'performance', 'outage', 'downtime', 'client',
            'billing', 'license', 'renewal', 'migration', 'project',
            'ransomware', 'attack', 'disaster', 'recovery', 'backup',
            'failed', 'error', 'vulnerable'
        ]

        # Calculate base score from keywords
        keyword_score = sum(keyword.lower() in content.lower() for keyword in msp_keywords) * 0.05

        # Check for common MSP conversation patterns
        pattern_scores = 0.0

        # Check for problem-solution pattern (problem followed by solution)
        if re.search(r'(issue|problem|error|failure|outage|malfunction).*?(fix|solution|resolve|mitigate|repair)', content, re.IGNORECASE):
            pattern_scores += 0.2

        # Check for decision pattern
        if re.search(r'(decide|decision|choose|recommend|approve|implement)', content, re.IGNORECASE):
            pattern_scores += 0.15

       # Check for follow-up pattern
        if re.search(r'(follow.up|next.steps|action.items|schedule|will.be|future)', content, re.IGNORECASE):
            pattern_scores += 0.15

        # Higher importance for client-facing information
        if re.search(r'(client|customer|end.user|business)', content, re.IGNORECASE):
            pattern_scores += 0.1

        # Add together with base importance
        base_importance = 0.2  # Every conversation has some importance
        total_score = min(base_importance + keyword_score + pattern_scores, 1.0)

        return total_score

    def _trickle_up_memory(self, memory: AIMemory):
        """Propagate important memories up the hierarchy with MSP context"""
        try:
            # Add MSP-specific context to memories as they trickle up
            if self.entity_type == 'device':
                device = Devices.query.get(self.entity_uuid)
                if device and memory.importance_score > 0.8:
                    # Add device metadata to provide better context
                    device_context = f"Device: {device.devicename} ({device.agent_platform if hasattr(device, 'agent_platform') else 'Unknown platform'})"

                    # Include health score if available
                    health_context = f", Health score: {device.health_score}" if device.health_score is not None else ""

                    # Get core memory content
                    memory_content = self._detokenize_memory(memory.content)

                    # Create enhanced group memory with MSP context
                    group_memory_content = f"{device_context}{health_context} | {memory_content}"

                    # Condense for group level (remove device-specific details)
                    group_memory_prompt = f"""
                    Convert this device-specific note into a brief group-level observation that would be relevant for MSP management:
                    {group_memory_content}

                    Group-level summary (be brief and focus on business impact):
                    """

                    condensed_content = self.llm.invoke(group_memory_prompt).content

                    # Create new memory at group level
                    group_memory = AIMemory(
                        memoryuuid=uuid.uuid4(),
                        entity_uuid=device.groupuuid,
                        entity_type='group',
                        tenantuuid=self.tenant_uuid,
                        content=self._tokenize_memory(condensed_content),
                        created_at=int(time.time()),
                        last_accessed=int(time.time()),
                        importance_score=memory.importance_score * 0.9,
                        memory_type='trickle_up',
                        topics=memory.topics
                    )
                    db.session.add(group_memory)
                    db.session.commit()

            elif self.entity_type == 'group':
                group = Groups.query.get(self.entity_uuid)
                if group and memory.importance_score > 0.8:
                    # Get device count for context
                    device_count = Devices.query.filter_by(groupuuid=self.entity_uuid).count()

                    # Get core memory content
                    memory_content = self._detokenize_memory(memory.content)

                    # Create enhanced organization memory with MSP context
                    group_context = f"Group: {group.groupname} ({device_count} devices)"
                    org_memory_content = f"{group_context} | {memory_content}"

                    # Condense for organization level
                    org_memory_prompt = f"""
                    Convert this group-specific note into a brief organization-level insight that would be relevant for MSP management:
                    {org_memory_content}

                    Organization-level insight (focus on business impact and client relationship):
                    """

                    condensed_content = self.llm.invoke(org_memory_prompt).content

                    # Create new memory at organization level
                    org_memory = AIMemory(
                        memoryuuid=uuid.uuid4(),
                        entity_uuid=group.orguuid,
                        entity_type='organisation',
                        tenantuuid=self.tenant_uuid,
                        content=self._tokenize_memory(condensed_content),
                        created_at=int(time.time()),
                        last_accessed=int(time.time()),
                        importance_score=memory.importance_score * 0.9,
                        memory_type='trickle_up',
                        topics=memory.topics
                    )
                    db.session.add(org_memory)
                    db.session.commit()

            elif self.entity_type == 'organisation':
                org = Organisations.query.get(self.entity_uuid)
                if org and memory.importance_score > 0.9:
                    # Get core memory content
                    memory_content = self._detokenize_memory(memory.content)

                    # Create enhanced tenant memory with MSP business context
                    org_context = f"Client: {org.orgname}"
                    tenant_memory_content = f"{org_context} | {memory_content}"

                    # Condense for tenant level (business management perspective)
                    tenant_memory_prompt = f"""
                    Convert this client-specific note into a brief MSP business insight:
                    {tenant_memory_content}

                    MSP business insight (focus on trends, opportunities, risks, and business implications):
                    """

                    condensed_content = self.llm.invoke(tenant_memory_prompt).content

                    # Create new memory at tenant level
                    tenant_memory = AIMemory(
                        memoryuuid=uuid.uuid4(),
                        entity_uuid=org.tenantuuid,
                        entity_type='tenant',
                        tenantuuid=self.tenant_uuid,
                        content=self._tokenize_memory(condensed_content),
                        created_at=int(time.time()),
                        last_accessed=int(time.time()),
                        importance_score=memory.importance_score * 0.9,
                        memory_type='trickle_up',
                        topics=memory.topics
                    )
                    db.session.add(tenant_memory)
                    db.session.commit()

        except Exception as e:
            log_with_route(logging.ERROR, f"Error in trickle-up memory: {str(e)}")
            # Don't let memory errors crash the system
            pass

    def chat_memory_messages(self) -> List[BaseMessage]:
        return self.messages

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

class MSPBusinessImpactAnalyzer:
    """Analyze business impact of technical issues for MSPs"""

    @staticmethod
    def analyze_impact(entity_type: str, entity_uuid: str, issue_type: str) -> Dict[str, Any]:
        """Analyze business impact of an issue"""
        impact = {
            "severity": "Medium",
            "client_impact": "May affect some services",
            "revenue_risk": "Low",
            "mitigation_time": "1-2 hours",
            "resources_needed": ["Technician"],
            "sla_implications": "Within standard SLA"
        }

        try:
            # Get entity
            if entity_type == "device":
                entity = Devices.query.get(entity_uuid)
                if not entity:
                    return impact

                # Get device's group and organization
                group = Groups.query.get(entity.groupuuid) if entity.groupuuid else None
                org = Organisations.query.get(group.orguuid) if group else None

                # Analyze based on device metadata
                if issue_type == "security":
                    # Check security events
                    metadata = DeviceMetadata.query.filter_by(
                        deviceuuid=entity_uuid,
                        metalogos_type='eventsFiltered-Security'
                    ).order_by(DeviceMetadata.created_at.desc()).first()

                    if metadata and metadata.score is not None:
                        if metadata.score < 50:
                            impact["severity"] = "Critical"
                            impact["client_impact"] = "Immediate security threat"
                            impact["revenue_risk"] = "High"
                            impact["mitigation_time"] = "ASAP (within hours)"
                            impact["resources_needed"] = ["Senior Security Specialist", "Technician"]
                            impact["sla_implications"] = "Emergency response required"
                        elif metadata.score < 70:
                            impact["severity"] = "High"
                            impact["client_impact"] = "Potential security vulnerability"
                            impact["revenue_risk"] = "Medium"
                            impact["mitigation_time"] = "Today"
                            impact["resources_needed"] = ["Security Specialist"]
                            impact["sla_implications"] = "Priority response"

                elif issue_type == "performance":
                    # Check system events
                    metadata = DeviceMetadata.query.filter_by(
                        deviceuuid=entity_uuid,
                        metalogos_type='eventsFiltered-System'
                    ).order_by(DeviceMetadata.created_at.desc()).first()

                    if metadata and metadata.score is not None:
                        if metadata.score < 50:
                            impact["severity"] = "High"
                            impact["client_impact"] = "Significant performance degradation"
                            impact["revenue_risk"] = "Medium"
                            impact["mitigation_time"] = "4-8 hours"
                            impact["resources_needed"] = ["Systems Engineer", "Technician"]
                            impact["sla_implications"] = "Approaching SLA breach"
                        elif metadata.score < 70:
                            impact["severity"] = "Medium"
                            impact["client_impact"] = "Moderate performance issues"
                            impact["revenue_risk"] = "Low"
                            impact["mitigation_time"] = "24 hours"
                            impact["resources_needed"] = ["Technician"]
                            impact["sla_implications"] = "Within standard SLA"

                # Consider device role - placeholder for future role detection
                # TODO: Implement device role detection based on device characteristics

                # Adjust based on organization SLA if available
                if org:
                    tenant = Tenants.query.get(org.tenantuuid)
                    if tenant:
                        sla_info = tenant.get_customer_sla(org.orguuid)
                        if sla_info and sla_info.get('type') == 'Premium':
                            impact["sla_implications"] = "Premium SLA - requires immediate attention"
                            impact["revenue_risk"] = "High"  # Risk to high-value client relationship

            elif entity_type in ["group", "organisation"]:
                # For group/org level, impact is based on aggregate device issues
                if entity_type == "group":
                    entity = Groups.query.get(entity_uuid)
                    if not entity:
                        return impact
                    devices = Devices.query.filter_by(groupuuid=entity_uuid).all()
                else:
                    entity = Organisations.query.get(entity_uuid)
                    if not entity:
                        return impact
                    groups = Groups.query.filter_by(orguuid=entity_uuid).all()
                    group_ids = [group.groupuuid for group in groups]
                    devices = Devices.query.filter(Devices.groupuuid.in_(group_ids)).all()

                if not devices:
                    return impact

                # Count devices with issues
                issue_count = 0
                critical_issues = 0

                for device in devices:
                    if issue_type == "security":
                        metadata = DeviceMetadata.query.filter_by(
                            deviceuuid=device.deviceuuid,
                            metalogos_type='eventsFiltered-Security'
                        ).order_by(DeviceMetadata.created_at.desc()).first()
                    else:  # performance or general
                        metadata = DeviceMetadata.query.filter_by(
                            deviceuuid=device.deviceuuid,
                            metalogos_type='eventsFiltered-System'
                        ).order_by(DeviceMetadata.created_at.desc()).first()

                    if metadata and metadata.score is not None and metadata.score < 70:
                        issue_count += 1
                        if metadata.score < 50:
                            critical_issues += 1

                # Determine impact based on percentage of affected devices
                total_devices = len(devices)
                if total_devices > 0:
                    affected_percentage = (issue_count / total_devices) * 100
                    critical_percentage = (critical_issues / total_devices) * 100

                    if critical_percentage >= 20 or (critical_issues >= 3 and issue_type == "security"):
                        impact["severity"] = "Critical"
                        impact["client_impact"] = f"Widespread critical issues affecting {critical_percentage:.0f}% of devices"
                        impact["revenue_risk"] = "High"
                        impact["mitigation_time"] = "Immediate response required"
                        impact["resources_needed"] = ["Senior Engineer", "Project Manager", "Multiple Technicians"]
                        impact["sla_implications"] = "SLA breach likely"
                    elif affected_percentage >= 30 or critical_issues > 0:
                        impact["severity"] = "High"
                        impact["client_impact"] = f"Significant issues affecting {affected_percentage:.0f}% of devices"
                        impact["revenue_risk"] = "Medium"
                        impact["mitigation_time"] = "Response within hours"
                        impact["resources_needed"] = ["Engineer", "Multiple Technicians"]
                        impact["sla_implications"] = "Priority response required"
                    elif affected_percentage >= 10:
                        impact["severity"] = "Medium"
                        impact["client_impact"] = f"Issues affecting {affected_percentage:.0f}% of devices"
                        impact["revenue_risk"] = "Low"
                        impact["mitigation_time"] = "24-48 hours"
                        impact["resources_needed"] = ["Technician"]
                        impact["sla_implications"] = "Standard SLA response"

                # Adjust for organization size/importance if available
                if entity_type == "organisation":
                    # Check if this is a significant client
                    tenant = Tenants.query.get(entity.tenantuuid)
                    if tenant:
                        orgs_count = Organisations.query.filter_by(tenantuuid=tenant.tenantuuid).count()
                        if orgs_count > 0:
                            # Count devices across all orgs to see relative importance
                            all_devices_count = Devices.query.filter_by(tenantuuid=tenant.tenantuuid).count()
                            org_devices_count = len(devices)

                            if all_devices_count > 0:
                                org_importance = org_devices_count / all_devices_count

                                # If this org represents a significant portion of devices
                                if org_importance > 0.25:  # More than 25% of all devices
                                    # Increase severity and risk
                                    impact_levels = {"Low": 0, "Medium": 1, "High": 2, "Critical": 3}
                                    current_level = impact_levels.get(impact["severity"], 1)
                                    new_level = min(current_level + 1, 3)

                                    for level_name, level_value in impact_levels.items():
                                        if level_value == new_level:
                                            impact["severity"] = level_name
                                            break

                                    impact["client_impact"] += " (Major client)"
                                    impact["revenue_risk"] = "High"
                                    impact["sla_implications"] = "Prioritize response to protect client relationship"

            elif entity_type == "tenant":
                # For tenant level, this is an MSP-wide issue
                entity = Tenants.query.get(entity_uuid)
                if not entity:
                    return impact

                # For tenant-wide issues, consider total device count with issues
                if issue_type == "security":
                    # Count devices with security issues
                    security_metadata = DeviceMetadata.query.join(Devices).filter(
                        Devices.tenantuuid == entity_uuid,
                        DeviceMetadata.metalogos_type == 'eventsFiltered-Security',
                        DeviceMetadata.score < 70
                    ).count()

                    total_devices = Devices.query.filter_by(tenantuuid=entity_uuid).count()

                    if total_devices > 0:
                        affected_percentage = (security_metadata / total_devices) * 100

                        if affected_percentage >= 15:
                            impact["severity"] = "Critical"
                            impact["client_impact"] = "Widespread security issues affecting multiple clients"
                            impact["revenue_risk"] = "Very High"
                            impact["mitigation_time"] = "All hands response required"
                            impact["resources_needed"] = ["Security Team", "Technical Director", "Account Managers"]
                            impact["sla_implications"] = "Multiple SLA breaches likely"
                        elif affected_percentage >= 5:
                            impact["severity"] = "High"
                            impact["client_impact"] = "Security issues affecting multiple clients"
                            impact["revenue_risk"] = "High"
                            impact["mitigation_time"] = "Coordinated response plan needed"
                            impact["resources_needed"] = ["Security Specialist", "Multiple Technicians"]
                            impact["sla_implications"] = "Potential SLA breaches"

                elif issue_type == "performance":
                    # Similar logic for performance issues
                    perf_metadata = DeviceMetadata.query.join(Devices).filter(
                        Devices.tenantuuid == entity_uuid,
                        DeviceMetadata.metalogos_type.in_(['eventsFiltered-System', 'eventsFiltered-Application']),
                        DeviceMetadata.score < 70
                    ).count()

                    total_devices = Devices.query.filter_by(tenantuuid=entity_uuid).count()

                    if total_devices > 0:
                        affected_percentage = (perf_metadata / total_devices) * 100

                        if affected_percentage >= 20:
                            impact["severity"] = "High"
                            impact["client_impact"] = "Widespread performance issues affecting multiple clients"
                            impact["revenue_risk"] = "High"
                            impact["mitigation_time"] = "Coordinated response plan needed"
                            impact["resources_needed"] = ["Systems Engineer", "Multiple Technicians"]
                            impact["sla_implications"] = "Potential SLA breaches"

        except Exception as e:
            log_with_route(logging.ERROR, f"Error in business impact analysis: {str(e)}")

        return impact

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