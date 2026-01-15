# Filepath: app/models/device_osquery.py

# Filepath: app/models/device_osquery.py
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship, backref
from . import db
import uuid
import time

class DeviceOSQuery(db.Model):
    __tablename__ = 'device_osquery'
    
    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    deviceuuid = db.Column(UUID(as_uuid=True), db.ForeignKey('devices.deviceuuid', ondelete="CASCADE"), nullable=False)
    query_name = db.Column(db.String(255), nullable=False)
    query_data = db.Column(JSONB, nullable=False)
    last_updated = db.Column(db.BigInteger, nullable=False, default=lambda: int(time.time()))

    # Define the relationship with the Devices model
    device = relationship(
        'Devices',
        backref=backref('osquery_data', passive_deletes=True),
        passive_deletes=True
    )

    __table_args__ = (
        db.Index('idx_device_query', deviceuuid, query_name),
    )

    @classmethod
    def store_query_result(cls, deviceuuid, query_name, data):
        """Store or update query results for a device"""
        record = cls.query.filter_by(
            deviceuuid=deviceuuid,
            query_name=query_name
        ).first()
        
        if record:
            record.query_data = data
            record.last_updated = int(time.time())
        else:
            record = cls(
                deviceuuid=deviceuuid,
                query_name=query_name,
                query_data=data
            )
            db.session.add(record)
        
        db.session.commit()
        return record