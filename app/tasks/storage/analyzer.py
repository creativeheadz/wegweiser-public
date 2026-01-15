# Filepath: app/tasks/storage/analyzer.py
from app.tasks.base.analyzer import BaseAnalyzer
import json
import re
import bleach
from typing import Dict, Any
from datetime import datetime

import os

# Default criteria prompt (used when tenant hasn't customized)
DEFAULT_CRITERIA = """1. Disk health assessment: SMART status, error rates, and predicted lifespan indicators.
2. Storage capacity analysis: Total capacity, used space, free space, and growth trends.
3. Performance evaluation: Read/write speeds, I/O patterns, and throughput characteristics.
4. Partition analysis: Partition layout, file systems, and allocation efficiency.
5. Drive type assessment: SSD vs HDD characteristics and performance implications.
6. RAID and redundancy evaluation: Array status, rebuild status, and fault tolerance.
7. Backup and recovery readiness: Shadow copy status and recovery point availability.
8. Storage optimization recommendations: Cleanup opportunities and upgrade suggestions."""


class StorageAnalyzer(BaseAnalyzer):
    """Analyzer for Windows Storage Information"""

    task_type = 'msinfo-StorageInfo'

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
            storage_data=json.dumps(current_data, indent=2)
        )

        return f"""You MUST respond with valid JSON only. No other text before or after.

Analyze the storage data and return a single JSON object with EXACTLY these fields:
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