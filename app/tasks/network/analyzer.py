# Filepath: app/tasks/network/analyzer.py
from app.tasks.base.analyzer import BaseAnalyzer
from app.tasks.base.exclusions import (
    build_exclusion_block, 
    get_tenant_prompt_config,
    get_density_config
)
import json
import re
import bleach
from typing import Dict, Any
from datetime import datetime

import os

# Default criteria prompt (used when tenant hasn't customized)
DEFAULT_CRITERIA = """1. Detailed evaluation of network interface configurations, including adapter types, driver versions, link speeds, duplex settings, and operational status.
2. Assessment of IP addressing schemes, subnet configurations, DHCP vs static assignments, and potential addressing conflicts or inefficiencies.
3. Analysis of network performance metrics, including bandwidth utilization, latency indicators, packet loss, and throughput characteristics.
4. Identification of network bottlenecks, misconfigurations, or hardware limitations that could impact performance or reliability.
5. Evaluation of network security posture, including firewall configurations, open ports, network segmentation, and potential vulnerabilities.
6. Assessment of network redundancy, failover capabilities, and single points of failure that could affect business continuity.
7. Analysis of network protocols in use, quality of service (QoS) configurations, and optimization opportunities.
8. Recommendations for network monitoring, alerting thresholds, and proactive maintenance strategies."""


class NetworkAnalyzer(BaseAnalyzer):
    """Analyzer for Windows Network Configuration"""

    task_type = 'msinfo-NetworkConfig'

    def create_prompt(self, current_data: Dict[str, Any], context: Dict[str, Any]) -> str:
        """Create analysis prompt with historical context and tenant customizations"""
        previous = context['analyses'][0] if context['analyses'] else None
        score_trend = context['score_trend']
        trend_text = "No previous scores available"
        
        if score_trend:
            if len(score_trend) > 1:
                if score_trend[0] > score_trend[-1]:
                    trend_text = f"Health score improving: {score_trend[::-1]}"
                elif score_trend[0] < score_trend[-1]:
                    trend_text = f"Health score declining: {score_trend[::-1]}"
                else:
                    trend_text = f"Health score stable: {score_trend[::-1]}"
            else:
                trend_text = f"Single previous score: {score_trend[0]}"

        # Load base prompt template
        with open(os.path.join(os.path.dirname(__file__), 'prompts', 'base.prompt'), 'r') as f:
            base_prompt = f.read()

        # Get tenant customizations
        from app.models import db, Devices
        device = db.session.get(Devices, self.device_id)
        tenant_id = str(device.tenantuuid) if device else None
        
        # Get custom criteria or use default
        criteria = DEFAULT_CRITERIA
        if tenant_id:
            prompt_config = get_tenant_prompt_config(tenant_id, self.task_type)
            if prompt_config and prompt_config.criteria_prompt:
                criteria = prompt_config.criteria_prompt
        
        # Get density configuration
        density = get_density_config(tenant_id, self.task_type) if tenant_id else {}
        
        # Build exclusion block (sandboxed)
        exclusion_block = build_exclusion_block(self.device_id, self.task_type)

        # Format the prompt with all placeholders
        prompt = base_prompt.format(
            criteria=criteria,
            summary_sentences=density.get('summary_sentences', 3),
            detail_bullets=density.get('detail_bullets', 5),
            performance_bullets=density.get('performance_bullets', 4),
            security_bullets=density.get('security_bullets', 3),
            reliability_bullets=density.get('reliability_bullets', 3),
            monitoring_bullets=density.get('monitoring_bullets', 3),
            exclusion_block=exclusion_block,
            network_data=json.dumps(current_data, indent=2)
        )

        return f"""You MUST respond with valid JSON only. No other text before or after.

    Analyze the network data and return a single JSON object with EXACTLY these fields:
    - analysis: HTML formatted analysis with <p>, <ul>, <li> tags
    - score: Health score from 1-100 (integer only, no quotes). Do NOT default to 85.

Previous Analysis Summary:
Last Health Score: {previous['score'] if previous else 'No previous score'}
Score Trend: {trend_text}

Previous Key Findings:
{previous['analysis'] if previous else 'No previous analysis'}

{prompt}

Remember: Respond with ONLY the JSON object, no markdown code blocks, no explanations."""

    def parse_response(self, response: str) -> Dict[str, Any]:
        """Parse AI response into structured format - JSON ONLY"""
        return self.parse_json_response(response)