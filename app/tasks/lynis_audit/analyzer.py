# Filepath: app/tasks/lynis_audit/analyzer.py
from app.tasks.base.analyzer import BaseAnalyzer
import json
import re
import bleach
from typing import Dict, Any
from datetime import datetime

# Default criteria prompt (used when tenant hasn't customized)
DEFAULT_CRITERIA = """1. Executive Summary - High-level overview of security posture and critical findings.
2. Security Posture Overview - Hardening Index interpretation, Security Grade (A-F), Risk Level.
3. Critical Security Findings - Issues requiring immediate attention with remediation steps.
4. High-Priority Warnings - Important findings with business impact.
5. System Hardening Recommendations - Quick Wins, Standard Hardening, Advanced Hardening.
6. Compliance Assessment - ISO27001, PCI-DSS, HIPAA, CIS Benchmarks.
7. Vulnerability Summary by category (Authentication, Network, Software, File System, Audit, Kernel).
8. MSP Action Plan - Step-by-step guidance with specific commands.
9. Monitoring & Maintenance Strategy - Key metrics, frequency, thresholds."""


class LynisAuditAnalyzer(BaseAnalyzer):
    """Analyzer for Lynis security audit reports"""

    task_type = 'lynis-audit'

    def create_prompt(self, current_data: Dict[str, Any], context: Dict[str, Any]) -> str:
        """Create analysis prompt with historical context and tenant customizations"""
        previous = context['analyses'][0] if context['analyses'] else None
        score_trend = context['score_trend']
        trend_text = "No previous scores available"

        if score_trend:
            if len(score_trend) > 1:
                if score_trend[0] > score_trend[-1]:
                    trend_text = f"Security posture improving: {score_trend[::-1]}"
                elif score_trend[0] < score_trend[-1]:
                    trend_text = f"Security posture declining: {score_trend[::-1]}"
                else:
                    trend_text = f"Security posture stable: {score_trend[::-1]}"
            else:
                trend_text = f"Single previous audit: {score_trend[0]}"

        # Extract key context information for the prompt
        lynis_data = json.dumps(current_data, indent=2)

        # Try to extract hardening index if available
        hardening_index = "N/A"
        if isinstance(current_data, dict):
            if 'hardening_index' in current_data:
                hardening_index = current_data['hardening_index']
            elif 'findings' in current_data and 'hardening_index' in current_data.get('findings', {}):
                hardening_index = current_data['findings']['hardening_index']

        previous_score = previous['score'] if previous else 'N/A'
        previous_analysis = previous['analysis'] if previous else 'No previous analysis'

        # Get tenant customizations
        criteria = self.get_custom_criteria(DEFAULT_CRITERIA)
        exclusion_block = self.get_exclusion_block()

        return f"""You MUST respond with valid JSON only. No other text before or after.

Analyze this Lynis security audit report in context of previous findings and return your response in this exact JSON format:
{{
    "analysis": "HTML formatted analysis with <p>, <ul>, <li>, <strong>, <em>, <h4>, <h5>, <br> tags",
    "score": 75
}}

Where:
- analysis: Your detailed HTML analysis for display to MSP users (use semantic HTML tags only)
- score: Security health score from 1-100 (integer only)

Analysis Criteria:
{criteria}

Previous Audit Summary:
Last Security Score: {previous_score}
Score Trend: {trend_text}

Previous Key Findings:
{previous_analysis}

{exclusion_block}

Current Lynis Audit Data:
{lynis_data}

Provide a comprehensive security assessment covering the criteria above.

Format your analysis with HTML using <p>, <h4>, <h5>, <ul>, <li>, <strong>, <em>, <br> tags.
Be specific and actionable. Provide exact commands for remediation where possible.
Think like an MSP managing multiple clients' systems.

The score should reflect overall security posture (1-100) considering the previous score of {previous_score}.

Remember: Respond with ONLY the JSON object, no markdown code blocks, no explanations."""

    def parse_response(self, response: str) -> Dict[str, Any]:
        """Parse AI response into structured format - JSON ONLY"""
        return self.parse_json_response(response)
