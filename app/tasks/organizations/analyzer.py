# Filepath: app/tasks/organizations/analyzer.py
from app.tasks.base.analyzer import BaseAnalyzer
from app.tasks.base.exclusions import build_exclusion_block_for_org, get_tenant_prompt_config
from app.models import db, Organisations, Groups, Devices, DeviceMetadata, OrganizationMetadata
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
DEFAULT_CRITERIA = """1. Top 10 Worst Performing Groups: Identify groups with lowest health scores, summarize critical issues.
2. Cross-Group Pattern Detection: Look for common issues across multiple groups, identify systemic problems.
3. Organizational Summary: Total group and device count, OS distribution, average health score, health distribution.
4. Strategic Recommendations: Organization-wide policies needed, resource allocation priorities, risk mitigation strategies."""


class OrganizationAnalyzer(BaseAnalyzer):
    """Analyzer for organization-level health analysis"""

    task_type = 'organization-health-analysis'

    def __init__(self, org_id: str, metadata_id: str):
        # Override parent constructor to use org_id instead of device_id
        self.org_id = org_id
        self.metadata_id = metadata_id
        self._config = None

    def get_custom_criteria(self, default_criteria: str) -> str:
        """Get custom criteria from tenant config or use default"""
        try:
            org = db.session.get(Organisations, self.org_id)
            if not org:
                return default_criteria
            
            config = get_tenant_prompt_config(str(org.tenantuuid), self.task_type)
            if config and config.criteria_prompt:
                return config.criteria_prompt
        except Exception as e:
            logging.warning(f"Error getting custom criteria for org {self.org_id}: {e}")
        return default_criteria

    def get_exclusion_block(self) -> str:
        """Get the exclusion block for this organization"""
        try:
            return build_exclusion_block_for_org(self.org_id, self.task_type)
        except Exception as e:
            logging.warning(f"Error building exclusion block for org {self.org_id}: {e}")
            return ''

    def validate(self) -> bool:
        """Validate that organization exists and has groups"""
        try:
            org = db.session.query(Organisations).get(self.org_id)
            if not org:
                logging.error(f"Organization {self.org_id} not found")
                return False
            
            # Check if organization has groups
            group_count = db.session.query(Groups).filter_by(orguuid=self.org_id).count()
            if group_count == 0:
                logging.warning(f"Organization {self.org_id} has no groups")
                return False
                
            return True
        except Exception as e:
            logging.error(f"Validation error for organization {self.org_id}: {str(e)}")
            return False

    def bill_tenant(self, org) -> bool:
        """Bill the tenant for organization analysis"""
        try:
            from app.models import Tenants

            cost = self.get_cost()
            tenant = db.session.query(Tenants).get(org.tenantuuid)

            if not tenant:
                logging.error(f"Tenant not found for organization {self.org_id}")
                return False

            logging.info(f"Billing tenant {tenant.tenantuuid} {cost} wegcoins for {self.task_type}")

            return tenant.deduct_wegcoins(cost, f"Organization analysis for {org.orgname}")

        except Exception as e:
            logging.error(f"Billing error for organization {self.org_id}: {str(e)}")
            return False

    def get_organization_group_data(self) -> Dict[str, Any]:
        """Collect comprehensive group and device data for the organization"""
        try:
            # Get organization and its groups
            org = db.session.query(Organisations).get(self.org_id)
            groups = db.session.query(Groups).filter_by(orguuid=self.org_id).all()
            
            group_data = []
            total_devices = 0
            os_counts = {}
            health_distribution = {'excellent': 0, 'good': 0, 'fair': 0, 'poor': 0}
            location_groups = {}
            
            for group in groups:
                # Get devices for this group
                devices = db.session.query(Devices).filter_by(groupuuid=group.groupuuid).all()
                group_device_count = len(devices)
                total_devices += group_device_count
                
                # Calculate group-level statistics
                group_health_scores = []
                group_os_counts = {}
                
                for device in devices:
                    # Get OS type from hardwareinfo
                    os_type = device.hardwareinfo or 'Unknown'
                    os_counts[os_type] = os_counts.get(os_type, 0) + 1
                    group_os_counts[os_type] = group_os_counts.get(os_type, 0) + 1
                    
                    # Collect health scores
                    health_score = device.health_score or 0
                    group_health_scores.append(health_score)
                    
                    # Categorize health score
                    if health_score >= 90:
                        health_distribution['excellent'] += 1
                    elif health_score >= 70:
                        health_distribution['good'] += 1
                    elif health_score >= 50:
                        health_distribution['fair'] += 1
                    else:
                        health_distribution['poor'] += 1
                
                # Calculate group average health
                group_avg_health = sum(group_health_scores) / len(group_health_scores) if group_health_scores else 0
                
                # Get group location (if available)
                group_location = getattr(group, 'location', 'Unknown')
                if group_location not in location_groups:
                    location_groups[group_location] = []
                location_groups[group_location].append(group.groupname)
                
                # Get latest group analyses
                latest_group_analyses = db.session.execute(text("""
                    SELECT DISTINCT ON (metalogos_type)
                        metalogos_type,
                        ai_analysis,
                        score,
                        analyzed_at
                    FROM groupmetadata
                    WHERE groupuuid = :group_uuid
                    AND processing_status = 'processed'
                    ORDER BY metalogos_type, created_at DESC
                """), {'group_uuid': str(group.groupuuid)}).fetchall()
                
                group_info = {
                    'uuid': str(group.groupuuid),
                    'name': group.groupname,
                    'health_score': group.health_score or group_avg_health,
                    'device_count': group_device_count,
                    'location': group_location,
                    'os_distribution': group_os_counts,
                    'avg_device_health': group_avg_health,
                    'analyses': []
                }
                
                # Add group analysis summaries
                for analysis in latest_group_analyses:
                    # Extract key issues from analysis text
                    analysis_text = analysis.ai_analysis or ""
                    # Simple extraction of first few sentences for summary
                    sentences = analysis_text.split('.')[:2]
                    summary = '. '.join(sentences).strip()
                    if summary and not summary.endswith('.'):
                        summary += '.'
                    
                    group_info['analyses'].append({
                        'type': analysis.metalogos_type,
                        'score': int(analysis.score) if analysis.score else 0,
                        'summary': summary[:200] + '...' if len(summary) > 200 else summary,
                        'analyzed_at': analysis.analyzed_at
                    })
                
                group_data.append(group_info)
            
            # Sort groups by health score (worst first)
            group_data.sort(key=lambda x: x['health_score'])
            
            return {
                'org_name': org.orgname,
                'org_uuid': str(org.orguuid),
                'total_groups': len(groups),
                'total_devices': total_devices,
                'groups': group_data,
                'os_distribution': os_counts,
                'health_distribution': health_distribution,
                'location_distribution': location_groups,
                'average_health': sum(g['health_score'] for g in group_data) / len(group_data) if group_data else 0
            }
            
        except Exception as e:
            logging.error(f"Error collecting organization group data: {str(e)}")
            return {}

    def create_prompt(self, current_data: Dict[str, Any], context: Dict[str, Any]) -> str:
        """Create analysis prompt with organization group data and tenant customizations"""
        try:
            # Load the base prompt template
            prompt_file = Path(__file__).parent / 'prompts' / 'base.prompt'
            with open(prompt_file, 'r') as f:
                base_prompt = f.read()

            # Get organization data
            org_data = self.get_organization_group_data()

            # Get tenant customizations
            criteria = self.get_custom_criteria(DEFAULT_CRITERIA)
            exclusion_block = self.get_exclusion_block()

            # Create detailed prompt with actual data
            data_section = f"""
## Organization Data Analysis:

**Organization:** {org_data.get('org_name', 'Unknown')}
**Total Groups:** {org_data.get('total_groups', 0)}
**Total Devices:** {org_data.get('total_devices', 0)}
**Average Health Score:** {org_data.get('average_health', 0):.1f}%

### OS Distribution Across Organization:
{json.dumps(org_data.get('os_distribution', {}), indent=2)}

### Health Score Distribution:
- Excellent (90-100%): {org_data.get('health_distribution', {}).get('excellent', 0)} devices
- Good (70-89%): {org_data.get('health_distribution', {}).get('good', 0)} devices
- Fair (50-69%): {org_data.get('health_distribution', {}).get('fair', 0)} devices
- Poor (<50%): {org_data.get('health_distribution', {}).get('poor', 0)} devices

### Location Distribution:
{json.dumps(org_data.get('location_distribution', {}), indent=2)}

### Top 10 Worst Performing Groups:
"""

            # Add worst performing groups
            worst_groups = org_data.get('groups', [])[:10]
            for i, group in enumerate(worst_groups, 1):
                data_section += f"""
**{i}. {group['name']}** (Health: {group['health_score']:.1f}%, Devices: {group['device_count']})
Location: {group.get('location', 'Unknown')}
OS Distribution: {json.dumps(group.get('os_distribution', {}), indent=2)}
Recent Group Issues:"""

                for analysis in group.get('analyses', [])[:2]:  # Top 2 analyses per group
                    data_section += f"\n- {analysis['type']}: {analysis['summary']}"

                data_section += "\n"

            # Add previous analysis context if available
            previous_context = ""
            if context.get('analyses'):
                previous = context['analyses'][0]
                previous_context = f"""
### Previous Organization Analysis:
**Previous Health Score:** {previous.get('score', 'N/A')}
**Key Previous Findings:** {previous.get('analysis', 'No previous analysis')[:300]}...
"""

            return f"""You MUST respond with valid JSON only. No other text before or after.

Analyze the organization data and return a single JSON object with EXACTLY these fields:
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
        """Get historical organization analysis context"""
        try:
            # Get previous organization analyses
            previous_analyses = db.session.query(OrganizationMetadata).filter_by(
                orguuid=self.org_id,
                metalogos_type=self.task_type,
                processing_status='processed'
            ).order_by(desc(OrganizationMetadata.created_at)).limit(3).all()

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
        """Execute organization analysis with historical context"""
        try:
            # Get organization and validate before transaction
            org = db.session.query(Organisations).get(self.org_id)
            if not self.validate():
                raise ValueError("Validation failed")

            # Process billing first - this handles its own transaction
            if not self.bill_tenant(org):
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
                    {"role": "system", "content": "You are a system administrator analyzing organization health."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=self.config.get('max_tokens', 2000),
                temperature=self.config.get('temperature', 0.5)
            )

            # Parse response
            result = self.parse_response(response.choices[0].message.content)

            # Update organization metadata
            metadata = db.session.query(OrganizationMetadata).get(self.metadata_id)
            metadata.ai_analysis = result['analysis']
            metadata.score = result['score']
            metadata.processing_status = 'processed'
            metadata.analyzed_at = int(datetime.utcnow().timestamp())

            # Update organization health score
            org.health_score = float(result['score'])

            db.session.commit()
            return result

        except Exception as e:
            msg = f"Analysis error for {self.task_type} on organization {self.org_id}: {str(e)}"
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
