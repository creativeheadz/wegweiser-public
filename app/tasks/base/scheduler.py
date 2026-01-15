# Filepath: app/tasks/base/scheduler.py
from typing import Type, Dict, Any
from app.extensions import celery
from app.models import db
from app.tasks.base.analyzer import BaseAnalyzer
import logging
from flask import current_app
from sqlalchemy import desc, select, text
from datetime import datetime
from contextlib import contextmanager
import threading
import time
from sqlalchemy.exc import OperationalError, DatabaseError, SQLAlchemyError, NoSuchColumnError

class AnalysisScheduler:
    _lock = threading.Lock()
    analyzers = {}  # Class-level dictionary

    def __init__(self):
        with self._lock:
            if not self.analyzers:
                self.register_default_analyzers()

    def register_default_analyzers(self):
        """Register all known analyzers"""
        from app.tasks.journal import JournalAnalyzer
        from app.tasks.auth import AuthAnalyzer
        from app.tasks.application import ApplicationLogAnalyzer
        from app.tasks.security import SecurityLogAnalyzer
        from app.tasks.system import SystemLogAnalyzer
        from app.tasks.programs import InstalledProgramsAnalyzer
        from app.tasks.kernel import KernelLogAnalyzer
        # from app.tasks.drivers import DriverAnalyzer  # Handled by dedicated worker; do not register here
        from app.tasks.storage import StorageAnalyzer
        from app.tasks.syslog import SyslogAnalyzer
        from app.tasks.hardware import HardwareAnalyzer
        from app.tasks.software import SoftwareAnalyzer
        from app.tasks.crashes import CrashAnalyzer
        from app.tasks.network import NetworkAnalyzer
        from app.tasks.groups import GroupAnalyzer
        from app.tasks.organizations import OrganizationAnalyzer
        from app.tasks.tenant import TenantRecommendationsAnalyzer, TenantSuggestionsAnalyzer
        from app.tasks.macos_hardware import MacOSHardwareAnalyzer
        from app.tasks.macos_os import MacOSOSAnalyzer
        from app.tasks.macos_logs import MacOSLogsAnalyzer
        from app.tasks.loki_scan import LokiScanAnalyzer

        self.register_analyzer(NetworkAnalyzer)
        self.register_analyzer(CrashAnalyzer)
        self.register_analyzer(SoftwareAnalyzer)
        self.register_analyzer(HardwareAnalyzer)
        self.register_analyzer(SyslogAnalyzer)
        self.register_analyzer(StorageAnalyzer)
        # self.register_analyzer(DriverAnalyzer)  # Skip registration to prevent generic worker from using DriverAnalyzer
        self.register_analyzer(JournalAnalyzer)
        self.register_analyzer(AuthAnalyzer)
        self.register_analyzer(ApplicationLogAnalyzer)
        self.register_analyzer(SecurityLogAnalyzer)
        self.register_analyzer(SystemLogAnalyzer)
        self.register_analyzer(InstalledProgramsAnalyzer)
        self.register_analyzer(KernelLogAnalyzer)
        self.register_analyzer(GroupAnalyzer)
        self.register_analyzer(OrganizationAnalyzer)
        self.register_analyzer(TenantRecommendationsAnalyzer)
        self.register_analyzer(TenantSuggestionsAnalyzer)
        self.register_analyzer(MacOSHardwareAnalyzer)
        self.register_analyzer(MacOSOSAnalyzer)
        self.register_analyzer(MacOSLogsAnalyzer)
        self.register_analyzer(LokiScanAnalyzer)

    def register_analyzer(self, analyzer_class):
        """Register a new analyzer for a task type"""
        task_type = analyzer_class.task_type
        if task_type not in self.analyzers:
            self.analyzers[task_type] = analyzer_class
            logging.debug(f"Registered analyzer for task type: {task_type}")

    def get_analyzer(self, task_type: str) -> Type[BaseAnalyzer]:
        """Get analyzer class by type"""
        # Handle mapping from database metalogos_type to analyzer task_type
        task_type_mapping = {
            'macos-hardware-eol-analysis': 'macos-hardware-eol',
            'macos-os-version-analysis': 'macos-os-version',
            'macos-log-health-analysis': 'macos-log-health'
        }

        # Use mapped type if available, otherwise use original
        mapped_type = task_type_mapping.get(task_type, task_type)
        return self.analyzers.get(mapped_type)

def check_db_connection(session):
    """Test if database connection is alive"""
    try:
        session.execute(text('SELECT 1'))
        return True
    except:
        return False

def get_pending_analysis(session, analysis_type: str, skip_ids=None):
    """Select and claim the next pending analysis row using SKIP LOCKED.

    Returns a lightweight dict with required fields to avoid stale ORM instances.
    """
    max_retries = 3
    retry_delay = 1  # seconds

    for attempt in range(max_retries):
        try:
            # Import here to avoid circular import issues
            from app.models import DeviceMetadata

            # Verify connection is alive
            if not check_db_connection(session):
                session.rollback()
                continue

            # Select explicit columns to avoid ORM mapping issues under connection churn
            q = (session.query(
                    DeviceMetadata.metadatauuid,
                    DeviceMetadata.deviceuuid,
                    DeviceMetadata.metalogos
                 )
                 .filter(
                     DeviceMetadata.metalogos_type == analysis_type,
                     DeviceMetadata.processing_status == 'pending'
                 )
                 .order_by(DeviceMetadata.created_at)
                 .with_for_update(skip_locked=True))

            if skip_ids:
                q = q.filter(~DeviceMetadata.metadatauuid.in_(list(skip_ids)))

            row = q.first()
            if not row:
                return None

            # Claim this row by setting it to processing to prevent re-selection
            updated = (session.query(DeviceMetadata)
                       .filter(
                           DeviceMetadata.metadatauuid == row[0],
                           DeviceMetadata.processing_status == 'pending'
                       )
                       .update({DeviceMetadata.processing_status: 'processing'}, synchronize_session=False))

            # Commit to release the row lock and persist the claim
            session.commit()

            if updated == 0:
                # Someone else claimed/processed it in the meantime; retry
                continue

            return {
                'metadatauuid': row[0],
                'deviceuuid': row[1],
                'metalogos': row[2],
            }

        except (OperationalError, DatabaseError, NoSuchColumnError) as e:
            if attempt == max_retries - 1:
                raise
            logging.warning(f"Database error on attempt {attempt + 1}, retrying: {str(e)}")
            time.sleep(retry_delay)
            try:
                session.rollback()
            except:
                pass

    return None

# Filepath: app/tasks/base/scheduler.py
@celery.task(name="app.tasks.run_analysis_worker", bind=True)
def run_analysis_worker(self, analysis_type: str, batch_size: int = 1):
    """Worker task that processes up to batch_size pending analyses of a specific type"""
    with current_app.app_context():
        scheduler = AnalysisScheduler()
        analyzer_cls = scheduler.get_analyzer(analysis_type)

        if not analyzer_cls:
            logging.error(f"No analyzer found for type {analysis_type}")
            return

        session = None
        processed = 0
        try:
            session = db.session()

            # Import here to avoid circular import issues
            from app.models import Devices

            skipped_ids = set()
            max_attempts = max(1, int(batch_size)) * 5  # allow skipping ineligible items without blocking

            attempts = 0
            while processed < max(1, int(batch_size)) and attempts < max_attempts:
                attempts += 1
                pending = get_pending_analysis(session, analysis_type, skip_ids=skipped_ids)

                if not pending:
                    if processed == 0:
                        logging.info(f"No pending {analysis_type} analyses found")
                    break

                # Get device and check if analysis is enabled for tenant
                device = session.get(Devices, pending['deviceuuid'])
                if not device or not device.tenant:
                    logging.error(f"Device or tenant not found for {pending['deviceuuid']}")
                    skipped_ids.add(pending['metadatauuid'])
                    continue

                # Skip if recurring analyses are disabled globally
                if not device.tenant.recurring_analyses_enabled:
                    skipped_ids.add(pending['metadatauuid'])
                    continue

                # Skip if this specific analysis type is disabled
                if not device.tenant.is_analysis_enabled(analysis_type):
                    skipped_ids.add(pending['metadatauuid'])
                    continue

                # Check if tenant has insufficient wegcoins
                analysis_cost = device.tenant.get_analysis_cost(analysis_type)
                if device.tenant.available_wegcoins < analysis_cost:
                    # Disable all analyses for this tenant instead of repeatedly logging
                    if device.tenant.recurring_analyses_enabled:
                        device.tenant.disable_all_analyses()
                        session.commit()
                        logging.warning(f"Disabled all analyses for tenant {device.tenant.tenantuuid} due to insufficient wegcoins (has {device.tenant.available_wegcoins}, needs {analysis_cost})")
                    skipped_ids.add(pending['metadatauuid'])
                    continue

                logging.info(f"Processing {analysis_type} analysis for device {pending['deviceuuid']}")

                analyzer = analyzer_cls(
                    str(pending['deviceuuid']),
                    str(pending['metadatauuid'])
                )

                result = analyzer.analyze(pending['metalogos'])
                if result.get('score', 0) > 0:
                    logging.info(f"Processed {pending['metadatauuid']} with score {result.get('score')}")
                else:
                    logging.warning(f"Analysis completed but returned zero score for {pending['metadatauuid']}")

                processed += 1

            # No pending transactional work here; analyzers manage their own commits
            return {"processed": processed}

        except SQLAlchemyError as e:
            logging.exception(f"Database error in {analysis_type} processor: {str(e)}")
            if session:
                try:
                    session.rollback()
                except:
                    pass
            return None

        except Exception as e:
            if '<userStyle>' not in str(e):  # Only log non-style errors
                logging.error(f"Error in {analysis_type} processor: {str(e)}")
            if session:
                try:
                    session.rollback()
                except:
                    pass
            return None

        finally:
            if session:
                try:
                    session.close()
                except:
                    pass

# Legacy task handler compatibility
@celery.task(name="app.tasks.process_pending_analyses")
def process_pending_analyses(analysis_type: str = 'journalFiltered', batch_size: int = 1):
    """Legacy task handler - redirects to worker"""
    run_analysis_worker.delay(analysis_type, batch_size)