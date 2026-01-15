# Filepath: app/tasks/groups/analyzer.py
from app.tasks.base.analyzer import BaseAnalyzer
from app.tasks.base.exclusions import build_exclusion_block_for_group, get_tenant_prompt_config
from app.models import db, Groups, Devices, DeviceMetadata, GroupMetadata
from app.models.devices import DeviceStatus
from sqlalchemy import text, desc
import json
import re
import bleach
from typing import Dict, Any, List
from datetime import datetime
import logging
import os
from pathlib import Path
from abc import abstractmethod
from flask import current_app

# Default criteria prompt (used when tenant hasn't customized)
DEFAULT_CRITERIA = """1. Top 10 Worst Performers: Identify the 10 devices with the lowest health scores, summarize their most critical issues.
2. Pattern Detection: Look for common issues across multiple devices, identify recurring problems that suggest systemic issues.
3. Programmatic Summary: Total device count, OS breakdown, average health score, health score distribution.
4. Critical Recommendations: Immediate actions needed for worst performers, preventive measures for common patterns."""


class GroupAnalyzer(BaseAnalyzer):
    """Analyzer for group-level health analysis"""

    task_type = 'group-health-analysis'

    def __init__(self, group_id: str, metadata_id: str):
        # Override parent constructor to use group_id instead of device_id
        self.group_id = group_id
        self.metadata_id = metadata_id
        self._config = None

    def get_custom_criteria(self, default_criteria: str) -> str:
        """Get custom criteria from tenant config or use default"""
        try:
            group = db.session.get(Groups, self.group_id)
            if not group:
                return default_criteria
            
            config = get_tenant_prompt_config(str(group.tenantuuid), self.task_type)
            if config and config.criteria_prompt:
                return config.criteria_prompt
        except Exception as e:
            logging.warning(f"Error getting custom criteria for group {self.group_id}: {e}")
        return default_criteria

    def get_exclusion_block(self) -> str:
        """Get the exclusion block for this group"""
        try:
            return build_exclusion_block_for_group(self.group_id, self.task_type)
        except Exception as e:
            logging.warning(f"Error building exclusion block for group {self.group_id}: {e}")
            return ''

    def validate(self) -> bool:
        """Validate that group exists and has devices"""
        try:
            group = db.session.query(Groups).get(self.group_id)
            if not group:
                logging.error(f"Group {self.group_id} not found")
                return False
            
            # Check if group has devices
            device_count = db.session.query(Devices).filter_by(groupuuid=self.group_id).count()
            if device_count == 0:
                logging.warning(f"Group {self.group_id} has no devices")
                return False
                
            return True
        except Exception as e:
            logging.error(f"Validation error for group {self.group_id}: {str(e)}")
            return False

    def bill_tenant(self, group) -> bool:
        """Bill the tenant for group analysis"""
        try:
            from app.models import Tenants

            cost = self.get_cost()
            tenant = db.session.query(Tenants).get(group.tenantuuid)

            if not tenant:
                logging.error(f"Tenant not found for group {self.group_id}")
                return False

            logging.info(f"Billing tenant {tenant.tenantuuid} {cost} wegcoins for {self.task_type}")

            return tenant.deduct_wegcoins(cost, f"Group analysis for {group.groupname}")

        except Exception as e:
            logging.error(f"Billing error for group {self.group_id}: {str(e)}")
            return False

    def get_group_device_data(self) -> Dict[str, Any]:
        """Collect comprehensive device data for the group"""
        try:
            # Get group and its devices
            group = db.session.query(Groups).get(self.group_id)
            devices = db.session.query(Devices).filter_by(groupuuid=self.group_id).all()
            
            device_data = []
            os_counts = {}
            health_distribution = {'excellent': 0, 'good': 0, 'fair': 0, 'poor': 0}
            
            for device in devices:
                # Get latest analyses for this device
                latest_analyses = db.session.execute(text("""
                    SELECT DISTINCT ON (metalogos_type)
                        metalogos_type,
                        ai_analysis,
                        score,
                        analyzed_at
                    FROM devicemetadata
                    WHERE deviceuuid = :device_uuid
                    AND processing_status = 'processed'
                    ORDER BY metalogos_type, created_at DESC
                """), {'device_uuid': str(device.deviceuuid)}).fetchall()
                
                # Get OS type from hardwareinfo
                os_type = device.hardwareinfo or 'Unknown'
                os_counts[os_type] = os_counts.get(os_type, 0) + 1
                
                # Categorize health score
                health_score = device.health_score or 0
                if health_score >= 90:
                    health_distribution['excellent'] += 1
                elif health_score >= 70:
                    health_distribution['good'] += 1
                elif health_score >= 50:
                    health_distribution['fair'] += 1
                else:
                    health_distribution['poor'] += 1
                
                device_info = {
                    'uuid': str(device.deviceuuid),
                    'name': device.devicename,
                    'health_score': health_score,
                    'os_type': os_type,
                    'location': getattr(device, 'location', 'Unknown'),
                    'analyses': []
                }
                
                # Add analysis summaries
                for analysis in latest_analyses:
                    # Extract key issues from analysis text
                    analysis_text = analysis.ai_analysis or ""
                    # Simple extraction of first few sentences for summary
                    sentences = analysis_text.split('.')[:2]
                    summary = '. '.join(sentences).strip()
                    if summary and not summary.endswith('.'):
                        summary += '.'
                    
                    device_info['analyses'].append({
                        'type': analysis.metalogos_type,
                        'score': int(analysis.score) if analysis.score else 0,
                        'summary': summary[:200] + '...' if len(summary) > 200 else summary,
                        'analyzed_at': analysis.analyzed_at
                    })
                
                device_data.append(device_info)
            
            # Sort devices by health score (worst first)
            device_data.sort(key=lambda x: x['health_score'])
            
            return {
                'group_name': group.groupname,
                'group_uuid': str(group.groupuuid),
                'total_devices': len(devices),
                'devices': device_data,
                'os_distribution': os_counts,
                'health_distribution': health_distribution,
                'average_health': sum(d['health_score'] for d in device_data) / len(device_data) if device_data else 0
            }
            
        except Exception as e:
            logging.error(f"Error collecting group device data: {str(e)}")
            return {}

    def create_prompt(self, current_data: Dict[str, Any], context: Dict[str, Any]) -> str:
        """Create analysis prompt with group device data and tenant customizations"""
        try:
            # Load the base prompt template
            prompt_file = Path(__file__).parent / 'prompts' / 'base.prompt'
            with open(prompt_file, 'r') as f:
                base_prompt = f.read()
            
            # Get group data
            group_data = self.get_group_device_data()
            
            # Get tenant customizations
            criteria = self.get_custom_criteria(DEFAULT_CRITERIA)
            exclusion_block = self.get_exclusion_block()
            
            # Create detailed prompt with actual data
            data_section = f"""
## Group Data Analysis:

**Group:** {group_data.get('group_name', 'Unknown')}
**Total Devices:** {group_data.get('total_devices', 0)}
**Average Health Score:** {group_data.get('average_health', 0):.1f}%

### OS Distribution:
{json.dumps(group_data.get('os_distribution', {}), indent=2)}

### Health Score Distribution:
- Excellent (90-100%): {group_data.get('health_distribution', {}).get('excellent', 0)} devices
- Good (70-89%): {group_data.get('health_distribution', {}).get('good', 0)} devices  
- Fair (50-69%): {group_data.get('health_distribution', {}).get('fair', 0)} devices
- Poor (<50%): {group_data.get('health_distribution', {}).get('poor', 0)} devices

### Top 10 Worst Performing Devices:
"""
            
            # Add worst performers
            worst_devices = group_data.get('devices', [])[:10]
            for i, device in enumerate(worst_devices, 1):
                data_section += f"""
**{i}. {device['name']}** (Health: {device['health_score']}%, OS: {device['os_type']})
Location: {device.get('location', 'Unknown')}
Recent Issues:"""
                
                for analysis in device.get('analyses', [])[:3]:  # Top 3 analyses
                    data_section += f"\n- {analysis['type']}: {analysis['summary']}"
                
                data_section += "\n"
            
            # Add previous analysis context if available
            previous_context = ""
            if context.get('analyses'):
                previous = context['analyses'][0]
                previous_context = f"""
### Previous Group Analysis:
**Previous Health Score:** {previous.get('score', 'N/A')}
**Key Previous Findings:** {previous.get('analysis', 'No previous analysis')[:300]}...
"""
            
            return f"""You MUST respond with valid JSON only. No other text before or after.

Analyze the group data and return a single JSON object with EXACTLY these fields:
- analysis: Your detailed HTML analysis for display to users (use <p>, <ul>, <li>, <strong>, <em> tags)
- score: Health score from 1-100 (integer only, no quotes). Do NOT default to 85.

Analysis Criteria:
{criteria}

{base_prompt}

{data_section}

{previous_context}

{exclusion_block}

Remember: Respond with ONLY the JSON object, no markdown code blocks, no explanations."""
            
        except Exception as e:
            logging.error(f"Error creating prompt: {str(e)}")
            return "Error creating analysis prompt"

    def parse_response(self, response: str) -> Dict[str, Any]:
        """Parse AI response into structured format - JSON ONLY"""
        return self.parse_json_response(response)

    def get_historical_context(self) -> Dict[str, Any]:
        """Get historical group analysis context"""
        try:
            # Get previous group analyses
            previous_analyses = db.session.query(GroupMetadata).filter_by(
                groupuuid=self.group_id,
                metalogos_type=self.task_type,
                processing_status='processed'
            ).order_by(desc(GroupMetadata.created_at)).limit(3).all()
            
            analyses = []
            scores = []
            
            for analysis in previous_analyses:
                analyses.append({
                    'analysis': analysis.ai_analysis,
                    'score': analysis.score,
                    'timestamp': analysis.analyzed_at
                })
                if analysis.score:
                    try:
                        scores.append(int(analysis.score))
                    except (ValueError, TypeError):
                        pass
            
            return {
                'analyses': analyses,
                'score_trend': scores
            }
            
        except Exception as e:
            logging.error(f"Error getting historical context: {str(e)}")
            return {'analyses': [], 'score_trend': []}

    def analyze(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Execute group analysis with historical context"""
        try:
            # Get group and validate before transaction
            group = db.session.query(Groups).get(self.group_id)
            if not self.validate():
                raise ValueError("Validation failed")

            # Process billing first - this handles its own transaction
            if not self.bill_tenant(group):
                raise ValueError("Billing failed")

            # Get historical context
            context = self.get_historical_context()

            # Create prompt with context
            prompt = self.create_prompt(data, context)

            # Get AI response
            client = self.get_ai_client()
            response = client.chat.completions.create(
                model="wegweiser",
                messages=[
                    {"role": "system", "content": "You are a system administrator analyzing group health."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=self.config.get('max_tokens', 2000),
                temperature=self.config.get('temperature', 0.5)
            )

            # Parse response
            result = self.parse_response(response.choices[0].message.content)

            # Update group metadata
            metadata = db.session.query(GroupMetadata).get(self.metadata_id)
            metadata.ai_analysis = result['analysis']
            metadata.score = result['score']
            metadata.processing_status = 'processed'
            metadata.analyzed_at = int(datetime.utcnow().timestamp())

            # Update group health score
            group.health_score = float(result['score'])

            db.session.commit()
            return result

        except Exception as e:
            msg = f"Analysis error for {self.task_type} on group {self.group_id}: {str(e)}"
            if str(e) == "Validation failed":
                logging.info(msg)
            else:
                logging.error(msg)
            db.session.rollback()
            return {
                'analysis': f'<p>Analysis failed: {str(e)}</p>',
                'score': 0,
                'timestamp': datetime.utcnow().isoformat()
            }
