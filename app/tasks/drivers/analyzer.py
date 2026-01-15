# Filepath: app/tasks/drivers/analyzer.py
from app.tasks.base.analyzer import BaseAnalyzer
import json
import re
import bleach
from typing import Dict, Any
from datetime import datetime

import time  # Add this import
from app.models import db, DeviceDrivers, DeviceMetadata
from collections import defaultdict
import os
import logging
from sqlalchemy.exc import NoSuchColumnError

# Default criteria prompt (used when tenant hasn't customized)
DEFAULT_CRITERIA = """1. Detailed evaluation of driver versions, ages, and compatibility with current Windows versions.
2. Assessment of critical system drivers including graphics, network, storage, and chipset drivers.
3. Identification of outdated, unsigned, or potentially problematic drivers.
4. Analysis of driver conflicts or missing drivers.
5. Evaluation of driver update availability and manufacturer support status.
6. Assessment of driver digital signatures and WHQL certification status.
7. Recommendations for driver maintenance and update strategies."""


class DriverAnalyzer(BaseAnalyzer):
    """Analyzer for Windows Device Drivers"""

    task_type = 'windrivers'

    def __init__(self, device_id):
        """Initialize with just device_id and create metadata record"""
        self.device_id = device_id
        self.metadata_id = None
        
        # Add config initialization for billing
        from flask import current_app
        self._config = current_app.config
        
        # Create new metadata record for this analysis
        metadata = DeviceMetadata(
            deviceuuid=device_id,
            metalogos_type=self.task_type,
            metalogos={},
            processing_status='processing'
        )
        db.session.add(metadata)
        db.session.commit()
        self.metadata_id = metadata.metadatauuid

    def validate(self) -> bool:
        """Validate that this device is a Windows device before running driver analysis"""
        from app.models import DeviceStatus
        try:
            device_status = DeviceStatus.query.filter_by(deviceuuid=self.device_id).first()
            if not device_status:
                logging.warning(f"No device status found for device {self.device_id}")
                return False

            if not device_status.agent_platform.startswith('Windows'):
                logging.warning(f"Skipping driver analysis for non-Windows device {self.device_id} (platform: {device_status.agent_platform})")
                return False

            return True
        except Exception as e:
            logging.error(f"Error validating device platform for {self.device_id}: {str(e)}")
            return False

    def get_driver_summary(self) -> Dict[str, Any]:
        """Gather and summarize driver data"""
        try:
            drivers = DeviceDrivers.query.filter_by(deviceuuid=self.device_id).all()
        except NoSuchColumnError as e:
            logging.error(f"Database error: {str(e)}")
            return {
                "driver_types": {},
                "total_drivers": 0,
                "outdated_count": 0,
            }

        summary = defaultdict(list)
        total_drivers = len(drivers)
        outdated_count = 0
        two_years_ago = datetime.now().replace(year=datetime.now().year - 2)

        for driver in drivers:
            driver_type = driver.driver_type or "Unknown"
            if driver.driver_date:
                try:
                    date_obj = datetime.fromtimestamp(int(driver.driver_date))
                    if date_obj < two_years_ago:
                        outdated_count += 1
                except (ValueError, TypeError):
                    pass

            if len(summary[driver_type]) < 500:  # Limit to 50 drivers per type
                summary[driver_type].append({
                    "name": driver.driver_name,
                    "version": driver.driver_version,
                    "date": datetime.fromtimestamp(int(driver.driver_date)).strftime('%Y-%m-%d') if driver.driver_date else "Unknown",
                })

        return {
            "driver_types": {k: v for k, v in summary.items() if v},
            "total_drivers": total_drivers,
            "outdated_count": outdated_count,
        }

    def create_prompt(self, current_data: Dict[str, Any], context: Dict[str, Any]) -> str:
        """Create analysis prompt with historical context and tenant customizations"""
        with open(os.path.join(os.path.dirname(__file__), 'prompts', 'base.prompt'), 'r') as f:
            base_prompt = f.read()

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

        prompt = base_prompt.format(
            driver_data=json.dumps(current_data, indent=2)
        )

        return f"""You MUST respond with valid JSON only. No other text before or after.

Analyze the driver data and return a single JSON object with EXACTLY these fields:
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

    def analyze(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Override analyze to handle driver data gathering"""
        # First gather and summarize driver data
        driver_summary = self.get_driver_summary()
        
        # Then proceed with normal analysis
        return super().analyze(driver_summary)

    def perform_analysis(self, data: Dict[str, Any] = None) -> None:
        """Perform the analysis on the driver data"""
        # Validate platform before proceeding
        if not self.validate():
            # Mark metadata as failed for non-Windows devices
            metadata = DeviceMetadata.query.get(self.metadata_id)
            if metadata:
                metadata.processing_status = 'failed'
                metadata.ai_analysis = 'Driver analysis not applicable for non-Windows devices'
                metadata.score = '0'
                metadata.analyzed_at = int(time.time())
                db.session.commit()
            return

        result = self.analyze({})

        # Update metadata with results
        metadata = DeviceMetadata.query.get(self.metadata_id)
        if metadata:
            metadata.ai_analysis = result['analysis']
            metadata.score = str(result['score'])
            metadata.analyzed_at = int(time.time())
            metadata.processing_status = 'processed'
            db.session.commit()