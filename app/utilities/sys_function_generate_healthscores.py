# Filepath: app/utilities/sys_function_generate_healthscores.py
from flask import current_app
import logging
from sqlalchemy import text
from app.utilities.app_logging_helper import log_with_route
from app import db
from app.extensions import celery
from datetime import datetime
from app.models import HealthScoreHistory

def update_cascading_health_scores():
    """Direct function for route usage"""
    with current_app.app_context():
        try:
            # Execute score updates
            for sql in [device_sql, group_sql, org_sql, tenant_sql]:
                db.session.execute(sql)
                db.session.commit()

            # Log the update
            log_sql = text("""
                INSERT INTO health_score_update_log (update_time, description) 
                VALUES (CURRENT_TIMESTAMP, 'Cascading health scores updated successfully')
            """)
            db.session.execute(log_sql)
            db.session.commit()
            
            return True

        except Exception as e:
            log_with_route(logging.ERROR, f"Error updating health scores: {str(e)}")
            db.session.rollback()
            return False

# SQL statements as module-level constants
device_sql = text("""
    WITH device_scores AS (
        SELECT deviceuuid,
               ROUND(AVG(score)) as avg_score
        FROM devicemetadata
        WHERE processing_status = 'processed'
        AND score IS NOT NULL
        GROUP BY deviceuuid
    )
    UPDATE devices d
    SET health_score = ds.avg_score
    FROM device_scores ds
    WHERE d.deviceuuid = ds.deviceuuid
""")

group_sql = text("""
    UPDATE groups g
    SET health_score = t.avg_score
    FROM (
        SELECT groupuuid,
               ROUND(AVG(health_score)) as avg_score
        FROM devices
        WHERE health_score IS NOT NULL
        GROUP BY groupuuid
    ) t
    WHERE g.groupuuid = t.groupuuid
""")

org_sql = text("""
    UPDATE organisations o
    SET health_score = t.avg_score
    FROM (
        SELECT orguuid,
               ROUND(AVG(health_score)) as avg_score
        FROM groups
        WHERE health_score IS NOT NULL
        GROUP BY orguuid
    ) t
    WHERE o.orguuid = t.orguuid
""")

tenant_sql = text("""
    UPDATE tenants t
    SET health_score = s.avg_score
    FROM (
        SELECT tenantuuid,
               ROUND(AVG(health_score)) as avg_score
        FROM organisations
        WHERE health_score IS NOT NULL
        GROUP BY tenantuuid
    ) s
    WHERE t.tenantuuid = s.tenantuuid
""")

@celery.task(name="app.utilities.update_cascading_health_scores")
def update_cascading_health_scores_task():
    """Celery task for scheduled updates"""
    with current_app.app_context():
        try:
            # Create update log table if it doesn't exist
            create_log_table_sql = """
            CREATE TABLE IF NOT EXISTS health_score_update_log (
                id SERIAL PRIMARY KEY,
                update_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                description TEXT
            );
            """
            db.session.execute(text(create_log_table_sql))
            db.session.commit()

            # Execute score updates using module-level SQL constants
            for sql in [device_sql, group_sql, org_sql, tenant_sql]:
                db.session.execute(sql)
                db.session.commit()

            # Record history entries
            current_time = datetime.utcnow()
            history_entries = []

            # Get updated scores and create history entries
            queries = {
                'device': "SELECT deviceuuid as uuid, health_score FROM devices WHERE health_score IS NOT NULL",
                'group': "SELECT groupuuid as uuid, health_score FROM groups WHERE health_score IS NOT NULL",
                'organisation': "SELECT orguuid as uuid, health_score FROM organisations WHERE health_score IS NOT NULL",
                'tenant': "SELECT tenantuuid as uuid, health_score FROM tenants WHERE health_score IS NOT NULL"
            }

            for entity_type, query in queries.items():
                rows = db.session.execute(text(query))
                for row in rows:
                    history_entries.append(
                        HealthScoreHistory(
                            entity_type=entity_type,
                            entity_uuid=row.uuid,
                            health_score=row.health_score,
                            timestamp=current_time
                        )
                    )

            if history_entries:
                db.session.bulk_save_objects(history_entries)
                
            # Log the update with explicit timestamp
            log_sql = text("""
                INSERT INTO health_score_update_log (update_time, description) 
                VALUES (CURRENT_TIMESTAMP, 'Cascading health scores updated successfully')
            """)
            db.session.execute(log_sql)
            db.session.commit()

            log_with_route(logging.INFO, f"Successfully updated all health scores and recorded {len(history_entries)} history entries")
            return True

        except Exception as e:
            log_with_route(logging.ERROR, f"Error updating health scores: {str(e)}")
            db.session.rollback()
            return False