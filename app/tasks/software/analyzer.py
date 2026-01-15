# Filepath: app/tasks/software/analyzer.py
from app.tasks.base.analyzer import BaseAnalyzer
import json
import re
import bleach
from typing import Dict, Any
from datetime import datetime

import os

# Default criteria prompt (used when tenant hasn't customized)
DEFAULT_CRITERIA = """1. Operating system assessment: OS version, build, edition, and patch level evaluation.
2. System services analysis: Critical service status, startup configuration, and dependencies.
3. Startup programs evaluation: Auto-start applications and their impact on boot time.
4. Windows features assessment: Installed features, roles, and optional components.
5. Framework and runtime analysis: .NET, Visual C++, Java versions and compatibility.
6. Update and patch status: Windows Update configuration and pending updates.
7. Security software evaluation: Antivirus, firewall, and security tool status.
8. Software licensing and compliance assessment."""


class SoftwareAnalyzer(BaseAnalyzer):
    """Analyzer for Windows System Software Configuration"""

    task_type = 'msinfo-SystemSoftwareConfig'

    def _truncate_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Truncate data to prevent token limit issues"""
        data_str = json.dumps(data, indent=2)
        if len(data_str) > 4000:  # Adjust this value as needed
            data_str = data_str[:4000] + "...[truncated]"
            return json.loads(data_str)
        return data

    def create_prompt(self, current_data: Dict[str, Any], context: Dict[str, Any]) -> str:
        """Create analysis prompt with historical context and tenant customizations"""
        # Truncate data if needed
        current_data = self._truncate_data(current_data)

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

        with open(os.path.join(os.path.dirname(__file__), 'prompts', 'base.prompt'), 'r') as f:
            base_prompt = f.read()

        # Get tenant customizations
        criteria = self.get_custom_criteria(DEFAULT_CRITERIA)
        exclusion_block = self.get_exclusion_block()

        prompt = base_prompt.format(
            software_data=json.dumps(current_data, indent=2)
        )

        return f"""You MUST respond with valid JSON only. No other text before or after.

Analyze the software data and return a single JSON object with EXACTLY these fields:
- analysis: Your detailed HTML analysis for display to users (use <p>, <ul>, <li>, <strong>, <em> tags)
- score: Health score from 1-100 (integer only, no quotes). Do NOT default to 85.

Analysis Criteria:
{criteria}

Previous Analysis Summary:
Last Health Score: {previous['score'] if previous else 'No previous score'}
Score Trend: {trend_text}

Previous Key Findings:
{previous['analysis'] if previous else 'No previous analysis'}

{exclusion_block}

{prompt}

Remember: Respond with ONLY the JSON object, no markdown code blocks, no explanations."""

    def parse_response(self, response: str) -> Dict[str, Any]:
        """Parse AI response into structured format - JSON ONLY"""
        return self.parse_json_response(response)