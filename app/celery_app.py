# Filepath: app/celery_app.py
from app.extensions import celery
from app import create_app
from app.models import db, DeviceDrivers
from app.utilities.app_logging_helper import log_with_route
import logging
import importlib
import os
from app.utilities import (
    sys_function_generate_healthscores,
    sys_function_process_payloads,
)
from app.tasks.lynis_parser_task import parse_lynis_audit
from app.tasks.connectivity_cleanup import cleanup_stale_connections

from app.tasks.drivers.analyzer import DriverAnalyzer
from app.tasks.groups.analyzer import GroupAnalyzer
from app.tasks.organizations.analyzer import OrganizationAnalyzer
from app.tasks.tenant.analyzer import TenantRecommendationsAnalyzer, TenantSuggestionsAnalyzer

from app.tasks.base.scheduler import run_analysis_worker

# Initialize Flask app first
flask_app = create_app()

# Using the shared Celery instance configured in create_app()


@celery.task
def run_driver_analysis_worker():
    """Process all unique devices that have driver records and are Windows devices"""
    try:
        session = db.session()
        try:
            # Get unique device IDs from DeviceDrivers table, but only for Windows devices
            from app.models import DeviceStatus
            unique_devices = (session.query(DeviceDrivers)
                            .join(DeviceStatus, DeviceDrivers.deviceuuid == DeviceStatus.deviceuuid)
                            .filter(DeviceStatus.agent_platform.like('Windows%'))
                            .with_entities(DeviceDrivers.deviceuuid)
                            .distinct()
                            .all())

            device_count = 0
            for (device_id,) in unique_devices:
                try:
                    analyzer = DriverAnalyzer(device_id)
                    analyzer.perform_analysis()  # Changed from _perform_analysis
                    device_count += 1
                    session.commit()
                except Exception as e:
                    session.rollback()
                    logging.error(f"Error analyzing device {device_id}: {str(e)}")
                    continue

            return f"Analyzed drivers for {device_count} devices"

        finally:
            session.close()

    except Exception as e:
        logging.error(f"Driver analysis error: {str(e)}")
        raise

@celery.task
def run_group_analysis_worker():
    """Process group analyses for all groups with enabled analysis"""
    try:
        from app.models import Groups, GroupMetadata, Tenants
        from sqlalchemy import text

        session = db.session()
        try:
            # Get all groups that belong to tenants with group analysis enabled
            groups = session.query(Groups).join(Tenants).filter(
                Tenants.recurring_analyses_enabled == True
            ).all()

            processed_count = 0
            for group in groups:
                try:
                    # Get the tenant for this group
                    tenant = session.query(Tenants).get(group.tenantuuid)
                    if not tenant:
                        continue

                    # Check if tenant has group analysis enabled
                    if not tenant.is_analysis_enabled('group-health-analysis'):
                        continue

                    # Check if group needs reanalysis based on new device intelligence
                    latest_group_analysis = session.query(GroupMetadata).filter_by(
                        groupuuid=group.groupuuid,
                        metalogos_type='group-health-analysis',
                        processing_status='processed'
                    ).order_by(GroupMetadata.analyzed_at.desc()).first()

                    # Get the most recent device analysis timestamp for this group
                    latest_device_analysis = session.execute(text("""
                        SELECT MAX(dm.analyzed_at) as latest_device_analysis
                        FROM devicemetadata dm
                        JOIN devices d ON dm.deviceuuid = d.deviceuuid
                        WHERE d.groupuuid = :group_uuid
                        AND dm.processing_status = 'processed'
                        AND dm.analyzed_at IS NOT NULL
                    """), {'group_uuid': str(group.groupuuid)}).scalar()

                    # Skip if no device analyses exist for this group
                    if not latest_device_analysis:
                        logging.debug(f"Skipping group {group.groupname} - no device analyses found")
                        continue

                    # Skip if group analysis is more recent than device analyses (no new intelligence)
                    if latest_group_analysis and latest_group_analysis.analyzed_at >= latest_device_analysis:
                        logging.debug(f"Skipping group {group.groupname} - no new device intelligence since last analysis")
                        continue

                    logging.info(f"Group {group.groupname} has new device intelligence - processing group analysis")

                    # Check for existing pending analysis
                    existing_pending = session.query(GroupMetadata).filter_by(
                        groupuuid=group.groupuuid,
                        metalogos_type='group-health-analysis',
                        processing_status='pending'
                    ).first()

                    metadata = existing_pending
                    if not existing_pending:
                        # Create new group metadata entry - new device intelligence available
                        metadata = GroupMetadata(
                            groupuuid=group.groupuuid,
                            metalogos_type='group-health-analysis',
                            metalogos={},  # Empty data for group analysis
                            processing_status='pending'
                        )
                        session.add(metadata)
                        session.commit()

                    if metadata:
                        # Process the analysis
                        analyzer = GroupAnalyzer(
                            str(group.groupuuid),
                            str(metadata.metadatauuid)
                        )

                        result = analyzer.analyze({})
                        if result.get('score', 0) > 0:
                            logging.info(f"Processed group analysis for {group.groupname} with score {result.get('score')}")
                            processed_count += 1
                        else:
                            logging.warning(f"Group analysis completed but returned zero score for {group.groupname}")

                except Exception as e:
                    session.rollback()
                    logging.error(f"Error analyzing group {group.groupuuid}: {str(e)}")
                    continue

            session.commit()
            return f"Processed group analyses for {processed_count} groups"

        finally:
            session.close()

    except Exception as e:
        logging.error(f"Group analysis error: {str(e)}")
        raise

@celery.task
def run_organization_analysis_worker():
    """Process organization analyses for all organizations with enabled analysis"""
    try:
        from app.models import Organisations, OrganizationMetadata, Tenants, Groups
        from sqlalchemy import text

        session = db.session()
        try:
            # Get all organizations that belong to tenants with organization analysis enabled
            organizations = session.query(Organisations).join(Tenants).filter(
                Tenants.recurring_analyses_enabled == True
            ).all()

            processed_count = 0
            for org in organizations:
                try:
                    # Get the tenant for this organization
                    tenant = session.query(Tenants).get(org.tenantuuid)
                    if not tenant:
                        continue

                    # Check if tenant has organization analysis enabled
                    if not tenant.is_analysis_enabled('organization-health-analysis'):
                        continue

                    # Check if organization needs reanalysis based on new group intelligence
                    latest_org_analysis = session.query(OrganizationMetadata).filter_by(
                        orguuid=org.orguuid,
                        metalogos_type='organization-health-analysis',
                        processing_status='processed'
                    ).order_by(OrganizationMetadata.analyzed_at.desc()).first()

                    # Get the most recent group analysis timestamp for this organization
                    latest_group_analysis = session.execute(text("""
                        SELECT MAX(gm.analyzed_at) as latest_group_analysis
                        FROM groupmetadata gm
                        JOIN groups g ON gm.groupuuid = g.groupuuid
                        WHERE g.orguuid = :org_uuid
                        AND gm.processing_status = 'processed'
                        AND gm.analyzed_at IS NOT NULL
                    """), {'org_uuid': str(org.orguuid)}).scalar()

                    # Skip if no group analyses exist for this organization
                    if not latest_group_analysis:
                        logging.debug(f"Skipping organization {org.orgname} - no group analyses found")
                        continue

                    # Skip if organization analysis is more recent than group analyses (no new intelligence)
                    if latest_org_analysis and latest_org_analysis.analyzed_at >= latest_group_analysis:
                        logging.debug(f"Skipping organization {org.orgname} - no new group intelligence since last analysis")
                        continue

                    logging.info(f"Organization {org.orgname} has new group intelligence - processing organization analysis")

                    # Check for existing pending analysis
                    existing_pending = session.query(OrganizationMetadata).filter_by(
                        orguuid=org.orguuid,
                        metalogos_type='organization-health-analysis',
                        processing_status='pending'
                    ).first()

                    metadata = existing_pending
                    if not existing_pending:
                        # Create new organization metadata entry - new group intelligence available
                        metadata = OrganizationMetadata(
                            orguuid=org.orguuid,
                            metalogos_type='organization-health-analysis',
                            metalogos={},  # Empty data for organization analysis
                            processing_status='pending'
                        )
                        session.add(metadata)
                        session.commit()

                    if metadata:
                        # Process the analysis
                        analyzer = OrganizationAnalyzer(
                            str(org.orguuid),
                            str(metadata.metadatauuid)
                        )

                        result = analyzer.analyze({})
                        if result.get('score', 0) > 0:
                            logging.info(f"Processed organization analysis for {org.orgname} with score {result.get('score')}")
                            processed_count += 1
                        else:
                            logging.warning(f"Organization analysis completed but returned zero score for {org.orgname}")

                except Exception as e:
                    session.rollback()
                    logging.error(f"Error analyzing organization {org.orguuid}: {str(e)}")
                    continue

            session.commit()
            return f"Processed organization analyses for {processed_count} organizations"

        finally:
            session.close()

    except Exception as e:
        logging.error(f"Organization analysis error: {str(e)}")
        raise

@celery.task
def run_tenant_analysis_worker():
    """Process tenant analyses for all tenants with enabled analysis"""
    try:
        from app.models import Tenants, TenantMetadata
        from sqlalchemy import text

        session = db.session()
        try:
            # Get all tenants that have tenant analysis enabled
            tenants = session.query(Tenants).filter(
                Tenants.recurring_analyses_enabled == True
            ).all()

            processed_count = 0
            for tenant in tenants:
                try:
                    # Process AI Recommendations
                    if tenant.is_analysis_enabled('tenant-ai-recommendations'):
                        processed_count += process_tenant_analysis(
                            session, tenant, 'tenant-ai-recommendations', TenantRecommendationsAnalyzer
                        )

                    # Process AI Suggestions
                    if tenant.is_analysis_enabled('tenant-ai-suggestions'):
                        processed_count += process_tenant_analysis(
                            session, tenant, 'tenant-ai-suggestions', TenantSuggestionsAnalyzer
                        )

                except Exception as e:
                    session.rollback()
                    logging.error(f"Error analyzing tenant {tenant.tenantuuid}: {str(e)}")
                    continue

            session.commit()
            return f"Processed tenant analyses for {processed_count} analyses"

        finally:
            session.close()

    except Exception as e:
        logging.error(f"Tenant analysis error: {str(e)}")
        raise

def process_tenant_analysis(session, tenant, analysis_type, analyzer_class):
    """Process a specific tenant analysis type"""
    try:
        from app.models import TenantMetadata
        # Check if analysis needs to be run (daily schedule)
        latest_analysis = session.query(TenantMetadata).filter_by(
            tenantuuid=tenant.tenantuuid,
            metalogos_type=analysis_type,
            processing_status='processed'
        ).order_by(TenantMetadata.analyzed_at.desc()).first()

        # Skip if analysis was done in the last 23 hours (daily schedule with some buffer)
        if latest_analysis and latest_analysis.analyzed_at:
            import time
            hours_since_last = (time.time() - latest_analysis.analyzed_at) / 3600
            if hours_since_last < 23:
                logging.debug(f"Skipping {analysis_type} for tenant {tenant.tenantname} - analyzed {hours_since_last:.1f} hours ago")
                return 0

        logging.info(f"Tenant {tenant.tenantname} needs {analysis_type} - processing")

        # Check for existing pending analysis
        existing_pending = session.query(TenantMetadata).filter_by(
            tenantuuid=tenant.tenantuuid,
            metalogos_type=analysis_type,
            processing_status='pending'
        ).first()

        metadata = existing_pending
        if not existing_pending:
            # Create new tenant metadata entry
            metadata = TenantMetadata(
                tenantuuid=tenant.tenantuuid,
                metalogos_type=analysis_type,
                metalogos={},  # Empty data for tenant analysis
                processing_status='pending'
            )
            session.add(metadata)
            session.commit()

        if metadata:
            # Process the analysis
            analyzer = analyzer_class(
                str(tenant.tenantuuid),
                str(metadata.metadatauuid)
            )

            result = analyzer.analyze({})
            if result.get('score', 0) > 0:
                logging.info(f"Processed {analysis_type} for {tenant.tenantname} with score {result.get('score')}")
                return 1
            else:
                logging.warning(f"Tenant analysis completed but returned zero score for {tenant.tenantname}")
                return 0

    except Exception as e:
        logging.error(f"Error processing {analysis_type} for tenant {tenant.tenantuuid}: {str(e)}")
        return 0

# Lightweight wrapper tasks that mirror the working driver worker
# Each wrapper simply enqueues the generic worker with the appropriate analysis type.
# This avoids any potential binding/signature issues with passing args via beat.
@celery.task(name='app.tasks.run_msinfo_network_worker')
def run_msinfo_network_worker(batch_size: int = 10):
    try:
        return run_analysis_worker.delay('msinfo-NetworkConfig', batch_size).id
    except Exception as e:
        logging.error(f"Failed to enqueue msinfo-NetworkConfig: {e}")
        return None

@celery.task(name='app.tasks.run_msinfo_crashes_worker')
def run_msinfo_crashes_worker(batch_size: int = 10):
    try:
        return run_analysis_worker.delay('msinfo-RecentAppCrashes', batch_size).id
    except Exception as e:
        logging.error(f"Failed to enqueue msinfo-RecentAppCrashes: {e}")
        return None

@celery.task(name='app.tasks.run_msinfo_software_worker')
def run_msinfo_software_worker(batch_size: int = 10):
    try:
        return run_analysis_worker.delay('msinfo-SystemSoftwareConfig', batch_size).id
    except Exception as e:
        logging.error(f"Failed to enqueue msinfo-SystemSoftwareConfig: {e}")
        return None

@celery.task(name='app.tasks.run_syslog_worker')
def run_syslog_worker(batch_size: int = 10):
    try:
        return run_analysis_worker.delay('syslogFiltered', batch_size).id
    except Exception as e:
        logging.error(f"Failed to enqueue syslogFiltered: {e}")
        return None

@celery.task(name='app.tasks.run_msinfo_storage_worker')
def run_msinfo_storage_worker(batch_size: int = 10):
    try:
        return run_analysis_worker.delay('msinfo-StorageInfo', batch_size).id
    except Exception as e:
        logging.error(f"Failed to enqueue msinfo-StorageInfo: {e}")
        return None

@celery.task(name='app.tasks.run_msinfo_installed_programs_worker')
def run_msinfo_installed_programs_worker(batch_size: int = 10):
    try:
        return run_analysis_worker.delay('msinfo-InstalledPrograms', batch_size).id
    except Exception as e:
        logging.error(f"Failed to enqueue msinfo-InstalledPrograms: {e}")
        return None

@celery.task(name='app.tasks.run_events_system_worker')
def run_events_system_worker(batch_size: int = 10):
    try:
        return run_analysis_worker.delay('eventsFiltered-System', batch_size).id
    except Exception as e:
        logging.error(f"Failed to enqueue eventsFiltered-System: {e}")
        return None

@celery.task(name='app.tasks.run_journal_worker')
def run_journal_worker(batch_size: int = 10):
    try:
        return run_analysis_worker.delay('journalFiltered', batch_size).id
    except Exception as e:
        logging.error(f"Failed to enqueue journalFiltered: {e}")
        return None

@celery.task(name='app.tasks.run_auth_worker')
def run_auth_worker(batch_size: int = 10):
    try:
        return run_analysis_worker.delay('authFiltered', batch_size).id
    except Exception as e:
        logging.error(f"Failed to enqueue authFiltered: {e}")
        return None

# Lynis parser worker: scans pending lynis items and enqueues parse_lynis_audit
@celery.task(name='app.tasks.run_lynis_parse_worker')
def run_lynis_parse_worker(batch_size: int = 20):
    try:
        from app.models import DeviceMetadata
        session = db.session()
        try:
            rows = (session.query(DeviceMetadata.metadatauuid, DeviceMetadata.metalogos_type)
                    .filter(
                        DeviceMetadata.metalogos_type.in_(['lynis-audit', 'lynis_audit']),
                        DeviceMetadata.processing_status == 'pending'
                    )
                    .order_by(DeviceMetadata.created_at)
                    .limit(max(1, int(batch_size)))
                    .all())
            enqueued = 0
            for (metadata_id, mtype) in rows:
                try:
                    # Normalize metalogos_type to expected value for parser
                    if mtype == 'lynis-audit':
                        session.query(DeviceMetadata).filter(DeviceMetadata.metadatauuid == metadata_id).update({DeviceMetadata.metalogos_type: 'lynis_audit'})
                        session.commit()
                    parse_lynis_audit.delay(str(metadata_id))
                    enqueued += 1
                except Exception as e:
                    logging.error(f"Failed to enqueue parse_lynis_audit for {metadata_id}: {e}")
            return enqueued
        finally:
            session.close()
    except Exception as e:
        logging.error(f"Lynis parse worker error: {e}")
        return 0

@celery.task(name='app.tasks.run_events_application_worker')
def run_events_application_worker(batch_size: int = 10):
    try:
        return run_analysis_worker.delay('eventsFiltered-Application', batch_size).id
    except Exception as e:
        logging.error(f"Failed to enqueue eventsFiltered-Application: {e}")
        return None

@celery.task(name='app.tasks.run_events_security_worker')
def run_events_security_worker(batch_size: int = 10):
    try:
        return run_analysis_worker.delay('eventsFiltered-Security', batch_size).id
    except Exception as e:
        logging.error(f"Failed to enqueue eventsFiltered-Security: {e}")
        return None

@celery.task(name='app.tasks.run_kernel_worker')
def run_kernel_worker(batch_size: int = 10):
    try:
        return run_analysis_worker.delay('kernFiltered', batch_size).id
    except Exception as e:
        logging.error(f"Failed to enqueue kernFiltered: {e}")
        return None

@celery.task(name='app.tasks.run_msinfo_hardware_worker')
def run_msinfo_hardware_worker(batch_size: int = 10):
    try:
        return run_analysis_worker.delay('msinfo-SystemHardwareConfig', batch_size).id
    except Exception as e:
        logging.error(f"Failed to enqueue msinfo-SystemHardwareConfig: {e}")
        return None

# macOS wrapper tasks (use database metalogos_type values)
@celery.task(name='app.tasks.run_macos_hardware_eol_worker')
def run_macos_hardware_eol_worker(batch_size: int = 10):
    try:
        return run_analysis_worker.delay('macos-hardware-eol-analysis', batch_size).id
    except Exception as e:
        logging.error(f"Failed to enqueue macos-hardware-eol-analysis: {e}")
        return None

@celery.task(name='app.tasks.run_macos_os_version_worker')
def run_macos_os_version_worker(batch_size: int = 10):
    try:
        return run_analysis_worker.delay('macos-os-version-analysis', batch_size).id
    except Exception as e:
        logging.error(f"Failed to enqueue macos-os-version-analysis: {e}")
        return None

@celery.task(name='app.tasks.run_macos_log_health_worker')
def run_macos_log_health_worker(batch_size: int = 10):
    try:
        return run_analysis_worker.delay('macos-log-health-analysis', batch_size).id
    except Exception as e:
        logging.error(f"Failed to enqueue macos-log-health-analysis: {e}")
        return None


def setup_periodic_tasks(sender, **kwargs):
    """Setup periodic tasks for analysis workers"""
    sender.add_periodic_task(
        60.0,
        run_msinfo_network_worker.s(),
        name='Network Analysis Worker'
    )

    sender.add_periodic_task(
        60.0,
        run_msinfo_crashes_worker.s(),
        name='Crash Analysis Worker'
    )
    sender.add_periodic_task(
        60.0,
        run_msinfo_software_worker.s(),
        name='Software Analysis Worker'
    )
    sender.add_periodic_task(
        60.0,
        run_syslog_worker.s(),
        name='Syslog Analysis Worker'
    )
    sender.add_periodic_task(
        60.0,
        run_msinfo_storage_worker.s(),
        name='Storage Analysis Worker'
    )
    sender.add_periodic_task(
        60.0,
        run_msinfo_installed_programs_worker.s(),
        name='Installed Programs Analysis Worker'
    )

    sender.add_periodic_task(
        60.0,
        run_events_system_worker.s(),
        name='System Log Analysis Worker'
    )
    sender.add_periodic_task(
        60.0,
        run_journal_worker.s(),
        name='Journal Analysis Worker'
    )

    sender.add_periodic_task(
        60.0,
        run_auth_worker.s(),
        name='Auth Analysis Worker'
    )

    sender.add_periodic_task(
        60.0,
        run_events_application_worker.s(),
        name='Application Log Analysis Worker'
    )

    sender.add_periodic_task(
        60.0,
        run_events_security_worker.s(),
        name='Security Log Analysis Worker'
    )

    sender.add_periodic_task(
        60.0,
        run_kernel_worker.s(),
        name='Kernel Log Analysis Worker'
    )
    sender.add_periodic_task(
        60.0,
        run_msinfo_hardware_worker.s(),
        name='Hardware Analysis Worker'
    )

    sender.add_periodic_task(
        86400.0,
        run_driver_analysis_worker.s(),
        name='Driver Analysis Worker'
    )

    sender.add_periodic_task(
        7200.0,  # Every 2 hours
        run_group_analysis_worker.s(),
        name='Group Analysis Worker'
    )

    sender.add_periodic_task(
        10800.0,  # Every 3 hours
        run_organization_analysis_worker.s(),
        name='Organization Analysis Worker'
    )

    sender.add_periodic_task(
        604800.0,  # Every week (7 days * 24 hours * 60 minutes * 60 seconds)
        run_tenant_analysis_worker.s(),
        name='Tenant Analysis Worker'
    )

    # macOS Analysis Workers (using database metalogos_type)
    sender.add_periodic_task(
        300.0,  # Every 5 minutes
        run_macos_hardware_eol_worker.s(),
        name='macOS Hardware EOL Analysis Worker'
    )

    sender.add_periodic_task(
        300.0,  # Every 5 minutes
        run_macos_os_version_worker.s(),
        name='macOS OS Version Analysis Worker'
    )

    sender.add_periodic_task(
        300.0,  # Every 5 minutes
        run_macos_log_health_worker.s(),
        name='macOS Log Health Analysis Worker'
    )

    sender.add_periodic_task(60.0,
        sys_function_process_payloads.call_processpayloads_task.s(),
        name='Process payloads every minute'
    )

    sender.add_periodic_task(3600.0,
        sys_function_generate_healthscores.update_cascading_health_scores_task.s(),
        name='Generate Healthscores every 1 hour'
    )

    # Lynis audit parser worker (non-AI, no wegcoin cost)
    sender.add_periodic_task(
        60.0,
        run_lynis_parse_worker.s(),
        name='Lynis Audit Parse Worker'
    )

    # Connectivity cleanup - mark stale devices as offline
    sender.add_periodic_task(
        300.0,  # Every 5 minutes
        cleanup_stale_connections.s(),
        name='Connectivity Cleanup - Mark Stale Devices Offline'
    )

# Connect the signal and also call it immediately to ensure tasks are registered
celery.on_after_configure.connect(setup_periodic_tasks)

# Also call it immediately to ensure periodic tasks are set up
# This handles cases where the signal might not fire properly with --beat
try:
    setup_periodic_tasks(celery)
    print("Periodic tasks setup completed")
except Exception as e:
    print(f"Error setting up periodic tasks: {e}")


# This makes the celery worker command work
app = celery

if __name__ == '__main__':
    celery.start()