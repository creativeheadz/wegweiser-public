# Filepath: app/tasks/macos_os/analyzer.py
from app.tasks.base.analyzer import BaseAnalyzer
import json
import re
import bleach
from typing import Dict, Any
from datetime import datetime

import os

# Default criteria prompt (used when tenant hasn't customized)
DEFAULT_CRITERIA = """1. Version Identification: Parse exact macOS version and codename.
2. Currency Assessment: Compare against latest available macOS versions.
3. Security Status: Evaluate security update availability and currency.
4. Compatibility: Assess app and hardware compatibility implications.
5. Upgrade Path: Recommend upgrade strategy if needed."""


class MacOSOSAnalyzer(BaseAnalyzer):
    """Analyzer for macOS Operating System Version Assessment"""

    task_type = 'macos-os-version'

    def should_run(self, device_uuid: str, context: Dict[str, Any]) -> bool:
        """Check if this analysis should run (when OS version changes)"""
        device_data = context.get('device_data', {})
        status = device_data.get('devicestatus', {})
        
        # Check if we have macOS device
        agent_platform = status.get('agent_platform', '')
        if not agent_platform.startswith('macOS'):
            return False
        
        # Check if OS version has changed since last analysis
        if context.get('analyses'):
            last_analysis = context['analyses'][0]
            last_metadata = last_analysis.get('metadata', {})
            last_os_version = last_metadata.get('os_version', '')
            
            current_os_version = agent_platform
            if current_os_version == last_os_version:
                # OS hasn't changed, don't run
                return False
        
        return True

    def create_prompt(self, current_data: Dict[str, Any], context: Dict[str, Any]) -> str:
        """Create analysis prompt for macOS OS version assessment with tenant customizations"""
        device_data = context.get('device_data', {})
        status = device_data.get('devicestatus', {})
        
        # Extract OS information
        agent_platform = status.get('agent_platform', 'Unknown')
        system_model = status.get('system_model', 'Unknown')
        
        # Get previous analysis for comparison
        previous = context['analyses'][0] if context['analyses'] else None
        previous_text = ""
        if previous:
            previous_text = f"""
PREVIOUS ANALYSIS:
Last OS Version: {previous.get('metadata', {}).get('os_version', 'Unknown')}
Last Score: {previous.get('score', 'Unknown')}
Previous Findings: {previous.get('analysis', 'No previous analysis')[:200]}...
"""

        # Get tenant customizations
        criteria = self.get_custom_criteria(DEFAULT_CRITERIA)
        exclusion_block = self.get_exclusion_block()

        with open(os.path.join(os.path.dirname(__file__), 'prompts', 'base.prompt'), 'r') as f:
            base_prompt = f.read()

        prompt = base_prompt.format(
            agent_platform=agent_platform,
            system_model=system_model,
            previous_analysis=previous_text,
            criteria=criteria,
            exclusion_block=exclusion_block,
            os_data=json.dumps({
                'agent_platform': agent_platform,
                'system_model': system_model,
                'analysis_date': datetime.now().isoformat()
            }, indent=2)
        )

        return prompt

    def parse_response(self, response: str) -> Dict[str, Any]:
        """Parse AI response into structured format - JSON ONLY"""
        result = self.parse_json_response(response)

        # Add metadata for change detection
        result['metadata'] = {
            'analysis_date': datetime.now().isoformat()
        }

        return result

    def get_data_sources(self, device_uuid: str) -> Dict[str, Any]:
        """Get required data sources for analysis"""
        from app.models import DeviceStatus
        
        # Get latest device status
        status = DeviceStatus.query.filter_by(deviceuuid=device_uuid).first()
        
        data = {}
        if status:
            data['devicestatus'] = {
                'agent_platform': status.agent_platform,
                'system_model': status.system_model,
                'system_manufacturer': status.system_manufacturer,
                'last_update': status.last_update
            }
            
        return data
