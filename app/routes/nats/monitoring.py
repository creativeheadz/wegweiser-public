# Filepath: app/routes/nats/monitoring.py
"""
NATS Monitoring Routes

Provides monitoring and health check endpoints for the NATS infrastructure,
including connection status, message flow metrics, and tenant-specific statistics.
"""

import json
import logging
import time
from typing import Dict, Any, List

from flask import request, jsonify, current_app
from sqlalchemy import func, text

from app import csrf

from app.models import db, Devices, Tenants, DeviceConnectivity
from app.utilities.app_logging_helper import log_with_route
try:
    from app.utilities.nats_manager import nats_manager, NATS_AVAILABLE
    from app.handlers.nats.message_handlers import nats_message_service
except ImportError:
    NATS_AVAILABLE = False
    nats_manager = None
    nats_message_service = None

from . import nats_bp


def require_nats(f):
    """Decorator to check if NATS is available"""
    def wrapper(*args, **kwargs):
        if not NATS_AVAILABLE:
            return jsonify({"error": "NATS functionality not available"}), 503
        return f(*args, **kwargs)
    wrapper.__name__ = f.__name__
    return wrapper


@nats_bp.route('/health', methods=['GET'])
@require_nats
def nats_health_check():
    """Health check for NATS infrastructure"""
    try:
        health_status = {
            'status': 'healthy',
            'timestamp': int(time.time()),
            'components': {
                'nats_server': 'unknown',
                'connection_manager': 'unknown',
                'database': 'unknown'
            },
            'metrics': {
                'active_connections': 0,
                'total_tenants': 0,
                'online_devices': 0
            }
        }
        
        # Check database connectivity
        try:
            db.session.execute(text('SELECT 1'))
            health_status['components']['database'] = 'healthy'
        except Exception as e:
            health_status['components']['database'] = 'unhealthy'
            health_status['status'] = 'degraded'
            log_with_route(logging.ERROR, f"Database health check failed: {str(e)}")
        
        # Check NATS connection manager
        try:
            connection_count = len(nats_manager.connections)
            health_status['components']['connection_manager'] = 'healthy'
            health_status['metrics']['active_connections'] = connection_count
        except Exception as e:
            health_status['components']['connection_manager'] = 'unhealthy'
            health_status['status'] = 'degraded'
            log_with_route(logging.ERROR, f"NATS connection manager health check failed: {str(e)}")
        
        # Get basic metrics
        try:
            tenant_count = Tenants.query.count()
            online_devices = DeviceConnectivity.query.filter_by(
                is_online=True,
                connection_type='nats'
            ).count()
            
            health_status['metrics']['total_tenants'] = tenant_count
            health_status['metrics']['online_devices'] = online_devices
        except Exception as e:
            log_with_route(logging.ERROR, f"Error getting metrics: {str(e)}")
        
        # Determine overall status
        unhealthy_components = [k for k, v in health_status['components'].items() if v == 'unhealthy']
        if unhealthy_components:
            health_status['status'] = 'unhealthy' if len(unhealthy_components) > 1 else 'degraded'
        
        return jsonify(health_status), 200
        
    except Exception as e:
        log_with_route(logging.ERROR, f"Health check failed: {str(e)}")
        return jsonify({
            'status': 'unhealthy',
            'error': str(e),
            'timestamp': int(time.time())
        }), 500


@nats_bp.route('/metrics', methods=['GET'])
def nats_metrics():
    """Get detailed NATS metrics"""
    try:
        current_time = int(time.time())
        
        # Connection metrics
        connection_metrics = {
            'active_connections': len(nats_manager.connections),
            'jetstream_contexts': len(nats_manager.jetstream_contexts),
            'tenant_credentials': len(nats_manager.tenant_credentials)
        }
        
        # Device connectivity metrics
        device_metrics = db.session.query(
            DeviceConnectivity.connection_type,
            func.count(DeviceConnectivity.deviceuuid).label('count'),
            func.sum(func.cast(DeviceConnectivity.is_online, db.Integer)).label('online_count')
        ).group_by(DeviceConnectivity.connection_type).all()
        
        connectivity_stats = {}
        for metric in device_metrics:
            connectivity_stats[metric.connection_type or 'unknown'] = {
                'total_devices': metric.count,
                'online_devices': metric.online_count or 0,
                'offline_devices': metric.count - (metric.online_count or 0)
            }
        
        # NATS-specific metrics
        nats_devices = DeviceConnectivity.query.filter_by(connection_type='nats').all()
        
        nats_stats = {
            'total_nats_devices': len(nats_devices),
            'online_nats_devices': sum(1 for d in nats_devices if d.is_online),
            'stale_nats_devices': 0,
            'recent_heartbeats': 0
        }
        
        # Calculate stale devices (no heartbeat in last 2 minutes)
        stale_threshold = current_time - 120
        for device in nats_devices:
            if device.last_heartbeat and device.last_heartbeat < stale_threshold:
                nats_stats['stale_nats_devices'] += 1
            elif device.last_heartbeat and device.last_heartbeat >= (current_time - 60):
                nats_stats['recent_heartbeats'] += 1
        
        # Tenant metrics
        tenant_stats = db.session.query(
            Tenants.tenantuuid,
            Tenants.tenantname,
            func.count(Devices.deviceuuid).label('device_count'),
            func.sum(func.cast(DeviceConnectivity.is_online, db.Integer)).label('online_count')
        ).outerjoin(
            Devices, Tenants.tenantuuid == Devices.tenantuuid
        ).outerjoin(
            DeviceConnectivity, Devices.deviceuuid == DeviceConnectivity.deviceuuid
        ).group_by(
            Tenants.tenantuuid, Tenants.tenantname
        ).all()
        
        tenant_metrics = []
        for stat in tenant_stats:
            tenant_metrics.append({
                'tenant_uuid': str(stat.tenantuuid),
                'tenant_name': stat.tenantname,
                'total_devices': stat.device_count or 0,
                'online_devices': stat.online_count or 0
            })
        
        return jsonify({
            'timestamp': current_time,
            'connection_metrics': connection_metrics,
            'connectivity_stats': connectivity_stats,
            'nats_stats': nats_stats,
            'tenant_metrics': tenant_metrics
        }), 200
        
    except Exception as e:
        log_with_route(logging.ERROR, f"Error getting NATS metrics: {str(e)}")
        return jsonify({'error': str(e)}), 500


@nats_bp.route('/tenant/<uuid:tenant_uuid>/metrics', methods=['GET'])
def tenant_nats_metrics(tenant_uuid):
    """Get NATS metrics for a specific tenant"""
    try:
        tenant_uuid_str = str(tenant_uuid)
        current_time = int(time.time())
        
        # Verify tenant exists
        tenant = Tenants.query.filter_by(tenantuuid=tenant_uuid_str).first()
        if not tenant:
            return jsonify({"error": "Tenant not found"}), 404
        
        # Get tenant devices with connectivity info
        devices_query = db.session.query(
            Devices,
            DeviceConnectivity
        ).outerjoin(
            DeviceConnectivity, Devices.deviceuuid == DeviceConnectivity.deviceuuid
        ).filter(
            Devices.tenantuuid == tenant_uuid_str
        ).all()
        
        tenant_metrics = {
            'tenant_uuid': tenant_uuid_str,
            'tenant_name': tenant.tenantname,
            'timestamp': current_time,
            'device_stats': {
                'total_devices': 0,
                'nats_devices': 0,
                'online_devices': 0,
                'offline_devices': 0,
                'stale_devices': 0,
                'node_red_devices': 0,
                'unknown_devices': 0
            },
            'connection_health': {
                'healthy_connections': 0,
                'stale_connections': 0,
                'failed_connections': 0
            },
            'recent_activity': {
                'heartbeats_last_minute': 0,
                'heartbeats_last_hour': 0,
                'last_activity': None
            }
        }
        
        stale_threshold = current_time - 120  # 2 minutes
        recent_threshold = current_time - 60   # 1 minute
        hour_threshold = current_time - 3600   # 1 hour
        
        latest_activity = 0
        
        for device, connectivity in devices_query:
            tenant_metrics['device_stats']['total_devices'] += 1
            
            if not connectivity:
                tenant_metrics['device_stats']['unknown_devices'] += 1
                continue
            
            # Connection type stats
            if connectivity.connection_type == 'nats':
                tenant_metrics['device_stats']['nats_devices'] += 1
            elif connectivity.connection_type == 'node-red':
                tenant_metrics['device_stats']['node_red_devices'] += 1
            else:
                tenant_metrics['device_stats']['unknown_devices'] += 1
            
            # Online/offline stats
            if connectivity.is_online:
                if connectivity.last_heartbeat and connectivity.last_heartbeat >= stale_threshold:
                    tenant_metrics['device_stats']['online_devices'] += 1
                    tenant_metrics['connection_health']['healthy_connections'] += 1
                else:
                    tenant_metrics['device_stats']['stale_devices'] += 1
                    tenant_metrics['connection_health']['stale_connections'] += 1
            else:
                tenant_metrics['device_stats']['offline_devices'] += 1
                tenant_metrics['connection_health']['failed_connections'] += 1
            
            # Activity tracking
            if connectivity.last_heartbeat:
                if connectivity.last_heartbeat >= recent_threshold:
                    tenant_metrics['recent_activity']['heartbeats_last_minute'] += 1
                if connectivity.last_heartbeat >= hour_threshold:
                    tenant_metrics['recent_activity']['heartbeats_last_hour'] += 1
                
                if connectivity.last_heartbeat > latest_activity:
                    latest_activity = connectivity.last_heartbeat
        
        if latest_activity > 0:
            tenant_metrics['recent_activity']['last_activity'] = latest_activity
        
        return jsonify(tenant_metrics), 200
        
    except Exception as e:
        log_with_route(logging.ERROR, f"Error getting tenant NATS metrics: {str(e)}")
        return jsonify({'error': str(e)}), 500


@nats_bp.route('/connections', methods=['GET'])
def nats_connections():
    """Get information about active NATS connections"""
    try:
        connections_info = {
            'timestamp': int(time.time()),
            'total_connections': len(nats_manager.connections),
            'connections': []
        }
        
        for tenant_uuid, connection in nats_manager.connections.items():
            try:
                # Get tenant info
                tenant = Tenants.query.filter_by(tenantuuid=tenant_uuid).first()
                tenant_name = tenant.tenantname if tenant else 'Unknown'
                
                # Get device count for tenant
                device_count = Devices.query.filter_by(tenantuuid=tenant_uuid).count()
                
                connection_info = {
                    'tenant_uuid': tenant_uuid,
                    'tenant_name': tenant_name,
                    'is_connected': connection.is_connected if hasattr(connection, 'is_connected') else False,
                    'device_count': device_count,
                    'has_jetstream': tenant_uuid in nats_manager.jetstream_contexts
                }
                
                connections_info['connections'].append(connection_info)
                
            except Exception as e:
                log_with_route(logging.ERROR, f"Error getting connection info for tenant {tenant_uuid}: {str(e)}")
                connections_info['connections'].append({
                    'tenant_uuid': tenant_uuid,
                    'tenant_name': 'Error',
                    'is_connected': False,
                    'device_count': 0,
                    'has_jetstream': False,
                    'error': str(e)
                })
        
        return jsonify(connections_info), 200
        
    except Exception as e:
        log_with_route(logging.ERROR, f"Error getting NATS connections: {str(e)}")
        return jsonify({'error': str(e)}), 500


@nats_bp.route('/debug/subjects', methods=['GET'])
def debug_nats_subjects():
    """Debug endpoint to show NATS subject structure"""
    try:
        # Get sample of devices to show subject patterns
        devices = db.session.query(
            Devices.deviceuuid,
            Devices.devicename,
            Devices.tenantuuid,
            Tenants.tenantname
        ).join(
            Tenants, Devices.tenantuuid == Tenants.tenantuuid
        ).limit(10).all()
        
        subject_examples = []
        
        for device in devices:
            device_uuid = str(device.deviceuuid)
            tenant_uuid = str(device.tenantuuid)
            
            subjects = {
                'device_uuid': device_uuid,
                'device_name': device.devicename,
                'tenant_uuid': tenant_uuid,
                'tenant_name': device.tenantname,
                'subjects': {
                    'heartbeat': f'tenant.{tenant_uuid}.device.{device_uuid}.heartbeat',
                    'command': f'tenant.{tenant_uuid}.device.{device_uuid}.command',
                    'response': f'tenant.{tenant_uuid}.device.{device_uuid}.response',
                    'status': f'tenant.{tenant_uuid}.device.{device_uuid}.status',
                    'monitoring': f'tenant.{tenant_uuid}.device.{device_uuid}.monitoring'
                },
                'wildcards': {
                    'all_device_messages': f'tenant.{tenant_uuid}.device.{device_uuid}.>',
                    'all_tenant_messages': f'tenant.{tenant_uuid}.>',
                    'all_tenant_devices': f'tenant.{tenant_uuid}.device.>'
                }
            }
            
            subject_examples.append(subjects)
        
        return jsonify({
            'timestamp': int(time.time()),
            'subject_pattern': 'tenant.{tenant_uuid}.device.{device_uuid}.{message_type}',
            'examples': subject_examples
        }), 200

    except Exception as e:
        log_with_route(logging.ERROR, f"Error getting subject debug info: {str(e)}")
        return jsonify({'error': str(e)}), 500


@nats_bp.route('/service/status', methods=['GET'])
def nats_service_status():
    """Get NATS message service status"""
    try:
        service_stats = nats_message_service.get_service_stats()

        return jsonify({
            'timestamp': int(time.time()),
            'service_status': service_stats
        }), 200

    except Exception as e:
        log_with_route(logging.ERROR, f"Error getting service status: {str(e)}")
        return jsonify({'error': str(e)}), 500


@nats_bp.route('/service/start', methods=['POST'])
@csrf.exempt
@require_nats
def start_nats_service():
    """Start NATS message processing service"""
    try:
        if nats_message_service.running:
            return jsonify({
                'success': False,
                'message': 'Service is already running'
            }), 400

        # Start service in background with Flask app context
        import asyncio
        import threading

        # Get the current app instance to pass to the thread
        app = current_app._get_current_object()

        def run_service():
            with app.app_context():
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    loop.run_until_complete(nats_message_service.start_message_processing())
                except Exception as e:
                    log_with_route(logging.ERROR, f"Error running NATS service: {str(e)}")
                finally:
                    loop.close()

        service_thread = threading.Thread(target=run_service, daemon=True)
        service_thread.start()

        return jsonify({
            'success': True,
            'message': 'NATS message service started'
        }), 200

    except Exception as e:
        log_with_route(logging.ERROR, f"Error starting NATS service: {str(e)}")
        return jsonify({'error': str(e)}), 500


@nats_bp.route('/service/start-get', methods=['GET'])
@require_nats
def start_nats_service_get():
    """Start NATS message processing service via GET (for testing)"""
    try:
        if nats_message_service.running:
            return jsonify({
                'success': False,
                'message': 'Service is already running'
            }), 400

        # Start service in background
        import asyncio
        import threading

        def run_service():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                loop.run_until_complete(nats_message_service.start_message_processing())
            except Exception as e:
                log_with_route(logging.ERROR, f"Error running NATS service: {str(e)}")
            finally:
                loop.close()

        service_thread = threading.Thread(target=run_service, daemon=True)
        service_thread.start()

        return jsonify({
            'success': True,
            'message': 'NATS message service started via GET'
        }), 200

    except Exception as e:
        log_with_route(logging.ERROR, f"Error starting NATS service: {str(e)}")
        return jsonify({'error': str(e)}), 500


@nats_bp.route('/agent-status', methods=['GET'])
def get_agent_status():
    """
    Get agent status counts for the current tenant.
    Returns online, stale, and offline agent counts.

    Status definitions:
    - Online: heartbeat within last 2 minutes
    - Stale: heartbeat between 2-10 minutes ago
    - Offline: heartbeat >10 minutes ago OR is_online=False
    """
    try:
        from flask import session

        # Get tenant UUID from session
        tenant_uuid = session.get('tenant_uuid')
        if not tenant_uuid:
            return jsonify({'error': 'Not authenticated or no tenant'}), 401

        # Get device connectivity stats for this tenant
        devices_with_connectivity = db.session.query(
            DeviceConnectivity
        ).join(
            Devices, Devices.deviceuuid == DeviceConnectivity.deviceuuid
        ).filter(
            Devices.tenantuuid == tenant_uuid
        ).all()

        current_time = int(time.time())
        online_threshold = current_time - 120   # 2 minutes
        stale_threshold = current_time - 600    # 10 minutes

        online_count = 0
        offline_count = 0
        stale_count = 0

        for connectivity in devices_with_connectivity:
            # If explicitly marked offline or no heartbeat ever received
            if not connectivity.is_online or not connectivity.last_heartbeat:
                offline_count += 1
            # If heartbeat is older than 10 minutes, consider offline
            elif connectivity.last_heartbeat < stale_threshold:
                offline_count += 1
            # If heartbeat is between 2-10 minutes, consider stale
            elif connectivity.last_heartbeat < online_threshold:
                stale_count += 1
            # If heartbeat is within last 2 minutes, consider online
            else:
                online_count += 1

        return jsonify({
            'success': True,
            'online': online_count,
            'offline': offline_count,
            'stale': stale_count,
            'total': online_count + offline_count + stale_count,
            'timestamp': current_time
        }), 200

    except Exception as e:
        log_with_route(logging.ERROR, f"Error getting agent status: {str(e)}")
        return jsonify({'error': str(e)}), 500
