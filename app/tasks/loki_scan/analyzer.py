# Filepath: app/tasks/loki_scan/analyzer.py
from typing import Dict, Any
import json

from app.tasks.base.analyzer import BaseAnalyzer

# Default criteria prompt (used when tenant hasn't customized)
DEFAULT_CRITERIA = """1. Clear indication whether the system appears COMPROMISED, SUSPICIOUS, or CLEAN based on the alerts.
2. Group related IOCs (file paths, registry keys, processes, network indicators) into coherent findings.
3. Distinguish between high-severity alerts (likely malware/IOC) and noisy or low-risk notices.
4. Prioritize findings that require immediate remediation.
5. Provide clear, concise remediation steps and follow-up checks for an MSP technician."""


class LokiScanAnalyzer(BaseAnalyzer):
    """Analyzer for Loki IOC / malware scan results."""

    task_type = "loki-scan"

    def create_prompt(self, current_data: Dict[str, Any], context: Dict[str, Any]) -> str:
        """Create analysis prompt with historical context and tenant customizations for Loki results."""
        previous = context["analyses"][0] if context.get("analyses") else None
        score_trend = context.get("score_trend", [])

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

        summary = current_data.get("summary", {})
        alerts = current_data.get("alerts", [])
        warnings = current_data.get("warnings", [])
        notices = current_data.get("notices", [])

        # Limit number of events we pass to the model (results are already trimmed, but be explicit)
        limited_events = {
            "alerts": alerts[:20],
            "warnings": warnings[:20],
            "notices": notices[:20],
        }

        # Get tenant customizations
        criteria = self.get_custom_criteria(DEFAULT_CRITERIA)
        exclusion_block = self.get_exclusion_block()

        return f"""You MUST respond with valid JSON only. No other text before or after.

Analyze the following Loki IOC / malware scan for a managed endpoint and return a single JSON object with EXACTLY these fields:
- analysis: Your detailed HTML analysis for display to users (use <p>, <ul>, <li>, <strong>, <em>, <h4>, <h5> tags)
- score: Health score from 1-100 (integer only, no quotes), where higher is better (fewer or less severe findings). Do NOT default to 85.

Analysis Criteria:
{criteria}

Previous Analysis Summary:
Last Health Score: {previous['score'] if previous else 'No previous score'}
Score Trend: {trend_text}

Previous Key Findings:
{previous['analysis'] if previous else 'No previous analysis'}

{exclusion_block}

Current Loki Scan Summary:
- Total alerts: {summary.get('total_alerts', 0)}
- Total warnings: {summary.get('total_warnings', 0)}
- Total notices: {summary.get('total_notices', 0)}

Sample Loki events (truncated to maximum 20 per level):
{json.dumps(limited_events, indent=2)}

Your response MUST be a single JSON object in this structure:
{{
    "analysis": "<p>HTML formatted summary...</p>",
    "score": 1
}}

IMPORTANT: The score MUST be a realistic integer from 1-100 for the provided scan results. Do NOT default to 85.

Do NOT include markdown code fences or any text before or after the JSON object.
"""

    def parse_response(self, response: str) -> Dict[str, Any]:
        """Parse AI response into structured format - JSON ONLY"""
        return self.parse_json_response(response)

