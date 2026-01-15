# Filepath: app/tasks/syslog/analyzer.py
from app.tasks.base.analyzer import BaseAnalyzer
import json
import re
import bleach
from typing import Dict, Any
from datetime import datetime

import os

# Default criteria prompt (used when tenant hasn't customized)
DEFAULT_CRITERIA = """1. System service analysis: Service start/stop events, failures, and restarts.
2. Authentication and access events: Login attempts, sudo usage, and privilege escalations.
3. Cron and scheduled task evaluation: Scheduled job execution and failures.
4. Application logging assessment: Key application events and error patterns.
5. Network service events: SSH, HTTP, DNS, and other service activities.
6. Package management events: Updates, installations, and removals.
7. System state changes: Reboots, shutdowns, and runlevel changes.
8. Security-relevant events: Failed authentications, suspicious activities."""


class SyslogAnalyzer(BaseAnalyzer):
    """Analyzer for Linux Syslog Data"""

    task_type = 'syslogFiltered'

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

        with open(os.path.join(os.path.dirname(__file__), 'prompts', 'base.prompt'), 'r') as f:
            base_prompt = f.read()

        # Get tenant customizations
        criteria = self.get_custom_criteria(DEFAULT_CRITERIA)
        exclusion_block = self.get_exclusion_block()

        prompt = base_prompt.format(
            syslog_data=json.dumps(current_data, indent=2)
        )

        return f"""You MUST respond with valid JSON only. No other text before or after.

Analyze the syslog data and return a single JSON object with EXACTLY these fields:
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