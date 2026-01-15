# Filepath: app/tasks/auth/analyzer.py
from app.tasks.base.analyzer import BaseAnalyzer
import json
import re
import bleach
from typing import Dict, Any
from datetime import datetime

# Default criteria prompt (used when tenant hasn't customized)
DEFAULT_CRITERIA = """1. Authentication event analysis: Login success/failure patterns and anomalies.
2. SSH access evaluation: Remote login attempts, key-based vs password auth.
3. Privilege escalation monitoring: Sudo usage, su commands, and root access.
4. Failed authentication patterns: Brute force indicators and repeated failures.
5. User session analysis: Session durations, concurrent logins, unusual times.
6. PAM module events: Authentication module issues and configuration problems.
7. Account lockout and policy enforcement: Password policy compliance.
8. Security posture assessment and recommendations."""


class AuthAnalyzer(BaseAnalyzer):
    """Analyzer for Linux authentication logs"""

    task_type = 'authFiltered'

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

        # Get tenant customizations
        criteria = self.get_custom_criteria(DEFAULT_CRITERIA)
        exclusion_block = self.get_exclusion_block()

        return f"""You MUST respond with valid JSON only. No other text before or after.

Analyze these Linux authentication logs in context of previous findings and return a single JSON object with EXACTLY these fields:
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

New Authentication Log Data:
{json.dumps(current_data, indent=2)}

Format the analysis field with HTML using <p>, <ul>, <li> tags:
- Summary of key findings (including trend analysis)
- Security concerns and implications
- Recommendations and best practices

The score should reflect authentication security health (1-100) considering previous score of {previous['score'] if previous else 'N/A'}.

Remember: Respond with ONLY the JSON object, no markdown code blocks, no explanations."""

    def parse_response(self, response: str) -> Dict[str, Any]:
        """Parse AI response into structured format - JSON ONLY"""
        return self.parse_json_response(response)