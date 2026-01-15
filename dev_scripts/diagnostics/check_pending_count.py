import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
from app import create_app
from app.models import db, DeviceMetadata
from sqlalchemy import func

app = create_app()

if __name__ == "__main__":
    with app.app_context():
        session = db.session()
        try:
            total_pending = session.query(func.count()).select_from(DeviceMetadata).filter(DeviceMetadata.processing_status == 'pending').scalar()
            total_processing = session.query(func.count()).select_from(DeviceMetadata).filter(DeviceMetadata.processing_status == 'processing').scalar()
            total_processed = session.query(func.count()).select_from(DeviceMetadata).filter(DeviceMetadata.processing_status == 'processed').scalar()
            total_failed = session.query(func.count()).select_from(DeviceMetadata).filter(DeviceMetadata.processing_status == 'failed').scalar()

            print({
                'pending': int(total_pending or 0),
                'processing': int(total_processing or 0),
                'processed': int(total_processed or 0),
                'failed': int(total_failed or 0),
            })

            # Breakdown of pending by analysis type (top 15)
            rows = (session.query(DeviceMetadata.metalogos_type, func.count().label('cnt'))
                    .filter(DeviceMetadata.processing_status == 'pending')
                    .group_by(DeviceMetadata.metalogos_type)
                    .order_by(func.count().desc())
                    .limit(15)
                    .all())
            if rows:
                breakdown = {r[0]: int(r[1]) for r in rows}
                print('pending_by_type:', breakdown)
        finally:
            session.close()
