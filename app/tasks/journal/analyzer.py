# Filepath: app/tasks/journal/analyzer.py
from app.tasks.base.analyzer import BaseAnalyzer
import json
from typing import Dict, Any

# Default criteria prompt (used when tenant hasn't customized)
DEFAULT_CRITERIA = """1. Service management events: Systemd service failures, restarts, and state changes.
2. Authentication events: Login attempts, session management, and PAM events.
3. Boot and shutdown analysis: Startup sequence issues and shutdown events.
4. Hardware events: Device detection, driver loading, and hardware errors.
5. Network events: Interface changes, connection issues, and DNS problems.
6. Application events: Key application logs and error patterns.
7. Security events: SELinux/AppArmor denials and security-relevant activities.
8. Resource events: Memory, CPU, and disk-related warnings."""


class JournalAnalyzer(BaseAnalyzer):
    """Analyzer for Linux journal logs"""

    task_type = 'journalFiltered'

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

Analyze these Linux Journal events in context of previous findings and return a single JSON object with EXACTLY these fields:
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

New Journal Data to Analyze:
{json.dumps(current_data, indent=2)}

Format the analysis field with HTML using <p>, <ul>, <li> tags:
- Summary (including trend analysis)
- Critical findings (new and ongoing)
- Recommendations

The score should reflect system health based on journal events (1-100) considering previous score of {previous['score'] if previous else 'N/A'}.

Remember: Respond with ONLY the JSON object, no markdown code blocks, no explanations."""

    def parse_response(self, response: str) -> Dict[str, Any]:
        """Parse AI response into structured format - JSON ONLY"""
        return self.parse_json_response(response)