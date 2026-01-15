# Filepath: app/routes/admin/agent_updates.py
"""
Admin routes for managing agent updates
"""
import hashlib
import logging
import os
import time
import uuid as uuid_lib
from datetime import datetime
from pathlib import Path

from flask import Blueprint, render_template, request, jsonify, session
from flask_principal import Permission, RoleNeed

from app.models import (
    db, Devices, Groups, Organisations, Tenants,
    DeviceConnectivity, AgentUpdateHistory, Snippets
)
from app.utilities.app_logging_helper import log_with_route
from app.utilities.snippet_scheduler import upsertSnippetSchedule


agent_updates_bp = Blueprint('agent_updates_bp', __name__)
admin_permission = Permission(RoleNeed('admin'))


def get_available_updates():
    """Get list of available update packages from installerFiles directory"""
    updates = []
    platforms = ['Linux', 'MacOS', 'Windows']

    for platform in platforms:
        update_dir = Path(f'/opt/wegweiser/installerFiles/{platform}/updates')
        if not update_dir.exists():
            continue

        for update_file in update_dir.glob('agent-*.tar.gz'):
            # Remove both .tar.gz extensions to get just the version
            version = update_file.name.replace('agent-', '').replace('.tar.gz', '')
            hash_file = Path(str(update_file) + '.sha256')

            if hash_file.exists():
                with open(hash_file, 'r') as f:
                    sha256 = f.read().strip()
            else:
                # Calculate hash if not exists
                sha256 = hashlib.sha256()
                with open(update_file, 'rb') as f:
                    for chunk in iter(lambda: f.read(4096), b""):
                        sha256.update(chunk)
                sha256 = sha256.hexdigest()

            updates.append({
                'version': version,
                'platform': platform,
                'file_path': str(update_file),
                'file_size': update_file.stat().st_size,
                'sha256': sha256,
                'created_at': datetime.fromtimestamp(update_file.stat().st_mtime)
            })

    # Sort by platform and version
    updates.sort(key=lambda x: (x['platform'], x['version']), reverse=True)
    return updates


def get_version_distribution():
    """Get current agent version distribution across fleet"""
    version_stats = db.session.query(
        DeviceConnectivity.agent_version,
        db.func.count(DeviceConnectivity.deviceuuid).label('count')
    ).filter(
        DeviceConnectivity.agent_version.isnot(None)
    ).group_by(
        DeviceConnectivity.agent_version
    ).all()

    total_devices = Devices.query.count()
    devices_with_version = sum([stat.count for stat in version_stats])
    devices_without_version = total_devices - devices_with_version

    stats = []
    for version, count in version_stats:
        percentage = (count / total_devices * 100) if total_devices > 0 else 0
        stats.append({
            'version': version or 'Unknown',
            'count': count,
            'percentage': round(percentage, 1)
        })

    if devices_without_version > 0:
        percentage = (devices_without_version / total_devices * 100) if total_devices > 0 else 0
        stats.append({
            'version': 'No version reported',
            'count': devices_without_version,
            'percentage': round(percentage, 1)
        })

    # Sort by count descending
    stats.sort(key=lambda x: x['count'], reverse=True)

    return {
        'total_devices': total_devices,
        'versions': stats
    }


def get_update_history_stats():
    """Get statistics on recent update deployments"""
    recent_updates = AgentUpdateHistory.query.order_by(
        AgentUpdateHistory.initiated_at.desc()
    ).limit(100).all()

    if not recent_updates:
        return {
            'total_updates': 0,
            'successful': 0,
            'failed': 0,
            'pending': 0,
            'staged': 0,
            'success_rate': 0
        }

    total = len(recent_updates)
    successful = sum(1 for u in recent_updates if u.status == 'success')
    failed = sum(1 for u in recent_updates if u.status == 'failed')
    pending = sum(1 for u in recent_updates if u.status == 'pending')
    staged = sum(1 for u in recent_updates if u.status == 'staged')

    success_rate = (successful / total * 100) if total > 0 else 0

    return {
        'total_updates': total,
        'successful': successful,
        'failed': failed,
        'pending': pending,
        'staged': staged,
        'success_rate': round(success_rate, 1)
    }


@agent_updates_bp.route('/admin/agent-updates')
@admin_permission.require(http_exception=403)
def agent_updates_page():
    """Admin page for viewing and deploying agent updates"""
    log_with_route(logging.INFO, f"User {session.get('username', 'unknown')} is viewing agent updates page.")

    available_updates = get_available_updates()
    version_distribution = get_version_distribution()
    update_history_stats = get_update_history_stats()

    # Get recent update history
    recent_history = AgentUpdateHistory.query.order_by(
        AgentUpdateHistory.initiated_at.desc()
    ).limit(20).all()

    return render_template('administration/agent_updates.html',
                         available_updates=available_updates,
                         version_distribution=version_distribution,
                         update_history_stats=update_history_stats,
                         recent_history=recent_history)


@agent_updates_bp.route('/admin/agent-updates/deploy', methods=['POST'])
@admin_permission.require(http_exception=403)
def deploy_agent_update():
    """Deploy agent update via snippet scheduling"""
    log_with_route(logging.INFO, f"User {session.get('username', 'unknown')} is deploying an agent update.")

    try:
        data = request.json
        update_version = data.get('update_version')
        target_type = data.get('target_type')  # 'device', 'group', 'org', 'tenant'
        target_uuid = data.get('target_uuid')
        apply_mode = data.get('apply_mode', 'immediate')  # 'immediate' or 'scheduled_reboot'
        target_component = data.get('target_component', 'both')  # 'nats_agent', 'agent', 'both'
        platform = data.get('platform', 'Linux')

        if not all([update_version, target_type, target_uuid, platform]):
            return jsonify({'success': False, 'error': 'Missing required parameters'}), 400

        # Get update package info
        update_dir = Path(f'/opt/wegweiser/installerFiles/{platform}/updates')
        update_file = update_dir / f'agent-{update_version}.tar.gz'
        hash_file = Path(str(update_file) + '.sha256')

        if not update_file.exists():
            return jsonify({'success': False, 'error': f'Update package not found for version {update_version}'}), 404

        if not hash_file.exists():
            return jsonify({'success': False, 'error': 'Update hash file not found'}), 404

        with open(hash_file, 'r') as f:
            update_hash = f.read().strip()

        # Get or create AgentUpdate snippet
        snippet = Snippets.query.filter_by(snippetname='AgentUpdate.py').first()
        if not snippet:
            # Create default snippet for tenant 00000000-0000-0000-0000-000000000000
            snippet = Snippets(
                snippetuuid=uuid_lib.uuid4(),
                tenantuuid='00000000-0000-0000-0000-000000000000',
                snippetname='AgentUpdate.py',
                created_at=int(time.time()),
                max_exec_secs=600  # 10 minutes max execution time
            )
            db.session.add(snippet)
            db.session.commit()

        # Prepare snippet parameters
        snippet_params = {
            'UPDATE_VERSION': update_version,
            'UPDATE_URL': f'https://app.wegweiser.tech/download/updates/{platform.lower()}/agent-{update_version}.tar.gz',
            'UPDATE_HASH': update_hash,
            'APPLY_MODE': apply_mode,
            'TARGET_COMPONENT': target_component
        }

        # Schedule snippet based on target type
        devices_scheduled = []

        if target_type == 'device':
            device = Devices.query.filter_by(deviceuuid=target_uuid).first()
            if not device:
                return jsonify({'success': False, 'error': 'Device not found'}), 404

            upsertSnippetSchedule(
                deviceuuid=str(device.deviceuuid),
                snippetname=snippet.snippetname,
                parameters=snippet_params
            )
            devices_scheduled.append(str(device.deviceuuid))

            # Record update history
            history = AgentUpdateHistory(
                deviceuuid=device.deviceuuid,
                update_version=update_version,
                previous_version=DeviceConnectivity.query.filter_by(deviceuuid=device.deviceuuid).first().agent_version if DeviceConnectivity.query.filter_by(deviceuuid=device.deviceuuid).first() else None,
                apply_mode=apply_mode,
                target_component=target_component,
                status='pending'
            )
            db.session.add(history)

        elif target_type == 'group':
            devices = Devices.query.filter_by(groupuuid=target_uuid).all()
            for device in devices:
                upsertSnippetSchedule(
                    deviceuuid=str(device.deviceuuid),
                    snippetname=snippet.snippetname,
                    parameters=snippet_params
                )
                devices_scheduled.append(str(device.deviceuuid))

                # Record update history
                history = AgentUpdateHistory(
                    deviceuuid=device.deviceuuid,
                    update_version=update_version,
                    previous_version=DeviceConnectivity.query.filter_by(deviceuuid=device.deviceuuid).first().agent_version if DeviceConnectivity.query.filter_by(deviceuuid=device.deviceuuid).first() else None,
                    apply_mode=apply_mode,
                    target_component=target_component,
                    status='pending'
                )
                db.session.add(history)

        elif target_type == 'org':
            groups = Groups.query.filter_by(orguuid=target_uuid).all()
            for group in groups:
                devices = Devices.query.filter_by(groupuuid=group.groupuuid).all()
                for device in devices:
                    upsertSnippetSchedule(
                        deviceuuid=str(device.deviceuuid),
                        snippetname=snippet.snippetname,
                        parameters=snippet_params
                    )
                    devices_scheduled.append(str(device.deviceuuid))

                    # Record update history
                    history = AgentUpdateHistory(
                        deviceuuid=device.deviceuuid,
                        update_version=update_version,
                        previous_version=DeviceConnectivity.query.filter_by(deviceuuid=device.deviceuuid).first().agent_version if DeviceConnectivity.query.filter_by(deviceuuid=device.deviceuuid).first() else None,
                        apply_mode=apply_mode,
                        target_component=target_component,
                        status='pending'
                    )
                    db.session.add(history)

        elif target_type == 'tenant':
            orgs = Organisations.query.filter_by(tenantuuid=target_uuid).all()
            for org in orgs:
                groups = Groups.query.filter_by(orguuid=org.orguuid).all()
                for group in groups:
                    devices = Devices.query.filter_by(groupuuid=group.groupuuid).all()
                    for device in devices:
                        upsertSnippetSchedule(
                            deviceuuid=str(device.deviceuuid),
                            snippetname=snippet.snippetname,
                            parameters=snippet_params
                        )
                        devices_scheduled.append(str(device.deviceuuid))

                        # Record update history
                        history = AgentUpdateHistory(
                            deviceuuid=device.deviceuuid,
                            update_version=update_version,
                            previous_version=DeviceConnectivity.query.filter_by(deviceuuid=device.deviceuuid).first().agent_version if DeviceConnectivity.query.filter_by(deviceuuid=device.deviceuuid).first() else None,
                            apply_mode=apply_mode,
                            target_component=target_component,
                            status='pending'
                        )
                        db.session.add(history)

        db.session.commit()

        log_with_route(logging.INFO, f"Agent update {update_version} scheduled for {len(devices_scheduled)} devices")

        return jsonify({
            'success': True,
            'message': f'Update {update_version} scheduled for {len(devices_scheduled)} device(s)',
            'devices_scheduled': len(devices_scheduled)
        })

    except Exception as e:
        log_with_route(logging.ERROR, f"Error deploying agent update: {e}")
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500


@agent_updates_bp.route('/admin/agent-updates/history/<uuid:device_uuid>')
@admin_permission.require(http_exception=403)
def get_device_update_history(device_uuid):
    """Get update history for a specific device"""
    history = AgentUpdateHistory.query.filter_by(
        deviceuuid=device_uuid
    ).order_by(
        AgentUpdateHistory.initiated_at.desc()
    ).all()

    return jsonify({
        'success': True,
        'history': [h.to_dict() for h in history]
    })
