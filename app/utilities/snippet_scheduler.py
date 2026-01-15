# Filepath: app/utilities/snippet_scheduler.py
"""
Snippet scheduling utilities for Wegweiser
"""

import logging
import time
import uuid as uuid_lib
from sqlalchemy import and_
from app.models import db, Snippets, SnippetsSchedule
from sqlalchemy.sql.expression import true, false

logger = logging.getLogger(__name__)


def recStringToSeconds(recString):
    """Convert recurrence string to seconds

    Args:
        recString: "0" for one-time, or "1h", "30m", "1d" for recurring

    Returns:
        tuple: (recurrence_multiplier, interval_value)
    """
    if recString.isdigit():
        if int(recString) == 0:
            recurrence = 0
            interval = 0
    else:
        units = {
            's': 1,
            'm': 60,
            'h': 3600,
            'd': 86400
        }
        try:
            interval = int(''.join(filter(str.isdigit, recString)))
            unit = ''.join(filter(str.isalpha, recString))
        except ValueError:
            raise ValueError(f"Invalid time format: {recString}")
        if unit not in units:
            raise ValueError(f"Unknown time unit: {unit}")
        recurrence = units[unit]
    return (recurrence, interval)


def getEpochTime(startTime):
    """Convert start time to epoch

    Args:
        startTime: "now" or epoch timestamp

    Returns:
        int: epoch timestamp
    """
    if startTime == "now" or not startTime:
        return int(time.time())
    else:
        try:
            return int(startTime)
        except (ValueError, TypeError):
            return int(time.time())


def upsertSnippetSchedule(deviceuuid, snippetname, parameters=None):
    """Schedule a snippet for execution on a device

    Args:
        deviceuuid: Device UUID (string)
        snippetname: Name of snippet to schedule (e.g., 'AgentUpdate.py')
        parameters: Optional dict of parameters to pass to snippet (NOT YET IMPLEMENTED)

    Returns:
        bool: True if successful, False otherwise
    """
    try:
        # Look up snippet by name
        snippet = Snippets.query.filter_by(snippetname=snippetname).first()
        if not snippet:
            logger.error(f"Snippet not found: {snippetname}")
            return False

        snippetUuid = str(snippet.snippetuuid)

        # For agent updates, we want one-time immediate execution
        recString = "0"  # One-time execution
        startTime = "now"  # Immediate execution

        # Check for existing schedule
        existing_row = SnippetsSchedule.query.filter(
            and_(
                SnippetsSchedule.snippetuuid == snippetUuid,
                SnippetsSchedule.deviceuuid == deviceuuid
            )
        ).first()

        if existing_row:
            logger.debug(f'Found existing schedule for snippet: {snippetname} on device: {deviceuuid}')
            db.session.delete(existing_row)
            db.session.commit()

        # Convert recurrence and time
        recurrence, interval = recStringToSeconds(recString)
        startTimeEpoch = getEpochTime(startTime)

        # Create new schedule
        newSchedule = SnippetsSchedule(
            scheduleuuid=uuid_lib.uuid4(),
            snippetuuid=snippetUuid,
            deviceuuid=deviceuuid,
            recurrence=recurrence,
            interval=interval,
            nextexecution=startTimeEpoch,
            enabled=True,
            parameters=parameters  # Store parameters as JSON
        )
        db.session.add(newSchedule)
        db.session.commit()

        if parameters:
            logger.info(f"Scheduled snippet {snippetname} for device {deviceuuid} with parameters")
        else:
            logger.info(f"Scheduled snippet {snippetname} for device {deviceuuid}")

        return True

    except Exception as e:
        logger.error(f"Failed to schedule snippet {snippetname}: {e}")
        db.session.rollback()
        return False
