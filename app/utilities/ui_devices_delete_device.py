# Filepath: app/utilities/ui_devices_delete_device.py
from app.models import Devices
from app.models import db
from app.utilities.app_logging_helper import log_with_route  # Custom logging utility
from app.utilities.ui_time_converter import unix_to_utc  # Time conversion utility
import logging

def delete_devices(deviceuuids):
    if not deviceuuids:
        raise ValueError('Device UUIDs are required')

    try:
        Devices.query.filter(Devices.deviceuuid.in_(deviceuuids)).delete(synchronize_session='fetch')
        db.session.commit()
        return {'message': 'Devices deleted successfully'}
    except Exception as e:
        db.session.rollback()
        log_with_route(logging.ERROR, f"Error deleting devices: {str(e)}")
        raise e
