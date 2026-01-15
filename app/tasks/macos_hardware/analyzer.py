# Filepath: app/tasks/macos_hardware/analyzer.py
from app.tasks.base.analyzer import BaseAnalyzer
import json
import re
import bleach
from typing import Dict, Any
from datetime import datetime

import os

# Default criteria prompt (used when tenant hasn't customized)
DEFAULT_CRITERIA = """1. Hardware Identification: Identify the exact Mac model, year, and generation.
2. Apple EOL Status: Determine current support status (Current, Vintage, Obsolete).
3. Age Assessment: Calculate device age and remaining useful life.
4. Performance Impact: Assess how age affects current performance.
5. Upgrade Recommendations: Suggest if hardware upgrade is needed."""


class MacOSHardwareAnalyzer(BaseAnalyzer):
    """Analyzer for macOS Hardware End-of-Life Assessment"""

    task_type = 'macos-hardware-eol'

    def should_run(self, device_uuid: str, context: Dict[str, Any]) -> bool:
        """Check if this analysis should run (only once per device)"""
        # Check if we already have a hardware EOL analysis for this device
        if context.get('analyses'):
            # If we have previous analyses, don't run again
            return False
        
        # Check if we have the required data
        device_data = context.get('device_data', {})
        if not device_data.get('devicestatus') or not device_data.get('devicebios'):
            return False
            
        # Check if we have macOS device
        status = device_data.get('devicestatus', {})
        agent_platform = status.get('agent_platform', '')
        if not agent_platform.startswith('macOS'):
            return False
            
        return True

    def create_prompt(self, current_data: Dict[str, Any], context: Dict[str, Any]) -> str:
        """Create analysis prompt for macOS hardware EOL assessment with tenant customizations"""
        device_data = context.get('device_data', {})
        status = device_data.get('devicestatus', {})
        bios = device_data.get('devicebios', {})
        
        # Extract key hardware information
        system_model = status.get('system_model', 'Unknown')
        agent_platform = status.get('agent_platform', 'Unknown')
        serial_number = bios.get('bios_serial', 'Unknown')
        
        # Get tenant customizations
        criteria = self.get_custom_criteria(DEFAULT_CRITERIA)
        exclusion_block = self.get_exclusion_block()
        
        with open(os.path.join(os.path.dirname(__file__), 'prompts', 'base.prompt'), 'r') as f:
            base_prompt = f.read()

        prompt = base_prompt.format(
            system_model=system_model,
            agent_platform=agent_platform,
            serial_number=serial_number,
            criteria=criteria,
            exclusion_block=exclusion_block,
            hardware_data=json.dumps({
                'system_model': system_model,
                'agent_platform': agent_platform,
                'serial_number': serial_number,
                'system_manufacturer': status.get('system_manufacturer', 'Unknown'),
                'analysis_date': datetime.now().isoformat()
            }, indent=2)
        )

        return prompt

    def parse_response(self, response: str) -> Dict[str, Any]:
        """Parse AI response into structured format - JSON ONLY"""
        return self.parse_json_response(response)

    def get_data_sources(self, device_uuid: str) -> Dict[str, Any]:
        """Get required data sources for analysis"""
        from app.models import DeviceStatus, DeviceBios
        
        # Get latest device status
        status = DeviceStatus.query.filter_by(deviceuuid=device_uuid).first()
        bios = DeviceBios.query.filter_by(deviceuuid=device_uuid).first()
        
        data = {}
        if status:
            data['devicestatus'] = {
                'system_model': status.system_model,
                'agent_platform': status.agent_platform,
                'system_manufacturer': status.system_manufacturer,
                'last_update': status.last_update
            }
        
        if bios:
            data['devicebios'] = {
                'bios_serial': bios.bios_serial,
                'bios_vendor': bios.bios_vendor,
                'bios_version': bios.bios_version,
                'last_update': bios.last_update
            }
            
        return data
