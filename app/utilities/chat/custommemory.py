from langchain_core.messages import HumanMessage, AIMessage, BaseMessage
from langchain_openai import AzureChatOpenAI
from flask import current_app
from app.models import (
    db, AIMemory, Devices, Groups, Organisations, Tenants,
    TenantMetadata, Conversations, Messages
)
from app.utilities.app_logging_helper import log_with_route

import json
import tiktoken
from typing import List, Dict, Any, Optional
from pydantic import Field, BaseModel
from uuid import UUID
from datetime import datetime, timedelta

# Constants
MEMORY_WINDOW_SIZE = 5  # Number of recent conversations to keep in memory


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
