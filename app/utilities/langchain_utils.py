from langchain_core.messages import HumanMessage, AIMessage
from langchain_openai import AzureChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables.history import RunnableWithMessageHistory
from langchain_core.messages import BaseMessage
from langchain_core.tools import StructuredTool
from flask import current_app
from app.models import db, AIMemory, Devices, Groups, Organisations, Tenants, TenantMetadata, Conversations, Messages
from app.utilities.app_logging_helper import log_with_route

import json
import time
import uuid
import tiktoken
import backoff
from typing import List, Dict, Any
from pydantic import Field, BaseModel
from typing import Optional, List, Dict, Any
from uuid import UUID

# Constants
MEMORY_WINDOW_SIZE = 5  # Number of recent conversations to keep in memory

@backoff.on_exception(backoff.expo, lambda: Exception, max_tries=3)
def retry_on_error():
    pass

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
        return ["chat_history", "history", "long_term_context"]

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

        return {
            "chat_history": self.messages,
            "history": self.messages,  # For backward compatibility
            "long_term_context": self._load_long_term_memories()
        }

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
                    'conversation_uuid': self.conversation_uuid
                }
            else:
                return

        else:
            content = {
                'user_message': inputs.get('input', 'N/A'),
                'ai_message': outputs.get('output', 'N/A'),
                'conversation_uuid': self.conversation_uuid
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
                importance_score=importance_score
            )
            db.session.add(new_memory)
            db.session.commit()

            self._trickle_up_memory(new_memory)

    def _condense_memory(self, content: str) -> str:
        prompt = f"""
        Condense the following conversation into a brief, informative summary.
        Focus on key points, decisions, or important information.
        Ignore pleasantries or irrelevant details.

        Conversation:
        {content}

        Condensed summary:
        """
        response = self.llm.invoke(prompt)
        return response.content

    def _tokenize_memory(self, content: str) -> str:
        tokens = self.tokenizer.encode(content)
        return json.dumps(tokens)

    def _detokenize_memory(self, tokenized_content: str) -> str:
        tokens = json.loads(tokenized_content)
        return self.tokenizer.decode(tokens)

    def _calculate_importance(self, content: str) -> float:
        keywords = ['error', 'critical', 'urgent', 'important', 'failure', 'security', 'performance']
        score = sum(keyword in content.lower() for keyword in keywords) * 0.2
        return min(score + 0.3, 1.0)  # Base score of 0.3, max of 1.0

    def _trickle_up_memory(self, memory: AIMemory):
        if self.entity_type == 'device':
            device = Devices.query.get(self.entity_uuid)
            if device and memory.importance_score > 0.8:
                group_memory_content = self._condense_memory(f"Device {device.devicename}: {self._detokenize_memory(memory.content)}")
                group_memory = AIMemory(
                    memoryuuid=uuid.uuid4(),
                    entity_uuid=device.groupuuid,
                    entity_type='group',
                    tenantuuid=self.tenant_uuid,
                    content=self._tokenize_memory(group_memory_content),
                    created_at=int(time.time()),
                    last_accessed=int(time.time()),
                    importance_score=memory.importance_score * 0.9
                )
                db.session.add(group_memory)
                db.session.commit()
        elif self.entity_type == 'group':
            group = Groups.query.get(self.entity_uuid)
            if group and memory.importance_score > 0.8:
                org_memory_content = self._condense_memory(f"Group {group.groupname}: {self._detokenize_memory(memory.content)}")
                org_memory = AIMemory(
                    memoryuuid=uuid.uuid4(),
                    entity_uuid=group.orguuid,
                    entity_type='organisation',
                    tenantuuid=self.tenant_uuid,
                    content=self._tokenize_memory(org_memory_content),
                    created_at=int(time.time()),
                    last_accessed=int(time.time()),
                    importance_score=memory.importance_score * 0.9
                )
                db.session.add(org_memory)
                db.session.commit()
        elif self.entity_type == 'organisation':
            org = Organisations.query.get(self.entity_uuid)
            if org and memory.importance_score > 0.9:
                tenant_memory_content = self._condense_memory(f"Organisation {org.orgname}: {self._detokenize_memory(memory.content)}")
                tenant_memory = AIMemory(
                    memoryuuid=uuid.uuid4(),
                    entity_uuid=org.tenantuuid,
                    entity_type='tenant',
                    tenantuuid=self.tenant_uuid,
                    content=self._tokenize_memory(tenant_memory_content),
                    created_at=int(time.time()),
                    last_accessed=int(time.time()),
                    importance_score=memory.importance_score * 0.9
                )
                db.session.add(tenant_memory)
                db.session.commit()

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

def create_langchain_conversation(entity_uuid: str, entity_type: str, tenant_profile: str,
                                entity_context: str, user_context: str,
                                current_history: Optional[List] = None,
                                knowledge_graph: Optional[Any] = None) -> Any:

    device = Devices.query.get(entity_uuid) if entity_type == 'device' else None

    # Define base system prompt
    base_prompt = """You are Wegweiser, a technical assistant providing accurate information about a Managed Services Provider's (MSP's) devices.
                    When discussing device information:
                    1. Use the get_device_info tool to fetch real-time information
                    2. Only query the specific information type that was requested
                    3. Format values in appropriate units (GB, MHz, etc.)
                    4. Do not make assumptions about device configurations
                    5. For health scores and real-time metrics, always query the latest data with force_refresh=True
                    """

    system_prompt = base_prompt

    system_prompt += f"\nCurrent device context:\n{entity_context}"

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

    # Update prompt template
    prompt = ChatPromptTemplate.from_messages([
        ("system", """You are Wegweiser, an AI powered assistant for Managed Services Providers (MSPs). Your task is to look at various entities and provide accurate, actionable information.
        Entity Type: {entity_type}
        Entity Profile: {entity_profile}
        Context: {context}
        User Context: {user_context}
        Long-term Context: {long_term_context}

        Recent Conversation History:
        {recent_history}

        When asked about past conversations, refer to this history to provide context.
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
        Please, do not include any signature or final greeting.
        The messages are exchanged in an ongoing chat conversation so any such signature is awkward.

        Respond with a clear, detailed, and helpful answer to the user's question. Do not include any "Thought", "Action", or "Observation" sections in your response.

        Human: {input}
        Assistant: """)
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
            "entity_profile": lambda _: tenant_profile,  # Fix: use tenant_profile instead of entity_profile
            "context": lambda _: entity_context,
            "user_context": lambda _: user_context,
            "long_term_context": lambda x: memory.load_memory_variables(x)["long_term_context"],
            "recent_history": lambda _: recent_history,
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
        log_with_route("langchain_utils", f"Error in get_ai_response for {session_id}: {str(e)}")
        class SimpleResponse:
            def __init__(self, text):
                self.content = text
                self.token_usage = 0

        return SimpleResponse(f"I encountered an issue processing your request. Please try again or rephrase your question.")

def adapt_response_style(response, communication_style):
    response = response.replace("Best regards,", "").replace("[Your AI Assistant]", "").strip()
    if communication_style == 'formal':
        response = response.replace("you're", "you are").replace("don't", "do not")
    elif communication_style == 'casual':
        response = response.replace("Hello", "Hi").replace("Goodbye", "Bye")
    return response

def generate_health_score_analysis(entity_type, entity_uuid):
    llm = AzureChatOpenAI(
        openai_api_key=current_app.config['AZURE_OPENAI_API_KEY'],
        azure_endpoint=current_app.config['AZURE_OPENAI_ENDPOINT'],
        azure_deployment="wegweiser",
        openai_api_version=current_app.config['AZURE_OPENAI_API_VERSION'],
    )

    if entity_type == 'device':
        entity = Devices.query.get(entity_uuid)
        entity_name = entity.devicename
    elif entity_type == 'group':
        entity = Groups.query.get(entity_uuid)
        entity_name = entity.groupname
    elif entity_type == 'organisation':
        entity = Organisations.query.get(entity_uuid)
        entity_name = entity.orgname
    elif entity_type == 'tenant':
        entity = Tenants.query.get(entity_uuid)
        entity_name = entity.tenantname
    else:
        return "Invalid entity type"

    prompt = f"""
    Analyze the health score for the following {entity_type}:
    Name: {entity_name}
    Health Score: {entity.health_score}

    Provide a detailed analysis of the health score, including:
    1. What this score means for the {entity_type}'s overall performance and reliability
    2. Potential factors contributing to this score
    3. Recommendations for improving the score
    4. Specific monitoring suggestions for this {entity_type}
    5. Any potential security or performance concerns based on this score

    Your analysis should be thorough and actionable, providing clear steps for the Managed Services Provider (MSP) to take.
    """

    response = llm.invoke(prompt)
    return response.content

def generate_entity_suggestions(entity_type, entity_uuid):
    llm = AzureChatOpenAI(
        openai_api_key=current_app.config['AZURE_OPENAI_API_KEY'],
        azure_endpoint=current_app.config['AZURE_OPENAI_ENDPOINT'],
        azure_deployment="wegweiser",
        openai_api_version=current_app.config['AZURE_OPENAI_API_VERSION'],
    )

    if entity_type == 'group':
        entity = Groups.query.get(entity_uuid)
        entity_name = entity.groupname
        devices = Devices.query.filter_by(groupuuid=entity_uuid).all()
    elif entity_type == 'organisation':
        entity = Organisations.query.get(entity_uuid)
        entity_name = entity.orgname
        devices = Devices.query.join(Groups).filter(Groups.orguuid == entity_uuid).all()
    elif entity_type == 'tenant':
        entity = Tenants.query.get(entity_uuid)
        entity_name = entity.tenantname
        devices = Devices.query.filter_by(tenantuuid=entity_uuid).all()
    else:
        return "Invalid entity type"

    device_info = [f"Device: {d.devicename}, Health Score: {d.health_score}" for d in devices]

    prompt = f"""
    # Strategic Analysis Report for {entity_name}

    ## Entity Overview
    - Type: {entity_type.title()}
    - Name: {entity_name}
    - Health Score: {entity.health_score}
    - Total Devices: {len(devices)}

    ## Device Health Distribution
    {' '.join(device_info)}

    Based on the above metrics, provide a comprehensive analysis using the following structure:

    ## Current State Assessment
    [Provide objective analysis of current operational state, focusing on key metrics and performance indicators]

    ## Critical Focus Areas
    ### Primary Concerns
    [List and explain immediate areas needing attention]

    ### Secondary Considerations
    [List and explain important but less urgent areas]

    ## Health Score Optimization Strategy
    ### Short-term Improvements
    [List specific, actionable steps for immediate implementation]

    ### Long-term Recommendations
    [List strategic initiatives for sustained improvement]

    ## Monitoring Framework
    ### Key Metrics
    [List essential metrics to track]

    ### Alert Thresholds
    [Recommend specific trigger points for alerts]

    ## Automation Opportunities
    ### Immediate Implementation
    [List processes ready for automation]

    ### Future Considerations
    [List potential automation targets]

    ## Security Recommendations
    ### Critical Controls
    [List essential security measures]

    ### Best Practices
    [List recommended security practices]

    The analysis should be data-driven, focused on actionable insights, and aligned with MSP operational requirements.
    Format the response in clean markdown with clear section hierarchies.
    """

    response = llm.invoke(prompt)
    return response.content

def generate_tool_recommendations(tenant_uuid):
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
    missing_tools = []
    current_tools_list = []

    # Iterate through profile data to find missing tools and format current tools
    for tool_category, selected_tools in profile_data.items():
        # Check if it's a list (expected for multi-select fields)
        if isinstance(selected_tools, list):
            if not selected_tools:  # Empty list means no tools selected for this category
                missing_tools.append(tool_category)
            else:
                # Format the list of selected tools for this category
                current_tools_list.append(f"{tool_category}: {', '.join(selected_tools)}")
        # Handle potential legacy single-select fields or other data types
        elif selected_tools == 'none' or not selected_tools:
             missing_tools.append(tool_category)
        else:
             # Assume it's a single value if not a list
             current_tools_list.append(f"{tool_category}: {selected_tools}")


    if not missing_tools:
        return "All tool categories have selections." # Updated message

    # Join the formatted current tools strings
    current_tools_str = '; '.join(current_tools_list)

    tenant_info = f"""
    Tenant Name: {tenant.tenantname}
    Company Size: {tenant.company_size}
    # Industry: {tenant.industry} # Assuming industry might not be in profile_data
    Primary Focus: {tenant.primary_focus} # Assuming primary_focus might not be in profile_data
    Current Tools: {current_tools_str}
    Missing Tool Categories: {', '.join(missing_tools)}
    """

    prompt = f"""
    Based on {tenant.tenantname}'s profile as an MSP, here is a strategic analysis of recommended tools and solutions that could enhance their operations:

    {tenant_info}

    Provide a comprehensive tool recommendation analysis using this structure:

    # Tool Stack Analysis and Recommendations

    ## Current Technology Stack Overview
    [Provide a brief overview of their current tools ({current_tools_str}) and how they fit together]

    ## Recommended Tools and Solutions for Missing Categories

    [For each category listed in 'Missing Tool Categories', use this format:]

    ### [Category Name]

    **Current Status**: No tools selected in this category.

    **Business Impact**: [Brief explanation of how this gap affects operations, considering their Company Size and Primary Focus]

    **Recommendations**:
    - Top Enterprise Solution: [Name and brief description relevant to the category]
    - Mid-Range Option: [Name and brief description relevant to the category]
    - Budget-Friendly Choice: [Name and brief description relevant to the category]

    **Implementation Considerations**:
    - Key Benefits: [Focus on benefits for an MSP of this size/focus]
    - Potential Challenges: [e.g., integration, training]
    - Integration Points: [Which other tools might this integrate with?]

    [Continue for each major gap in their toolset as listed in 'Missing Tool Categories']

    ## Implementation Priority
    [Suggest a prioritized order for implementing tools for the missing categories based on their likely business impact and complexity for this specific MSP profile]

    Keep the tone professional and consultative, focusing on business value and operational efficiency. Ensure recommendations are relevant to the specific category mentioned.
    """
    response = llm.invoke(prompt)
    recommendations = response.content

    # Save the recommendations in the TenantMetadata table under 'metalogos'
    new_metadata = TenantMetadata(
        tenantuuid=tenant_uuid,
        metalogos_type='ai_recommendations',
        metalogos={'recommendations': recommendations},
        processing_status='processed'
    )
    db.session.add(new_metadata)
    db.session.commit()

    # Return the recommendations for display
    return recommendations