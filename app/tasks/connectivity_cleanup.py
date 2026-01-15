# Filepath: app/tasks/connectivity_cleanup.py
"""
Periodic task to transition stale device connections to offline status.
Runs every 5 minutes to check for devices that haven't sent heartbeats.
"""

from app.celery_app import celery
from app.models.devices import DeviceConnectivity
from app.models import db
from app.utilities.app_logging_helper import log_with_route
import logging
import time


@celery.task(name='tasks.cleanup_stale_connections')
def cleanup_stale_connections():
    """
    Transition devices from online to offline when heartbeat exceeds threshold.
    
    Logic:
    - If is_online=True AND last_heartbeat > 10 minutes old: set is_online=False
    - This ensures devices don't stay in "Stale" status forever
    """
    try:
        current_time = int(time.time())
        offline_threshold = current_time - 600  # 10 minutes
        
        # Find devices marked as online but with old heartbeats
        stale_devices = DeviceConnectivity.query.filter(
            DeviceConnectivity.is_online == True,
            DeviceConnectivity.last_heartbeat < offline_threshold
        ).all()
        
        updated_count = 0
        for connectivity in stale_devices:
            connectivity.is_online = False
            connectivity.last_online_change = current_time
            updated_count += 1
            
            log_with_route(
                logging.INFO,
                f"Transitioned device {connectivity.deviceuuid} from stale to offline "
                f"(last heartbeat: {current_time - connectivity.last_heartbeat}s ago)"
            )
        
        if updated_count > 0:
            db.session.commit()
            log_with_route(
                logging.INFO,
                f"Connectivity cleanup: marked {updated_count} stale devices as offline"
            )
        
        return {
            'success': True,
            'updated': updated_count,
            'timestamp': current_time
        }
        
    except Exception as e:
        db.session.rollback()
        log_with_route(
            logging.ERROR,
            f"Error in connectivity cleanup task: {str(e)}"
        )
        return {
            'success': False,
            'error': str(e),
            'timestamp': int(time.time())
        }
