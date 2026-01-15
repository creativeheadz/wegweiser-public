# Filepath: app/tasks/macos_logs/analyzer.py
from app.tasks.base.analyzer import BaseAnalyzer
import json
import re
import bleach
from typing import Dict, Any
from datetime import datetime, timedelta

import os

# Default criteria prompt (used when tenant hasn't customized)
DEFAULT_CRITERIA = """1. Error Pattern Analysis: Examine error logs for critical system issues.
2. Security Event Assessment: Analyze security-related events and threats.
3. Crash Report Evaluation: Review application and system crashes.
4. Trend Identification: Identify patterns and recurring issues.
5. System Stability: Assess overall system health and stability."""


class MacOSLogsAnalyzer(BaseAnalyzer):
    """Analyzer for macOS System Log Health Assessment"""

    task_type = 'macos-log-health'

    def should_run(self, device_uuid: str, context: Dict[str, Any]) -> bool:
        """Check if this analysis should run (when new log data is available)"""
        from app.models import DeviceMetadata
        
        # Check if we have macOS log metadata
        log_types = ['macos-errors-filtered', 'macos-security-filtered', 'macos-crashes-filtered']
        
        # Get latest log metadata
        latest_logs = {}
        for log_type in log_types:
            metadata = DeviceMetadata.query.filter_by(
                deviceuuid=device_uuid,
                metalogos_type=log_type
            ).order_by(DeviceMetadata.created_at.desc()).first()
            
            if metadata:
                latest_logs[log_type] = metadata.created_at
        
        if not latest_logs:
            # No log data available
            return False
        
        # Check if we have new log data since last analysis
        if context.get('analyses'):
            last_analysis = context['analyses'][0]
            last_analysis_date = last_analysis.get('created_at')
            
            if last_analysis_date:
                # Check if any log data is newer than last analysis
                for log_type, log_date in latest_logs.items():
                    if log_date > last_analysis_date:
                        return True
                return False
        
        return True

    def create_prompt(self, current_data: Dict[str, Any], context: Dict[str, Any]) -> str:
        """Create analysis prompt for macOS log health assessment with tenant customizations"""
        
        # Get previous analysis for trend analysis
        previous = context['analyses'][0] if context['analyses'] else None
        score_trend = context.get('score_trend', [])
        
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

        previous_text = ""
        if previous:
            previous_text = f"""
PREVIOUS ANALYSIS:
Last Score: {previous.get('score', 'Unknown')}
Score Trend: {trend_text}
Previous Key Issues: {previous.get('analysis', 'No previous analysis')[:300]}...
"""

        # Get tenant customizations
        criteria = self.get_custom_criteria(DEFAULT_CRITERIA)
        exclusion_block = self.get_exclusion_block()

        with open(os.path.join(os.path.dirname(__file__), 'prompts', 'base.prompt'), 'r') as f:
            base_prompt = f.read()

        prompt = base_prompt.format(
            log_data=json.dumps(current_data, indent=2),
            previous_analysis=previous_text,
            criteria=criteria,
            exclusion_block=exclusion_block,
            analysis_date=datetime.now().isoformat()
        )

        return prompt

    def parse_response(self, response: str) -> Dict[str, Any]:
        """Parse AI response into structured format - JSON ONLY"""
        result = self.parse_json_response(response)

        # Add metadata for tracking
        result['metadata'] = {
            'analysis_date': datetime.now().isoformat(),
            'log_categories_analyzed': ['errors', 'security', 'crashes']
        }

        return result

    def get_data_sources(self, device_uuid: str) -> Dict[str, Any]:
        """Get required data sources for analysis"""
        from app.models import DeviceMetadata
        
        log_types = ['macos-errors-filtered', 'macos-security-filtered', 'macos-crashes-filtered']
        data = {}
        
        for log_type in log_types:
            metadata = DeviceMetadata.query.filter_by(
                deviceuuid=device_uuid,
                metalogos_type=log_type
            ).order_by(DeviceMetadata.created_at.desc()).first()
            
            if metadata and metadata.metalogos:
                # Extract category name from log_type
                category = log_type.replace('macos-', '').replace('-filtered', '')
                data[category] = metadata.metalogos
                
        return data
