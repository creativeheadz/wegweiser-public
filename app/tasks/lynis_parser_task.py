# Filepath: app/tasks/lynis_parser_task.py
"""
Celery task for parsing Lynis security audit results.

Unlike other analysis tasks, Lynis audits are NOT sent to AI.
Lynis already provides comprehensive analysis and recommendations.
This task simply parses the JSON and generates HTML for display.

Zero wegcoins cost - no AI involved.
"""

from app import celery, db
from app.models import DeviceMetadata, Devices
from app.utilities.lynis_parser import LynisResultParser
import logging
from datetime import datetime
from sqlalchemy.exc import SQLAlchemyError

logger = logging.getLogger(__name__)


@celery.task(name='tasks.parse_lynis_audit')
def parse_lynis_audit(metadata_id: str):
    """
    Parse Lynis audit results and update DeviceMetadata.

    Args:
        metadata_id: UUID of DeviceMetadata entry containing Lynis JSON

    Returns:
        dict: Status and score information

    Raises:
        No exceptions - logs errors and updates processing_status to 'error'
    """
    try:
        logger.info(f"Starting Lynis audit parsing for metadata {metadata_id}")

        # Load metadata entry
        metadata = db.session.query(DeviceMetadata).get(metadata_id)
        if not metadata:
            logger.error(f"DeviceMetadata not found: {metadata_id}")
            return {'error': 'Metadata not found', 'metadata_id': str(metadata_id)}

        # Verify metalogos_type
        if metadata.metalogos_type != 'lynis_audit':
            logger.error(f"Invalid metalogos_type: {metadata.metalogos_type} (expected lynis_audit)")
            return {'error': 'Invalid metadata type', 'metadata_id': str(metadata_id)}

        # Load device for health score recalculation
        device = db.session.query(Devices).get(metadata.deviceuuid)
        if not device:
            logger.error(f"Device not found: {metadata.deviceuuid}")
            return {'error': 'Device not found', 'metadata_id': str(metadata_id)}

        # Initialize parser with JSON data from metadata.metalogos
        parser = LynisResultParser(json_data=metadata.metalogos)

        # Extract summary and score
        summary = parser.get_summary()
        hardening_index = summary.get('hardening_index')

        if hardening_index is None:
            logger.error(f"No hardening_index in Lynis data for {metadata_id}")
            metadata.processing_status = 'error'
            metadata.ai_analysis = '<p>Error: No hardening index found in Lynis results</p>'
            db.session.commit()
            return {'error': 'No hardening index', 'metadata_id': str(metadata_id)}

        # Generate HTML report (no AI involved)
        html_report = parser.get_html_report()

        # Update metadata with parsed results
        metadata.score = hardening_index  # 1-100 scale (0-100 from Lynis, but we use max(1, score))
        metadata.weight = '1.0'  # Equal weight with other analyses
        metadata.ai_analysis = html_report  # Pre-rendered HTML (not from AI)
        metadata.processing_status = 'processed'
        metadata.analyzed_at = int(datetime.utcnow().timestamp())

        db.session.commit()

        logger.info(f"Lynis audit parsed successfully - Score: {hardening_index}, Device: {device.devicename}")

        # Trigger cascading health score recalculation (device → group → org → tenant)
        try:
            from app.utilities.sys_function_generate_healthscores import update_cascading_health_scores_task
            update_cascading_health_scores_task.delay()
            logger.info("Queued cascading health score update task")
        except Exception as e:
            logger.error(f"Failed to queue cascading health score update: {str(e)}")
            # Don't fail the task if health score update queueing fails

        return {
            'status': 'processed',
            'score': hardening_index,
            'metadata_id': str(metadata_id),
            'device_id': str(metadata.deviceuuid),
            'device_name': device.devicename,
            'warnings_count': summary.get('warnings_count', 0),
            'suggestions_count': summary.get('suggestions_count', 0)
        }

    except SQLAlchemyError as e:
        logger.error(f"Database error parsing Lynis audit {metadata_id}: {str(e)}")
        db.session.rollback()

        # Try to mark as error if possible
        try:
            metadata = db.session.query(DeviceMetadata).get(metadata_id)
            if metadata:
                metadata.processing_status = 'error'
                metadata.ai_analysis = f'<p>Error processing Lynis audit: Database error</p>'
                db.session.commit()
        except Exception:
            pass

        return {'error': 'Database error', 'metadata_id': str(metadata_id)}

    except Exception as e:
        logger.error(f"Unexpected error parsing Lynis audit {metadata_id}: {str(e)}", exc_info=True)
        db.session.rollback()

        # Try to mark as error if possible
        try:
            metadata = db.session.query(DeviceMetadata).get(metadata_id)
            if metadata:
                metadata.processing_status = 'error'
                metadata.ai_analysis = f'<p>Error processing Lynis audit: {str(e)}</p>'
                db.session.commit()
        except Exception:
            pass

        return {'error': str(e), 'metadata_id': str(metadata_id)}
