from typing import List, Dict, Any, Optional
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
import logging
from datetime import datetime
from flask import current_app
from app.utilities.app_logging_helper import log_with_route
from app.models import db, AIMemory

from typing import List, Dict

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