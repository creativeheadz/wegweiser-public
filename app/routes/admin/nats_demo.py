# Filepath: app/routes/admin/nats_demo.py
"""
NATS Streaming Demo Routes - Admin Only
Real-time system metrics streaming via NATS
"""

from flask import Blueprint, render_template, jsonify, request
from flask_principal import Permission, RoleNeed
from app import csrf
from app.utilities.app_logging_helper import log_with_route
from app.utilities.app_get_current_user import get_current_user
import logging

nats_demo_bp = Blueprint('nats_demo_bp', __name__)
admin_permission = Permission(RoleNeed('admin'))

@nats_demo_bp.route('/admin/nats-demo/dashboard')
@admin_permission.require(http_exception=403)
def dashboard():
    """Main NATS streaming demo dashboard"""
    user = get_current_user()
    user_email = user.companyemail if user else 'unknown'

    log_with_route(logging.INFO, f"NATS demo dashboard accessed by {user_email}")

    # Auto-start monitoring when dashboard is accessed
    try:
        from app.handlers.nats_demo.system_metrics import system_metrics_handler
        if not system_metrics_handler.running:
            import asyncio
            import threading
            from flask import current_app

            app = current_app._get_current_object()

            def start_async_monitoring():
                with app.app_context():
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    try:
                        loop.run_until_complete(system_metrics_handler.start_monitoring())
                    except Exception as e:
                        log_with_route(logging.ERROR, f"Error in async monitoring: {str(e)}")
                    finally:
                        loop.close()

            monitor_thread = threading.Thread(target=start_async_monitoring, daemon=True)
            monitor_thread.start()

            log_with_route(logging.INFO, f"NATS monitoring auto-started for {user_email}")
    except Exception as e:
        log_with_route(logging.ERROR, f"Error auto-starting NATS monitoring: {str(e)}")

    return render_template('administration/nats_demo_dashboard.html')

@nats_demo_bp.route('/admin/nats-demo/device/<device_uuid>')
@admin_permission.require(http_exception=403)
def device_monitor(device_uuid):
    """Single device monitoring page"""
    user = get_current_user()
    user_email = user.companyemail if user else 'unknown'
    
    log_with_route(logging.INFO, f"NATS device monitor for {device_uuid} accessed by {user_email}")
    
    return render_template('administration/nats_demo_dashboard.html', device_uuid=device_uuid)

@nats_demo_bp.route('/admin/nats-demo/api/metrics/<device_uuid>/<metric_type>')
@admin_permission.require(http_exception=403)
def get_metrics_history(device_uuid, metric_type):
    """Get historical metrics for charts"""
    from app.handlers.nats_demo.system_metrics import system_metrics_handler
    
    limit = request.args.get('limit', 50, type=int)
    metrics = system_metrics_handler.get_recent_metrics(device_uuid, metric_type, limit)
    
    return jsonify({
        'device_uuid': device_uuid,
        'metric_type': metric_type,
        'data': metrics
    })

@nats_demo_bp.route('/admin/nats-demo/api/start-monitoring', methods=['POST'])
@csrf.exempt
@admin_permission.require(http_exception=403)
def start_monitoring():
    """Start NATS metrics monitoring"""
    from app.handlers.nats_demo.system_metrics import system_metrics_handler
    
    user = get_current_user()
    user_email = user.companyemail if user else 'unknown'
    
    try:
        import asyncio
        
        # Start monitoring in background
        def start_async_monitoring():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                loop.run_until_complete(system_metrics_handler.start_monitoring())
            except Exception as e:
                log_with_route(logging.ERROR, f"Error in async monitoring: {str(e)}")
            finally:
                loop.close()
        
        import threading
        monitor_thread = threading.Thread(target=start_async_monitoring, daemon=True)
        monitor_thread.start()
        
        log_with_route(logging.INFO, f"NATS monitoring started by {user_email}")
        return jsonify({"success": True, "message": "Monitoring started"})
        
    except Exception as e:
        log_with_route(logging.ERROR, f"Error starting NATS monitoring: {str(e)}")
        return jsonify({"error": str(e)}), 500

@nats_demo_bp.route('/admin/nats-demo/api/status')
@admin_permission.require(http_exception=403)
def get_monitoring_status():
    """Get current monitoring status; lazily start if not running"""
    from app.handlers.nats_demo.system_metrics import system_metrics_handler

    # Lazy start: if not running, try to start in background
    if not system_metrics_handler.running:
        try:
            import threading, asyncio
            from flask import current_app

            app = current_app._get_current_object()

            def _start_bg():
                with app.app_context():
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    try:
                        loop.run_until_complete(system_metrics_handler.start_monitoring())
                    except Exception as e:
                        log_with_route(logging.ERROR, f"Lazy-start monitoring error: {e}")
                    finally:
                        loop.close()

            t = threading.Thread(target=_start_bg, daemon=True)
            t.start()
        except Exception as e:
            log_with_route(logging.ERROR, f"Unable to lazy-start monitoring: {e}")

    return jsonify({
        'running': system_metrics_handler.running,
        'active_connections': len(system_metrics_handler.active_connections),
        'devices_monitored': len(set(key.split('.')[0] for key in system_metrics_handler.metrics_buffer.keys())),
        'total_metrics': sum(len(buffer) for buffer in system_metrics_handler.metrics_buffer.values())
    })

@nats_demo_bp.route('/api/nats-demo/debug')
@csrf.exempt
def debug_status():
    """Debug endpoint - no auth required"""
    from app.handlers.nats_demo.system_metrics import system_metrics_handler

    buffer_info = {}
    for key, buffer in system_metrics_handler.metrics_buffer.items():
        buffer_info[key] = {
            'count': len(buffer),
            'latest': list(buffer)[-1] if buffer else None
        }

    return jsonify({
        'running': system_metrics_handler.running,
        'buffer_keys': list(system_metrics_handler.metrics_buffer.keys()),
        'buffer_info': buffer_info,
        'total_metrics': sum(len(buffer) for buffer in system_metrics_handler.metrics_buffer.values())
    })

@nats_demo_bp.route('/admin/nats-demo/api/agent/rpc', methods=['POST'])
@csrf.exempt
@admin_permission.require(http_exception=403)
def agent_rpc():
    """Send RPC command to agent via NATS"""
    import asyncio
    import uuid
    import json
    import time
    from app.utilities.nats_manager import nats_manager
    from app.models import Tenants

    user = get_current_user()
    user_email = user.companyemail if user else 'unknown'

    try:
        data = request.get_json()
        device_uuid = data.get('device_uuid')
        action = data.get('action')
        args = data.get('args', {})

        if not device_uuid or not action:
            return jsonify({'error': 'device_uuid and action are required'}), 400

        # Get tenant info (for now, use first tenant - will improve with proper device lookup)
        tenants = Tenants.query.all()
        if not tenants:
            return jsonify({'error': 'No tenants found'}), 500

        tenant_uuid = str(tenants[0].tenantuuid)

        # Create RPC request
        request_id = str(uuid.uuid4())
        rpc_request = {
            'action': action,
            'args': args,
            'request_id': request_id,
            'requested_by': user_email,
            'tenant_uuid': tenant_uuid,
            'timestamp': int(time.time() * 1000)
        }

        # Send via NATS command pattern (matching existing infrastructure)
        async def send_command():
            try:
                # Use direct NATS connection like the working agent
                import nats
                nc = await nats.connect("tls://nats.wegweiser.tech:443")

                # Send command
                command_subject = f"tenant.{tenant_uuid}.device.{device_uuid}.command"
                command_payload = {
                    'payload': {
                        'command': action,
                        'command_id': request_id,
                        'parameters': args
                    }
                }

                await nc.publish(command_subject, json.dumps(command_payload).encode())

                # Listen for response
                response_subject = f"tenant.{tenant_uuid}.device.{device_uuid}.response"
                response_received = asyncio.Event()
                response_data = {}

                async def response_handler(msg):
                    nonlocal response_data
                    try:
                        data = json.loads(msg.data.decode())
                        if data.get('command_id') == request_id:
                            response_data = data
                            response_received.set()
                    except Exception as e:
                        log_with_route(logging.ERROR, f"Error parsing response: {e}")

                # Subscribe to response
                sub = await nc.subscribe(response_subject, cb=response_handler)

                # Wait for response with timeout
                try:
                    await asyncio.wait_for(response_received.wait(), timeout=30.0)
                    await sub.unsubscribe()
                    return response_data.get('result', response_data)
                except asyncio.TimeoutError:
                    await sub.unsubscribe()
                    return {'error': 'Command timeout - agent did not respond'}
                finally:
                    # Clean up NATS connection
                    try:
                        await nc.close()
                    except:
                        pass

            except Exception as e:
                log_with_route(logging.ERROR, f"Command error: {str(e)}")
                return {'error': f'Command failed: {str(e)}'}

        # Run async function with proper event loop handling
        try:
            # Try to get existing event loop
            loop = asyncio.get_event_loop()
            if loop.is_closed():
                raise RuntimeError("Event loop is closed")
        except RuntimeError:
            # Create new event loop if none exists or is closed
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        try:
            result = loop.run_until_complete(send_command())
        except Exception as e:
            log_with_route(logging.ERROR, f"Event loop error: {str(e)}")
            # Try with a fresh loop as fallback
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                result = loop.run_until_complete(send_command())
            finally:
                loop.close()
        finally:
            # Only close if we created a new loop
            if not loop.is_running():
                loop.close()

        log_with_route(logging.INFO, f"Agent RPC {action} to {device_uuid} by {user_email}")

        return jsonify(result)

    except Exception as e:
        log_with_route(logging.ERROR, f"Agent RPC error: {str(e)}")
        return jsonify({'error': str(e)}), 500

@nats_demo_bp.route('/api/device/<device_uuid>/tenant')
def get_device_tenant(device_uuid):
    """Get tenant information for a device (for agent initialization)"""
    from app.models import Tenants, Devices

    try:
        # Look up the device to get its actual tenant
        device = Devices.query.filter_by(deviceuuid=device_uuid).first()
        if not device:
            # Try to restore from backup before returning error
            from app.utilities.device_restore import find_device_backup, restore_device_from_backup

            backup_path = find_device_backup(device_uuid)
            if backup_path:
                log_with_route(logging.INFO, f"Device {device_uuid} not found, attempting restoration from backup")
                success, message = restore_device_from_backup(device_uuid, backup_path)
                if success:
                    log_with_route(logging.INFO, f"Successfully restored device {device_uuid} from backup")
                    # Re-query the device after restoration
                    device = Devices.query.filter_by(deviceuuid=device_uuid).first()
                else:
                    log_with_route(logging.ERROR, f"Failed to restore device {device_uuid}: {message}")

            if not device:
                log_with_route(logging.ERROR, f"Device not found: {device_uuid}")
                return jsonify({'error': 'Device not found'}), 404

        # Get the device's actual tenant
        tenant = Tenants.query.filter_by(tenantuuid=device.tenantuuid).first()
        if not tenant:
            log_with_route(logging.ERROR, f"Tenant not found for device {device_uuid}")
            return jsonify({'error': 'Tenant not found'}), 404

        log_with_route(logging.INFO, f"Device {device_uuid} belongs to tenant {tenant.tenantuuid} ({tenant.tenantname})")

        return jsonify({
            'tenant_uuid': str(tenant.tenantuuid),
            'nats_server': 'tls://nats.wegweiser.tech:443',
            'device_uuid': device_uuid
        })

    except Exception as e:
        log_with_route(logging.ERROR, f"Error getting tenant info for device {device_uuid}: {str(e)}")
        return jsonify({'error': str(e)}), 500
