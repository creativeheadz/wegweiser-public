# Filepath: app/tasks/crashes/analyzer.py
from app.tasks.base.analyzer import BaseAnalyzer
import json
import re
import bleach
from typing import Dict, Any, List
from datetime import datetime

import os
from .utils import aggregate_crash_logs

# Default criteria prompt (used when tenant hasn't customized)
DEFAULT_CRITERIA = """1. Crash frequency analysis: Identify patterns in crash occurrences and severity.
2. Application stability assessment: Evaluate which applications are most problematic.
3. System impact evaluation: Assess crashes that affect system stability vs application-only.
4. Root cause indicators: Identify common factors like memory issues, driver conflicts.
5. Crash timing patterns: Analyze when crashes occur (startup, specific operations, etc.).
6. Critical vs minor crash categorization: Prioritize crashes requiring immediate attention.
7. Recovery and remediation recommendations: Specific steps to address crash issues.
8. Trend analysis: Compare crash patterns with previous analysis periods."""


class CrashAnalyzer(BaseAnalyzer):
    """Analyzer for Windows Application Crashes"""

    task_type = 'msinfo-RecentAppCrashes'

    def create_prompt(self, current_data: Dict[str, Any], context: Dict[str, Any]) -> str:
        """Create analysis prompt with historical context and tenant customizations"""
        # Process crash data
        aggregated_logs = aggregate_crash_logs([{'metalogos': current_data}])
        log_summary = "\n".join([f"{app}: {count} crashes" for app, count in aggregated_logs])

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
            crash_data=log_summary
        )

        return f"""You MUST respond with valid JSON only. No other text before or after.

Analyze the crash data and return a single JSON object with EXACTLY these fields:
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