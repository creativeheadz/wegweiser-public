# Filepath: app/models/stored_procedures.py
from sqlalchemy import DDL, event
from . import db

update_cascading_health_scores_procedure = DDL('''
CREATE OR REPLACE FUNCTION update_cascading_health_scores()
RETURNS void AS $$
BEGIN
    -- Update device health scores
    UPDATE devices d
    SET health_score = (
        SELECT ROUND(AVG(dm.score))
        FROM devicemetadata dm
        WHERE dm.deviceuuid = d.deviceuuid
          AND dm.score IS NOT NULL
    )
    WHERE EXISTS (
        SELECT 1
        FROM devicemetadata dm
        WHERE dm.deviceuuid = d.deviceuuid
          AND dm.score IS NOT NULL
    );

    -- Update group health scores
    UPDATE groups g
    SET health_score = (
        SELECT ROUND(AVG(d.health_score))
        FROM devices d
        WHERE d.groupuuid = g.groupuuid
          AND d.health_score IS NOT NULL
    )
    WHERE EXISTS (
        SELECT 1
        FROM devices d
        WHERE d.groupuuid = g.groupuuid
          AND d.health_score IS NOT NULL
    );

    -- Update organisation health scores
    UPDATE organisations o
    SET health_score = (
        SELECT ROUND(AVG(g.health_score))
        FROM groups g
        WHERE g.orguuid = o.orguuid
          AND g.health_score IS NOT NULL
    )
    WHERE EXISTS (
        SELECT 1
        FROM groups g
        WHERE g.orguuid = o.orguuid
          AND g.health_score IS NOT NULL
    );

    -- Update tenant health scores
    UPDATE tenants t
    SET health_score = (
        SELECT ROUND(AVG(o.health_score))
        FROM organisations o
        WHERE o.tenantuuid = t.tenantuuid
          AND o.health_score IS NOT NULL
    )
    WHERE EXISTS (
        SELECT 1
        FROM organisations o
        WHERE o.tenantuuid = t.tenantuuid
          AND o.health_score IS NOT NULL
    );

    -- Log the update
    INSERT INTO health_score_update_log (update_time, description)
    VALUES (NOW(), 'Cascading health scores updated for devices, groups, organisations, and tenants');
END;
$$ LANGUAGE plpgsql;
''')

# This will create the function when the app first connects to the database
event.listen(
    db.metadata,
    'after_create',
    update_cascading_health_scores_procedure
)