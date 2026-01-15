# Filepath: app/utilities/ui_devices_printers.py
import geoip2.database
from functools import wraps
from flask import current_app
from sqlalchemy import text
from app.models import db
from app.utilities.app_logging_helper import log_with_route
import logging

def fetch_printers_by_device(tenantuuid, deviceuuid):
    query = text("""
    SELECT deviceuuid, last_update, last_json, printer_name, printer_driver, printer_location, printer_status, printer_port
    FROM public.v_printerlist
    WHERE tenantuuid = :tenantuuid AND deviceuuid = :deviceuuid
    """)
    
    try:
        result = db.session.execute(query, {'tenantuuid': tenantuuid, 'deviceuuid': deviceuuid})
        column_names = result.keys()
        printers = [dict(zip(column_names, row)) for row in result.fetchall()]
        
        # Log the number of printers found using the custom logging function
        log_with_route(logging.DEBUG, f"Found {len(printers)} printers for device {deviceuuid} and tenant {tenantuuid}")
        
        return printers
    except Exception as e:
        log_with_route(logging.ERROR, f"Error fetching printers: {str(e)}", exc_info=True)
        return None
