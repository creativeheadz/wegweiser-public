# Filepath: app/models/snippets.py
from sqlalchemy.dialects.postgresql import UUID, JSON
from sqlalchemy.orm import relationship
from sqlalchemy import event, PrimaryKeyConstraint, and_
from . import db
import uuid
import time
from .groups import Groups
from app.utilities.app_logging_helper import log_with_route
import logging

class Snippets(db.Model):
    __tablename__ = 'snippets'
    snippetuuid = db.Column(UUID(as_uuid=True), primary_key=True, nullable=False)
    tenantuuid = db.Column(UUID(as_uuid=True), db.ForeignKey('tenants.tenantuuid', ondelete="CASCADE"), nullable=False)
    snippetname = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.BigInteger, nullable=False)
    max_exec_secs = db.Column(db.Integer, nullable=False)

class SnippetsSchedule(db.Model):
    __tablename__ = 'snippetsschedule'
    scheduleuuid = db.Column(UUID(as_uuid=True), nullable=False)
    snippetuuid = db.Column(UUID(as_uuid=True), db.ForeignKey('snippets.snippetuuid', ondelete="CASCADE"), nullable=False)
    deviceuuid = db.Column(UUID(as_uuid=True), db.ForeignKey('devices.deviceuuid', ondelete="CASCADE"), nullable=False)
    recurrence = db.Column(db.Integer, nullable=False)
    interval = db.Column(db.Integer, nullable=False)
    nextexecution = db.Column(db.BigInteger, nullable=False)
    lastexecution = db.Column(db.BigInteger, nullable=True)
    lastexecstatus = db.Column(db.String(255), nullable=True)
    inprogress = db.Column(db.Boolean, nullable=True)
    enabled = db.Column(db.Boolean, nullable=True)
    parameters = db.Column(JSON, nullable=True)  # Optional JSON parameters for snippet execution

    __table_args__ = (
        PrimaryKeyConstraint('snippetuuid', 'deviceuuid', name='snippetuuid_deviceuuid_sched_pk'),
    )

    @classmethod
    def get_pending_snippets(cls, device_uuid):
        """Get pending snippets, automatically resetting stale executions"""
        current_time = int(time.time())
        
        # First, reset any stale executions
        stale_snippets = db.session.query(cls).join(
            Snippets, cls.snippetuuid == Snippets.snippetuuid
        ).filter(
            and_(
                cls.deviceuuid == device_uuid,
                cls.inprogress == True,
                cls.lastexecution != None,
                current_time - cls.lastexecution > Snippets.max_exec_secs
            )
        ).all()

        # Reset stale snippets
        for snippet in stale_snippets:
            snippet.inprogress = False
            snippet.lastexecstatus = 'TIMEOUT'
            log_with_route(logging.WARNING, 
                f"Reset stale snippet {snippet.snippetuuid} - exceeded max execution time")

        if stale_snippets:
            try:
                db.session.commit()
            except Exception as e:
                db.session.rollback()
                log_with_route(logging.ERROR, f"Error resetting stale snippets: {str(e)}")

        # Now get pending snippets
        return db.session.query(cls).filter(
            and_(
                cls.deviceuuid == device_uuid,
                cls.nextexecution <= current_time,
                cls.inprogress == False,
                cls.enabled == True
            )
        ).all()

    def start_execution(self):
        """Mark snippet as starting execution"""
        try:
            self.inprogress = True
            self.lastexecution = int(time.time())
            db.session.commit()
            return True
        except Exception as e:
            db.session.rollback()
            log_with_route(logging.ERROR, f"Error marking snippet as started: {str(e)}")
            return False

    def complete_execution(self, status):
        """Mark snippet execution as complete and record in history"""
        try:
            current_time = int(time.time())
            self.inprogress = False
            self.lastexecstatus = status
            
            # Calculate next execution time based on recurrence and interval
            if self.recurrence and self.interval:
                self.nextexecution = current_time + (self.interval * self.recurrence)
            
            # Create history record
            history = SnippetsHistory(
                historyuuid=uuid.uuid4(),
                scheduleuuid=self.scheduleuuid,
                snippetuuid=self.snippetuuid,
                deviceuuid=self.deviceuuid,
                exectime=current_time,
                execstatus=status
            )
            db.session.add(history)
            
            db.session.commit()
            return True
        except Exception as e:
            db.session.rollback()
            log_with_route(logging.ERROR, f"Error marking snippet as complete: {str(e)}")
            return False

class SnippetsHistory(db.Model):
    __tablename__ = 'snippetshistory'
    historyuuid = db.Column(UUID(as_uuid=True), primary_key=True, nullable=False)
    scheduleuuid = db.Column(UUID(as_uuid=True), nullable=False)  
    snippetuuid = db.Column(UUID(as_uuid=True), nullable=False)
    deviceuuid = db.Column(UUID(as_uuid=True), nullable=False)
    exectime = db.Column(db.BigInteger, nullable=True)
    execstatus = db.Column(db.String(255), nullable=True)