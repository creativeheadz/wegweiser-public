# Filepath: app/tasks/hardware/analyzer.py
from app.tasks.base.analyzer import BaseAnalyzer
import json
import re
import bleach
from typing import Dict, Any
from datetime import datetime

import os

# Default criteria prompt (used when tenant hasn't customized)
DEFAULT_CRITERIA = """1. Processor analysis: CPU model, generation, core count, clock speeds, and performance tier assessment.
2. Memory evaluation: RAM capacity, speed, configuration, and upgrade potential.
3. Storage analysis: Drive types (SSD/HDD), capacity, health indicators, and performance characteristics.
4. Graphics assessment: GPU model, VRAM, driver version, and capability evaluation.
5. System board analysis: Motherboard model, chipset, BIOS version, and expansion capabilities.
6. Peripheral assessment: Connected devices, USB controllers, and I/O capabilities.
7. Thermal and power analysis: Cooling system status and power supply adequacy.
8. Hardware lifecycle assessment: End-of-life indicators and upgrade recommendations."""


class HardwareAnalyzer(BaseAnalyzer):
    """Analyzer for Windows System Hardware Configuration"""

    task_type = 'msinfo-SystemHardwareConfig'

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
            hardware_data=json.dumps(current_data, indent=2)
        )

        return f"""You MUST respond with valid JSON only. No other text before or after.

Analyze the hardware data and return a single JSON object with EXACTLY these fields:
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