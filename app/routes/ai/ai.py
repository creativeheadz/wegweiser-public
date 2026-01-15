# Filepath: app/routes/ai/ai.py
# Compatibility module to maintain backward compatibility with existing imports
# This file re-exports components from the new modular structure

# Flask imports
from flask import Blueprint, request, jsonify, current_app, session, render_template

# SQLAlchemy imports
from sqlalchemy import func, distinct, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
import re

# Standard library imports
import os
import time
import uuid
import json
import logging
from uuid import UUID
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional

# Third party imports
from dotenv import load_dotenv
from langchain_openai import AzureChatOpenAI

# App models
from app.models import (
    db, 
    Devices, 
    DeviceMetadata, 
    Tenants, 
    Messages, 
    Groups, 
    Organisations,
    HealthScoreHistory,
    DeviceStatus, 
    DeviceGpu, 
    DeviceBios, 
    DeviceMemory, 
    DeviceDrives, 
    DeviceBattery,
    DeviceNetworks,
    DevicePrinters,
)
from app.models import Conversations as ConversationModel
from app.models import Conversations as LegacyConversationModel

# App utilities
from app import csrf
from app.utilities.app_logging_helper import log_with_route
from app.utilities.app_access_login_required import login_required
from app.utilities.langchain_utils import (
    EntityMemoryManager,
    create_langchain_conversation,
    get_ai_response,
    adapt_response_style,
    generate_health_score_analysis,
    generate_entity_suggestions,
    get_tenant_uuid_for_entity,
    MEMORY_WINDOW_SIZE
)
from app.utilities.knowledge_graph import KnowledgeGraph

# Import from the blueprint
from . import ai_bp

# Import from core module
from .core import (
    checkDir,
    get_entity,
    get_or_create_conversation,
    store_conversation,
    get_tenant_profile,
    get_printers_by_deviceuuid,
    _extract_top_events
)

# Import from entity module
from .entity.utils import (
    get_entity_context,
    _format_device_info,
    get_device_metadata_context,
    get_hierarchical_entity_context
)

# Import from chat module
from .chat.routes import (
    entity_chat,
    get_entity_chat_history
)

# Import from entity module
from .entity.routes import (
    get_health_score_analysis,
    get_entity_suggestions
)

# Import from health module
from .health.routes import memory_health

# Import from wegcoin module
from .wegcoin.routes import get_wegcoin_balance

# Re-export entity_memory_manager for backward compatibility
entity_memory_manager = EntityMemoryManager()

# Load environment variables
load_dotenv()
LOG_DEVICE_HEALTH_SCORE = os.getenv('LOG_DEVICE_HEALTH_SCORE', 'False').lower() == 'true'

# Define CHAT_HISTORY_LIMIT for backward compatibility
CHAT_HISTORY_LIMIT = 10

# This file serves as a compatibility layer for existing code that imports from app.routes.ai.ai
# All functionality has been moved to modular files in subdirectories
