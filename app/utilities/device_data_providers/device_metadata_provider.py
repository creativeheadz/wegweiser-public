# Filepath: app/utilities/device_data_providers/device_metadata_provider.py
"""
Device Metadata Provider

Handles fetching device metadata including analyses, widgets,
and processing status information.
"""

from typing import Dict, Any, Optional, List
from datetime import datetime
import json
from sqlalchemy import desc
from app.models import db, DeviceMetadata
from .base_provider import BaseDeviceDataProvider


class DeviceMetadataProvider(BaseDeviceDataProvider):
    """
    Provider for device metadata including AI analyses, widgets,
    and processing status information.
    """
    
    def get_component_name(self) -> str:
        return "metadata"
    
    def get_data(self) -> Optional[Dict[str, Any]]:
        """
        Fetch device metadata information using ORM.
        
        Returns:
            Dictionary containing metadata organized by type
        """
        if not self.validate_uuids():
            return None
        
        try:
            # Get all metadata for the device
            metadata_records = db.session.query(DeviceMetadata)\
                .filter(DeviceMetadata.deviceuuid == self.deviceuuid)\
                .order_by(desc(DeviceMetadata.created_at))\
                .all()
            
            if not metadata_records:
                self.log_debug("No metadata found")
                return None
            
            # Organize metadata by type
            metadata_data = {
                'analyses': self._get_analyses_data(metadata_records),
                'widgets': self._get_widgets_data(metadata_records),
                'event_logs': self._get_event_logs_data(metadata_records),
                'regular_analyses': self._get_regular_analyses_data(metadata_records),
            }
            
            self.log_debug(f"Successfully fetched metadata for {len(metadata_records)} records")
            return metadata_data
            
        except Exception as e:
            self.log_error(f"Error fetching metadata: {str(e)}", exc_info=True)
            return None
    
    def _get_analyses_data(self, metadata_records: List[DeviceMetadata]) -> Dict[str, Any]:
        """
        Extract and organize analysis data from metadata records.
        
        Args:
            metadata_records: List of DeviceMetadata objects
            
        Returns:
            Dictionary containing analysis data organized by type
        """
        analyses = {}
        
        # Get latest processed analysis for each type
        processed_analyses = {}
        for record in metadata_records:
            if (record.processing_status == 'processed' and 
                record.metalogos_type not in processed_analyses):
                processed_analyses[record.metalogos_type] = {
                    'metalogos_type': record.metalogos_type,
                    'ai_analysis': record.ai_analysis,
                    'score': record.score,
                    'analyzed_at': record.analyzed_at,
                    'created_at': record.created_at,
                    'processing_status': record.processing_status,
                }
        
        analyses['latest_processed'] = processed_analyses
        return analyses
    
    def _get_widgets_data(self, metadata_records: List[DeviceMetadata]) -> List[Dict[str, Any]]:
        """
        Extract widget data from metadata records.
        
        Args:
            metadata_records: List of DeviceMetadata objects
            
        Returns:
            List of widget data dictionaries
        """
        widgets = []
        
        for record in metadata_records:
            if record.metalogos_type.startswith('widget_'):
                widgets.append({
                    'metalogos_type': record.metalogos_type,
                    'metalogos': record.metalogos,
                    'created_at': record.created_at,
                    'processing_status': record.processing_status,
                })
        
        return widgets
    
    def _get_event_logs_data(self, metadata_records: List[DeviceMetadata]) -> Dict[str, Any]:
        """
        Extract and organize event log data from metadata records.
        
        Args:
            metadata_records: List of DeviceMetadata objects
            
        Returns:
            Dictionary containing event log data organized by type
        """
        event_types = [
            'eventsFiltered-Application',
            'eventsFiltered-Security', 
            'eventsFiltered-System',
            'journalFiltered'
        ]
        
        event_logs = {}
        
        for event_type in event_types:
            # Get latest processed record for this event type
            latest_processed = None
            pending_count = 0
            consolidated_count = 0
            
            for record in metadata_records:
                if record.metalogos_type == event_type:
                    if record.processing_status == 'processed' and latest_processed is None:
                        latest_processed = record
                    elif record.processing_status == 'pending':
                        pending_count += 1
                    elif record.processing_status == 'consolidated':
                        consolidated_count += 1
            
            if latest_processed:
                event_logs[event_type] = {
                    'ai_analysis': latest_processed.ai_analysis,
                    'score': latest_processed.score,
                    'metalogos_type': latest_processed.metalogos_type,
                    'processed_at': datetime.fromtimestamp(latest_processed.analyzed_at) if latest_processed.analyzed_at else None,
                    'event_summary': self._get_event_summary(latest_processed.metalogos),
                    'processing_status': {
                        'pending_count': pending_count,
                        'has_backlog': pending_count > 0
                    },
                    'consolidation_info': {
                        'consolidated_count': consolidated_count,
                        'has_history': consolidated_count > 0
                    }
                }
        
        return event_logs
    
    def _get_regular_analyses_data(self, metadata_records: List[DeviceMetadata]) -> Dict[str, Any]:
        """
        Extract regular (non-event) analysis data from metadata records.
        
        Args:
            metadata_records: List of DeviceMetadata objects
            
        Returns:
            Dictionary containing regular analysis data
        """
        event_types = [
            'eventsFiltered-Application',
            'eventsFiltered-Security',
            'eventsFiltered-System', 
            'journalFiltered'
        ]
        
        regular_analyses = {}
        
        # Group by metalogos_type
        type_groups = {}
        for record in metadata_records:
            if (record.metalogos_type not in event_types and 
                not record.metalogos_type.startswith('widget_')):
                
                if record.metalogos_type not in type_groups:
                    type_groups[record.metalogos_type] = []
                type_groups[record.metalogos_type].append(record)
        
        # Get latest processed and pending for each type
        for metalogos_type, records in type_groups.items():
            last_processed = None
            next_pending = None
            
            for record in records:
                if record.processing_status == 'processed':
                    if last_processed is None or record.created_at > last_processed.created_at:
                        last_processed = record
                elif record.processing_status == 'pending':
                    if next_pending is None or record.created_at > next_pending.created_at:
                        next_pending = record
            
            regular_analyses[metalogos_type] = {
                'last_processed': datetime.fromtimestamp(last_processed.created_at) if last_processed else None,
                'next_pending': datetime.fromtimestamp(next_pending.created_at) if next_pending else None,
            }
        
        return regular_analyses
    
    def _get_event_summary(self, metalogos: Any) -> Dict[str, Any]:
        """
        Extract key summary information from metalogos.
        
        Args:
            metalogos: Metalogos data (JSON or string)
            
        Returns:
            Dictionary containing event summary
        """
        try:
            if isinstance(metalogos, str):
                metalogos_data = json.loads(metalogos)
            else:
                metalogos_data = metalogos
            
            if not isinstance(metalogos_data, dict) or 'Sources' not in metalogos_data:
                return {'error_count': 0, 'warning_count': 0, 'critical_count': 0, 'top_events': []}
            
            top_events = metalogos_data.get('Sources', {}).get('TopEvents', [])
            
            return {
                'error_count': sum(1 for event in top_events if event.get('Level') == 'ERROR'),
                'warning_count': sum(1 for event in top_events if event.get('Level') == 'WARNING'),
                'critical_count': sum(1 for event in top_events if event.get('Level') == 'CRITICAL'),
                'top_events': [
                    {**event, 'Level': event.get('Level', 'N/A')}
                    for event in top_events[:50]
                ]
            }
        except (json.JSONDecodeError, TypeError, KeyError) as e:
            self.log_error(f"Error parsing event summary: {str(e)}")
            return {'error_count': 0, 'warning_count': 0, 'critical_count': 0, 'top_events': []}
