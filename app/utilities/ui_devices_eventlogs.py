# Filepath: app/utilities/ui_devices_eventlogs.py
import geoip2.database
from functools import wraps
from flask import current_app, redirect, url_for, session
from sqlalchemy import text
from app.models import db



def fetch_event_logs_by_device(tenantuuid):
    query = text("""
    SELECT devicename, metalogos_type, ai_analysis, created_at, to_timestamp
    FROM public.v_latestanalysis
    WHERE tenantuuid = :tenantuuid
    AND metalogos_type IN ('eventsFiltered-Application', 'eventsFiltered-Security', 'eventsFiltered-System')
    ORDER BY devicename, metalogos_type
    """)
    
    try:
        result = db.session.execute(query, {'tenantuuid': tenantuuid})
        column_names = result.keys()
        eventlogs = [dict(zip(column_names, row)) for row in result.fetchall()]
        
        eventlogs_by_device = {}
        for log in eventlogs:
            devicename = log['devicename']
            if devicename not in eventlogs_by_device:
                eventlogs_by_device[devicename] = {}
            eventlogs_by_device[devicename][log['metalogos_type']] = {
                'ai_analysis': log['ai_analysis'],
                'created_at': log['to_timestamp']
            }

        return eventlogs_by_device
    except Exception as e:
        current_app.logger.error(f"Error fetching event logs: {str(e)}", exc_info=True)
        return {}