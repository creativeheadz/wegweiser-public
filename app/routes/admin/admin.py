# Filepath: app/routes/admin/admin.py
# Filepath: app/routes/admin.py (add this to the existing file)
import math
from datetime import datetime, timedelta
import redis
from flask import jsonify
import json
from app.extensions import celery
import os
from flask import Blueprint, render_template, request, jsonify, session, flash, redirect, url_for
from flask_principal import Permission, RoleNeed
from app.models import (
    Tenants, Organisations, Groups, FAQ, Devices, DeviceMetadata, DeviceBattery,
    DeviceDrives, DeviceMemory, DeviceNetworks, DeviceStatus, DeviceUsers,
    DevicePartitions, DeviceCpu, DeviceGpu, DeviceBios, DeviceCollector,
    DevicePrinters, DevicePciDevices, DeviceUsbDevices, DeviceDrivers,
    DeviceRealtimeData, DeviceRealtimeHistory, DeviceConnectivity, Messages,
    Tags, TagsXDevices, TagsXOrgs, TagsXGroups, TagsXTenants, TagsXAccounts, Accounts, UserXOrganisation,
    TenantMetadata, OrganizationMetadata, GroupMetadata, AIMemory, Context,
    Conversations, WegcoinTransaction, HealthScoreHistory, Snippets, SnippetsHistory,
    Profiles, MFA, RSSFeed
)
from app.models.email_verification import EmailVerification
from app.models.two_factor import UserTwoFactor
from app.models import db, GuidedTour, TourProgress
from app.utilities.app_logging_helper import log_with_route, reload_logging_config, update_logging_config, _logging_config
from app.utilities.app_get_current_user import get_current_user
from app.utilities.guided_tour_manager import create_tour, get_all_tours, get_tour_for_page, update_tour_steps, deactivate_tour
import logging
from sqlalchemy import text, inspect
from sqlalchemy.dialects.postgresql import UUID
import time
import subprocess
import uuid



admin_bp = Blueprint('admin_bp', __name__)
admin_permission = Permission(RoleNeed('admin'))
#csrf = CSRFProtect()

def get_admin_redis_client():
    """Get Redis client using environment variables"""
    host = os.getenv('ADMIN_REDIS_HOST')
    port = int(os.getenv('ADMIN_REDIS_PORT', '6379'))
    password = os.getenv('ADMIN_REDIS_PASSWORD')

    if not host:
        raise RuntimeError("ADMIN_REDIS_HOST environment variable is required")
    if not password:
        raise RuntimeError("ADMIN_REDIS_PASSWORD environment variable is required")

    return redis.Redis(
        host=host,
        port=port,
        password=password,
        decode_responses=True
    )


# View Tenants
@admin_bp.route('/admin/tenants')
@admin_permission.require(http_exception=403)
def view_tenants():
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    search_query = request.args.get('search', '', type=str)

    log_with_route(logging.INFO, f"User {session.get('username', 'unknown')} is viewing tenants page {page} with search query '{search_query}'.")

    if search_query:
        tenants_query = Tenants.query.filter(Tenants.tenantname.ilike(f'%{search_query}%'))
    else:
        tenants_query = Tenants.query

    tenants_pagination = tenants_query.paginate(page=page, per_page=per_page, error_out=False)
    tenants = tenants_pagination.items

    tenant_data = []
    for tenant in tenants:
        orgs = Organisations.query.filter_by(tenantuuid=tenant.tenantuuid).all()
        org_data = []
        for org in orgs:
            groups = Groups.query.filter_by(orguuid=org.orguuid).all()
            group_data = [{'groupuuid': group.groupuuid, 'groupname': group.groupname} for group in groups]
            org_data.append({'orguuid': org.orguuid, 'orgname': org.orgname, 'groups': group_data})
        tenant_data.append({'tenantuuid': tenant.tenantuuid, 'tenantname': tenant.tenantname, 'organisations': org_data})

    log_with_route(logging.DEBUG, f"Tenant data: {tenant_data}")

    return render_template('administration/admin_tenants.html',
                           tenants=tenant_data,
                           pagination=tenants_pagination,
                           search_query=search_query,
                           per_page=per_page)

# Logs Routes

def tail(file_path, lines=50):
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            return ''.join(f.readlines()[-lines:])
    except Exception as e:
        log_with_route(logging.ERROR, f"Error reading file {file_path}: {e}")
        return str(e)


@admin_bp.route('/admin/logs/nginx/access')
@admin_permission.require(http_exception=403)
def nginx_access_log():
    log_path = '/var/log/nginx/access.log'
    if os.path.exists(log_path):
        log_with_route(logging.INFO, f"Access log requested by user {session.get('username', 'unknown')}.")
        output = tail(log_path)
    else:
        log_with_route(logging.WARNING, f"Access log file not found: {log_path}")
        output = f'File not found: {log_path}'
    return jsonify(output)

@admin_bp.route('/admin/logs/nginx/error')
@admin_permission.require(http_exception=403)
def nginx_error_log():
    log_path = '/var/log/nginx/error.log'
    if os.path.exists(log_path):
        log_with_route(logging.INFO, f"Error log requested by user {session.get('username', 'unknown')}.")
        output = tail(log_path)
    else:
        log_with_route(logging.WARNING, f"Error log file not found: {log_path}")
        output = f'File not found: {log_path}'
    return jsonify(output)

@admin_bp.route('/admin/logs/nginx/filtered')
@admin_permission.require(http_exception=403)
def nginx_filtered_log():
    log_path = '/var/log/nginx/access.log'
    exclude_ips = {'81.150.150.132', '194.164.19.215'}

    try:
        if not os.path.exists(log_path):
            log_with_route(logging.WARNING, f"Filtered log file not found: {log_path}")
            return jsonify(f'File not found: {log_path}'), 404

        log_with_route(logging.INFO, f"Filtered log requested by user {session.get('username', 'unknown')}.")

        with open(log_path, 'r') as f:
            lines = f.readlines()

        filtered_lines = [line for line in lines if not any(ip in line for ip in exclude_ips)]

        log_data = {}
        for line in filtered_lines:
            parts = line.split()
            if len(parts) >= 12:
                ip = parts[0]
                url = parts[6]
                user_agent = parts[11]
                key = (ip, url, user_agent)
                if key not in log_data:
                    log_data[key] = 0
                log_data[key] += 1

        sorted_log_data = sorted(log_data.items(), key=lambda item: item[1], reverse=True)
        result = '\n'.join([f'{count} {ip} {url} {user_agent}' for (ip, url, user_agent), count in sorted_log_data])

        return jsonify(result)
    except Exception as e:
        log_with_route(logging.ERROR, f"Failed to process log data: {e}")
        return jsonify(f"Failed to process log data: {e}"), 500


@admin_bp.route('/admin/logs')
@admin_permission.require(http_exception=403)
def logs():
    # Updating the path to wegweiser.log to the new location
    wegweiser_log_path = 'wlog/wegweiser.log'
    log_with_route(logging.INFO, f"Logs page requested by user {session.get('username', 'unknown')}.")

    return render_template('administration/admin_logs.html', wegweiser_log=tail(wegweiser_log_path))

@admin_bp.route('/admin/design')
@admin_permission.require(http_exception=403)
def design():
    # Updating the path to wegweiser.log to the new location
    log_with_route(logging.INFO, f"Design page requested by user {session.get('username', 'unknown')}.")

    return render_template('administration/admin_design.html')



@admin_bp.route('/admin/devices/manage')
@admin_permission.require(http_exception=403)
def devices_manage():
    user = get_current_user()
    if user:
        user_email = user.companyemail
        user_id = user.useruuid
    else:
        user_email = 'unknown'
        user_id = 'unknown'

    log_with_route(logging.INFO, f"Devices management page requested by user {user_email} (ID: {user_id}).")

    try:
        # Use the same optimized query logic as devices.py for consistent online/offline status
        query = text("""
            SELECT
                d.deviceuuid,
                d.devicename,
                d.hardwareinfo,
                d.health_score,
                d.orguuid,
                d.groupuuid,
                d.tenantuuid,
                t.tenantname,
                o.orgname,
                g.groupname,
                dc.is_online,
                COALESCE(ds.last_update, dc.last_seen_online) as last_seen_online,
                CASE
                    WHEN dc.is_online THEN 'Online'
                    ELSE 'Offline'
                END as status
            FROM devices d
            LEFT JOIN tenants t ON d.tenantuuid = t.tenantuuid
            LEFT JOIN organisations o ON d.orguuid = o.orguuid
            LEFT JOIN groups g ON d.groupuuid = g.groupuuid
            LEFT JOIN deviceconnectivity dc ON d.deviceuuid = dc.deviceuuid
            LEFT JOIN devicestatus ds ON d.deviceuuid = ds.deviceuuid
            ORDER BY t.tenantname, o.orgname, g.groupname, d.devicename
        """)

        result = db.session.execute(query)
        devices_data = result.fetchall()

        # Group devices by tenant
        devices_by_tenant = {}
        for row in devices_data:
            tenant_name = row.tenantname or 'Unknown Tenant'

            if tenant_name not in devices_by_tenant:
                devices_by_tenant[tenant_name] = []

            # Create a device-like object for template compatibility
            device_info = {
                'deviceuuid': str(row.deviceuuid),
                'devicename': row.devicename,
                'hardwareinfo': row.hardwareinfo,
                'health_score': row.health_score or 0,
                'orguuid': str(row.orguuid),
                'groupuuid': str(row.groupuuid),
                'tenantuuid': str(row.tenantuuid)
            }

            # Format last_seen timestamp
            last_heartbeat = None
            if row.last_seen_online:
                try:
                    last_heartbeat = row.last_seen_online
                except (ValueError, TypeError):
                    last_heartbeat = None

            device_info['last_heartbeat'] = last_heartbeat

            devices_by_tenant[tenant_name].append({
                'device': type('Device', (), device_info)(),  # Create object-like structure
                'tenant_name': tenant_name,
                'org_name': row.orgname or 'Unknown Organization',
                'group_name': row.groupname or 'Unknown Group',
                'online_status': row.status,
                'health_score': row.health_score or 0
            })

        return render_template('administration/admin_devices.html', devices_by_tenant=devices_by_tenant)

    except Exception as e:
        log_with_route(logging.ERROR, f"Error in devices_manage: {str(e)}")
        return render_template('error.html', message=str(e)), 500



@admin_bp.route('/admin/run_all_ai_utilities')
@admin_permission.require(http_exception=403)
def run_all_ai_utilities():
    try:
        log_with_route(logging.INFO, "Running all AI utility scripts.")

        # Import the correct task function
        from app.utilities.ai_system_software_config_analysis import run_system_software_config_analysis_task

        # Run the Celery task asynchronously
        run_system_software_config_analysis_task.delay()

        log_with_route(logging.INFO, "All AI utility scripts executed successfully.")
        return jsonify({"status": "success", "message": "All AI utilities executed successfully."})

    except Exception as e:
        log_with_route(logging.ERROR, f"Error running AI utility scripts: {e}")
        return jsonify({"status": "error", "message": f"Failed to execute AI utilities: {e}"}), 500

@admin_bp.route('/admin/test_ai_utility')
@admin_permission.require(http_exception=403)
def test_ai_utility():
    try:
        from app.utilities.ai_auth_filtered import run as auth_filtered
        auth_filtered()
        log_with_route(logging.INFO, "AI utility executed successfully.")
        return jsonify({"status": "success", "message": "AI utility executed successfully."})
    except Exception as e:
        log_with_route(logging.ERROR, f"Error running AI utility: {e}")
        return jsonify({"status": "error", "message": f"Failed to execute AI utility: {e}"}), 500



@admin_bp.route('/admin/logs')
@admin_permission.require(http_exception=403)
def view_logs():
    user = get_current_user()
    if user:
        user_email = user.companyemail
        user_id = user.useruuid
    else:
        user_email = 'unknown'
        user_id = 'unknown'

    log_with_route(logging.INFO, f"Log viewer accessed by user {user_email} (ID: {user_id}).")
    return render_template('administration/admin_logs.html')

@admin_bp.route('/api/logs')
@admin_permission.require(http_exception=403)
def get_logs():
    try:
        limit = int(request.args.get('limit', 100))
        level = request.args.get('level')
        source_type = request.args.get('source_type')
        time_filter = request.args.get('time')

        start_time = None
        if time_filter:
            if time_filter == '1h':
                start_time = datetime.utcnow() - timedelta(hours=1)
            elif time_filter == '24h':
                start_time = datetime.utcnow() - timedelta(days=1)
            elif time_filter == '7d':
                start_time = datetime.utcnow() - timedelta(days=7)

        logs = get_logs_from_redis(limit, level, source_type, start_time)
        return jsonify({'logs': logs})
    except Exception as e:
        log_with_route(logging.ERROR, f"Error fetching logs: {str(e)}")
        return jsonify({'error': 'Failed to fetch logs'}), 500

        # Add to your admin.py route file

@admin_bp.route('/api/logs/metrics')
@admin_permission.require(http_exception=403)
def get_log_metrics():
    try:
        redis_client = get_admin_redis_client()

        # Get total logs count
        total_logs = redis_client.llen('wegweiser_logs')

        # Calculate error rate for last 24h
        errors = 0
        total = 0
        now = datetime.utcnow()
        logs = redis_client.lrange('wegweiser_logs', 0, 1000)  # Get last 1000 logs for sampling

        for log_data in logs:
            try:
                log = json.loads(log_data)
                log_time = datetime.fromisoformat(log['created_at'])
                if now - log_time <= timedelta(hours=24):
                    total += 1
                    if log.get('level') == 'ERROR':
                        errors += 1
            except json.JSONDecodeError:
                continue

        error_rate = round((errors / total * 100) if total > 0 else 0, 2)

        # Calculate logs per minute (last 5 minutes)
        recent_logs = 0
        five_mins_ago = now - timedelta(minutes=5)

        for log_data in logs[:100]:  # Sample last 100 logs for recent activity
            try:
                log = json.loads(log_data)
                log_time = datetime.fromisoformat(log['created_at'])
                if log_time >= five_mins_ago:
                    recent_logs += 1
            except json.JSONDecodeError:
                continue

        logs_per_minute = round(recent_logs / 5, 1)

        # Get average health score from Redis if available
        try:
            avg_health_score = round(float(redis_client.get('avg_health_score') or 0), 2)
        except:
            avg_health_score = 0

        return jsonify({
            'total_logs': total_logs,
            'error_rate': error_rate,
            'logs_per_minute': logs_per_minute,
            'avg_health_score': avg_health_score
        })

    except Exception as e:
        log_with_route(logging.ERROR, f"Error fetching log metrics: {str(e)}")
        return jsonify({'error': 'Failed to fetch metrics'}), 500


@admin_bp.route('/admin/celery-tasks')
@admin_permission.require(http_exception=403)
def celery_tasks():
    # Get the Celery beat schedule
    beat_schedule = celery.conf.beat_schedule

    # Convert the schedule to a list of dictionaries
    tasks = [
        {
            'name': name,
            'schedule': schedule.get('schedule'),
            'args': schedule.get('args', ()),
            'kwargs': schedule.get('kwargs', {}),
            'last_run_at': schedule.get('last_run_at'),
            'total_run_count': schedule.get('total_run_count', 0),
        }
        for name, schedule in beat_schedule.items()
    ]

    return render_template('administration/admin_celery.html', tasks=tasks)

@admin_bp.route('/api/ip-blocker/lists')
@admin_permission.require(http_exception=403)
def get_ip_lists():
    """Get both whitelist and blocklist with pagination and search"""
    try:
        # Get pagination parameters
        whitelist_page = int(request.args.get('whitelist_page', 1))
        blacklist_page = int(request.args.get('blacklist_page', 1))
        failed_page = int(request.args.get('failed_page', 1))
        per_page = int(request.args.get('per_page', 10))
        search = request.args.get('search', '').lower()

        redis_client = get_admin_redis_client()

        try:
            # Get whitelist
            # Get whitelist
            all_whitelist = redis_client.smembers("wegweiser:ip_blocker:whitelist") or set()
            whitelist_data = []
            for ip in all_whitelist:
                if not search or search in ip.lower():
                    try:
                        data = redis_client.hgetall(f"wegweiser:ip_blocker:whitelist_data:{ip}") or {}
                        # Check both possible timestamp keys and set if missing
                        if not data or ('added_date' not in data and 'timestamp' not in data):
                            timestamp = str(int(time.time()))
                            redis_client.hset(f"wegweiser:ip_blocker:whitelist_data:{ip}",
                                            mapping={
                                                "added_date": timestamp,
                                                "added_by": "System (timestamp restored)"
                                            })
                            whitelist_data.append({
                                "ip": ip,
                                "added_date": int(timestamp),
                                "added_by": "System (timestamp restored)"
                            })
                        else:
                            timestamp = data.get('added_date') or data.get('timestamp')
                            whitelist_data.append({
                                "ip": ip,
                                "added_date": int(timestamp),
                                "added_by": data.get('added_by', 'Unknown')
                            })
                    except redis.ResponseError:
                        whitelist_data.append({
                            "ip": ip,
                            "added_date": int(time.time()),
                            "added_by": "System (error recovery)"
                        })

            # Get blacklist
            all_blacklist = redis_client.smembers("wegweiser:ip_blocker:blacklist") or set()
            blacklist_data = []
            for ip in all_blacklist:
                if not search or search in ip.lower():
                    try:
                        data = redis_client.hgetall(f"wegweiser:ip_blocker:blacklist_data:{ip}") or {}
                        block_timestamp = data.get('block_info_timestamp')

                        if block_timestamp:
                            try:
                                # Store both timestamp and formatted date
                                timestamp = int(block_timestamp)
                                block_date = datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d %H:%M:%S")
                            except (ValueError, TypeError):
                                timestamp = int(time.time())
                                block_date = datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d %H:%M:%S")
                                log_with_route(logging.WARNING, f"Invalid block timestamp for IP {ip}: {block_timestamp}")
                        else:
                            timestamp = int(time.time())
                            block_date = datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d %H:%M:%S")
                            log_with_route(logging.WARNING, f"No block timestamp found for IP {ip}")

                        blacklist_data.append({
                            "ip": ip,
                            "block_date": block_date,
                            "timestamp": timestamp,  # Include raw timestamp for sorting
                            "network": data.get('whois_data_network_info_name', 'Unknown'),
                            "country": data.get('whois_data_network_info_country', 'Unknown'),
                            "description": data.get('whois_data_network_info_description', 'No description available'),
                            "abuse_contacts": json.loads(data.get('whois_data_contacts_abuse', '[]')),
                            "block_info_trigger_url": data.get('block_info_trigger_url'),
                            "block_info_reason": data.get('block_info_reason')
                        })
                    except redis.ResponseError:
                        blacklist_data.append({
                            "ip": ip,
                            "block_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                            "timestamp": int(time.time()),
                            "network": "Unknown",
                            "country": "Unknown",
                            "description": "No description available",
                            "abuse_contacts": [],
                            "block_info_trigger_url": None,
                            "block_info_reason": None
                        })

            # Get failed requests
            failed_requests = []
            failed_pattern = "wegweiser:ip_blocker:failed:*:count"
            count_keys = redis_client.keys(failed_pattern)

            for count_key in count_keys:
                ip = count_key.split(':')[-2]  # Get IP from key pattern
                if not search or search in ip.lower():
                    try:
                        count = redis_client.get(count_key)
                        if count:
                            # Try to get history
                            history_key = f"wegweiser:ip_blocker:failed:{ip}:history"
                            try:
                                latest_request = redis_client.lindex(history_key, 0)
                                if latest_request:
                                    latest_data = json.loads(latest_request)
                                    last_failure = latest_data.get('timestamp')
                                else:
                                    last_failure = int(time.time())
                            except (redis.ResponseError, json.JSONDecodeError):
                                last_failure = int(time.time())

                            failed_requests.append({
                                "ip": ip,
                                "count": int(count),
                                "last_failure": last_failure,
                                "network_info": "See blacklist for details"
                            })
                    except redis.ResponseError:
                        continue

            def paginate(items, page, per_page, sort_key='ip'):
                total_items = len(items)
                if sort_key == 'block_date':
                    # Sort by timestamp directly
                    sorted_items = sorted(items,
                                       key=lambda x: x.get('timestamp', 0),
                                       reverse=True)
                else:
                    sorted_items = sorted(items, key=lambda x: x[sort_key])

                start_idx = (page - 1) * per_page
                end_idx = start_idx + per_page
                return {
                    "total": total_items,
                    "pages": math.ceil(total_items / per_page),
                    "current_page": page,
                    "items": sorted_items[start_idx:end_idx]
                }

            return jsonify({
                "success": True,
                "whitelist": paginate(whitelist_data, whitelist_page, per_page),
                "blacklist": paginate(blacklist_data, blacklist_page, per_page, sort_key='block_date'),
                "failed_requests": paginate(failed_requests, failed_page, per_page)
            })

        except redis.RedisError as e:
            log_with_route(logging.ERROR, f"Redis operation error: {str(e)}")
            return jsonify({"success": False, "error": f"Redis operation error: {str(e)}"}), 500

    except Exception as e:
        log_with_route(logging.ERROR, f"Failed to fetch IP lists: {str(e)}")
        return jsonify({"success": False, "error": f"Failed to fetch IP lists: {str(e)}"}), 500

@admin_bp.route('/api/ip-blocker/failed-requests')
@admin_permission.require(http_exception=403)
def get_failed_requests():
    """Get failed request counts"""
    try:
        redis_client = get_admin_redis_client()
        keys = redis_client.keys("wegweiser:ip_blocker:failed:*")
        failed_requests = {}
        for key in keys:
            ip = key.split(":")[-1]
            count = redis_client.get(key)
            if count:
                failed_requests[ip] = int(count)
        return jsonify({
            "success": True,
            "failed_requests": failed_requests
        })
    except Exception as e:
        log_with_route(logging.ERROR, f"Failed to fetch failed requests: {str(e)}")
        return jsonify({"success": False, "error": "Failed to fetch failed requests"}), 500

@admin_bp.route('/api/ip-blocker/whitelist', methods=['POST', 'DELETE'])
@admin_permission.require(http_exception=403)
def manage_whitelist():
    try:
        data = request.get_json()
        ip = data.get('ip')

        if not ip:
            return jsonify({"success": False, "reason": "IP address required"}), 400

        redis_client = get_admin_redis_client()

        if request.method == 'DELETE':
            if redis_client.srem("wegweiser:ip_blocker:whitelist", ip):
                redis_client.delete(f"wegweiser:ip_blocker:whitelist_data:{ip}")
                return jsonify({"success": True, "reason": "IP removed from whitelist"})
            return jsonify({"success": False, "reason": "IP not found in whitelist"}), 404

        elif request.method == 'POST':
            # First check if IP is valid
            ip_parts = ip.split('.')
            if len(ip_parts) != 4 or not all(part.isdigit() and 0 <= int(part) <= 255 for part in ip_parts):
                return jsonify({"success": False, "reason": "Invalid IP address format"}), 400

            # If IP is currently blocked, unblock it first
            if redis_client.sismember("wegweiser:ip_blocker:blacklist", ip):
                subprocess.run([
                    'sudo', '/usr/sbin/iptables',
                    '-D', 'INPUT',
                    '-s', ip,
                    '-j', 'DROP'
                ], check=True)
                redis_client.srem("wegweiser:ip_blocker:blacklist", ip)
                redis_client.delete(f"wegweiser:ip_blocker:blacklist_data:{ip}")

            # Add to whitelist with timestamp and user info
            redis_client.sadd("wegweiser:ip_blocker:whitelist", ip)
            redis_client.hset(
                f"wegweiser:ip_blocker:whitelist_data:{ip}",
                mapping={
                    "added_date": str(int(time.time())),
                    "added_by": session.get('username', 'unknown')
                }
            )

            # Clear any failed request history
            redis_client.delete(f"wegweiser:ip_blocker:failed:{ip}:count")
            redis_client.delete(f"wegweiser:ip_blocker:failed:{ip}:history")

            log_with_route(logging.INFO, f"Added IP {ip} to whitelist by {session.get('username', 'unknown')}")
            return jsonify({"success": True, "reason": "IP added to whitelist"})

    except Exception as e:
        log_with_route(logging.ERROR, f"Error managing whitelist: {str(e)}")
        return jsonify({"success": False, "reason": str(e)}), 500

@admin_bp.route('/api/ip-blocker/unblock', methods=['POST'])
@admin_permission.require(http_exception=403)
def unblock_ip_api():
    """Unblock an IP address"""
    try:
        data = request.get_json()
        ip = data.get('ip')
        if not ip:
            return jsonify({"success": False, "reason": "IP address required"}), 400

        redis_client = get_admin_redis_client()
        if redis_client.srem("wegweiser:ip_blocker:blacklist", ip):
            # Also remove any failed request counts
            redis_client.delete(f"wegweiser:ip_blocker:failed:{ip}")
            return jsonify({"success": True, "reason": "IP unblocked successfully"})
        return jsonify({"success": False, "reason": "IP not found in blocklist"}), 404
    except Exception as e:
        log_with_route(logging.ERROR, f"Error unblocking IP: {str(e)}")
        return jsonify({"success": False, "reason": str(e)}), 500

@admin_bp.route('/api/ip-blocker/history/<ip>')
@admin_permission.require(http_exception=403)
def get_ip_history(ip):
    try:
        redis_client = get_admin_redis_client()

        # Get block data
        block_data = redis_client.hgetall(f"wegweiser:ip_blocker:blacklist_data:{ip}")

        # Get history - check both current failed requests and blocked history
        history = []

        # Check current failed requests history
        failed_history_key = f"wegweiser:ip_blocker:failed:{ip}:history"
        try:
            raw_failed = redis_client.lrange(failed_history_key, 0, -1)
            for entry in raw_failed:
                try:
                    history.append(json.loads(entry))
                except json.JSONDecodeError:
                    continue
        except redis.RedisError:
            pass

        # Check blocked history
        if 'request_history' in block_data:
            try:
                blocked_history = json.loads(block_data['request_history'])
                if isinstance(blocked_history, list):
                    history.extend(blocked_history)
            except json.JSONDecodeError:
                pass

        # Sort history by timestamp
        history.sort(key=lambda x: x.get('timestamp', 0), reverse=True)

        return jsonify({
            "success": True,
            "history": history,
            "block_info_reason": block_data.get('block_info_reason', 'Unknown'),
            "block_info_trigger_url": block_data.get('block_info_trigger_url', 'Unknown')
        })

    except Exception as e:
        log_with_route(logging.ERROR, f"Failed to fetch IP history: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500

@admin_bp.route('/admin/ip-blocker')
@admin_permission.require(http_exception=403)
def view_ip_blocker():
    """Render the IP blocker management page."""
    log_with_route(logging.INFO, "IP Blocker page accessed by admin.")
    return render_template('administration/admin_ipblocker.html')

# Logging Configuration Routes
@admin_bp.route('/admin/logging-config')
@admin_permission.require(http_exception=403)
def logging_config():
    """Render the logging configuration page."""
    user = get_current_user()
    user_email = user.companyemail if user else 'unknown'
    log_with_route(logging.INFO, f"Logging configuration page accessed by {user_email}.")
    return render_template('administration/admin_logging_config.html')

@admin_bp.route('/api/logging-config')
@admin_permission.require(http_exception=403)
def get_logging_config():
    """Get current logging configuration."""
    try:
        config = reload_logging_config()
        return jsonify({
            "success": True,
            "config": config
        })
    except Exception as e:
        log_with_route(logging.ERROR, f"Error getting logging config: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500

@admin_bp.route('/api/logging-config', methods=['POST'])
@admin_permission.require(http_exception=403)
def update_logging_config_api():
    """Update logging configuration."""
    try:
        data = request.get_json()
        if not data or 'levels' not in data:
            return jsonify({"success": False, "error": "Invalid request data"}), 400

        user = get_current_user()
        user_email = user.companyemail if user else 'unknown'

        # Validate the levels data
        valid_levels = ['INFO', 'DEBUG', 'ERROR', 'WARNING']
        levels = data['levels']

        if not isinstance(levels, dict):
            return jsonify({"success": False, "error": "Levels must be a dictionary"}), 400

        for level, enabled in levels.items():
            if level not in valid_levels:
                return jsonify({"success": False, "error": f"Invalid logging level: {level}"}), 400
            if not isinstance(enabled, bool):
                return jsonify({"success": False, "error": f"Level {level} must be boolean"}), 400

        # Update the configuration
        if update_logging_config(levels, user_email):
            log_with_route(logging.INFO, f"Logging configuration updated by {user_email}: {levels}")
            return jsonify({
                "success": True,
                "message": "Logging configuration updated successfully"
            })
        else:
            return jsonify({"success": False, "error": "Failed to save configuration"}), 500

    except Exception as e:
        log_with_route(logging.ERROR, f"Error updating logging config: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500

@admin_bp.route('/api/logging-config/reload', methods=['POST'])
@admin_permission.require(http_exception=403)
def reload_logging_config_api():
    """Reload logging configuration from file."""
    try:
        user = get_current_user()
        user_email = user.companyemail if user else 'unknown'

        config = reload_logging_config()
        log_with_route(logging.INFO, f"Logging configuration reloaded by {user_email}")

        return jsonify({
            "success": True,
            "message": "Logging configuration reloaded successfully",
            "config": config
        })
    except Exception as e:
        log_with_route(logging.ERROR, f"Error reloading logging config: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500


# FAQ Management Routes
@admin_bp.route('/admin/faq')
@admin_permission.require(http_exception=403)
def manage_faq():
    """Render the FAQ management page."""
    user = get_current_user()
    user_email = user.companyemail if user else 'unknown'
    log_with_route(logging.INFO, f"FAQ management page accessed by {user_email}.")

    # Get all FAQs ordered by order column
    faqs = FAQ.query.order_by(FAQ.order.asc()).all()

    # Convert to dictionaries for JSON serialization in template
    faqs_dict = [faq.to_dict() for faq in faqs]

    return render_template('administration/admin_faq.html', faqs=faqs, faqs_json=faqs_dict)


@admin_bp.route('/admin/faq/create', methods=['POST'])
@admin_permission.require(http_exception=403)
def create_faq():
    """Create a new FAQ."""
    try:
        question = request.form.get('question', '').strip()
        answer = request.form.get('answer', '').strip()
        order = request.form.get('order', type=int)

        if not question or not answer:
            flash('Question and answer are required.', 'error')
            return redirect(url_for('admin_bp.manage_faq'))

        # If no order specified, put it at the end
        if order is None:
            max_order = db.session.query(db.func.max(FAQ.order)).scalar() or 0
            order = max_order + 1

        # Create new FAQ
        new_faq = FAQ(
            question=question,
            answer=answer,
            order=order
        )

        db.session.add(new_faq)
        db.session.commit()

        user = get_current_user()
        user_email = user.companyemail if user else 'unknown'
        log_with_route(logging.INFO, f"FAQ created by {user_email}: {question[:50]}...")

        flash('FAQ created successfully.', 'success')

    except Exception as e:
        db.session.rollback()
        log_with_route(logging.ERROR, f"Error creating FAQ: {str(e)}")
        flash('Error creating FAQ. Please try again.', 'error')

    return redirect(url_for('admin_bp.manage_faq'))


@admin_bp.route('/admin/faq/update/<int:faq_id>', methods=['POST'])
@admin_permission.require(http_exception=403)
def update_faq(faq_id):
    """Update an existing FAQ."""
    try:
        faq = FAQ.query.get_or_404(faq_id)

        question = request.form.get('question', '').strip()
        answer = request.form.get('answer', '').strip()
        order = request.form.get('order', type=int)

        if not question or not answer:
            flash('Question and answer are required.', 'error')
            return redirect(url_for('admin_bp.manage_faq'))

        # Update FAQ
        faq.question = question
        faq.answer = answer
        if order is not None:
            faq.order = order

        db.session.commit()

        user = get_current_user()
        user_email = user.companyemail if user else 'unknown'
        log_with_route(logging.INFO, f"FAQ updated by {user_email}: ID {faq_id}")

        flash('FAQ updated successfully.', 'success')

    except Exception as e:
        db.session.rollback()
        log_with_route(logging.ERROR, f"Error updating FAQ {faq_id}: {str(e)}")
        flash('Error updating FAQ. Please try again.', 'error')

    return redirect(url_for('admin_bp.manage_faq'))


@admin_bp.route('/admin/faq/delete/<int:faq_id>', methods=['POST'])
@admin_permission.require(http_exception=403)
def delete_faq(faq_id):
    """Delete an FAQ."""
    try:
        faq = FAQ.query.get_or_404(faq_id)
        question_preview = faq.question[:50] + "..." if len(faq.question) > 50 else faq.question

        db.session.delete(faq)
        db.session.commit()

        user = get_current_user()
        user_email = user.companyemail if user else 'unknown'
        log_with_route(logging.INFO, f"FAQ deleted by {user_email}: {question_preview}")

        flash('FAQ deleted successfully.', 'success')

    except Exception as e:
        db.session.rollback()
        log_with_route(logging.ERROR, f"Error deleting FAQ {faq_id}: {str(e)}")
        flash('Error deleting FAQ. Please try again.', 'error')

    return redirect(url_for('admin_bp.manage_faq'))


@admin_bp.route('/admin/faq/reorder', methods=['POST'])
@admin_permission.require(http_exception=403)
def reorder_faqs():
    """Reorder FAQs based on provided order."""
    try:
        faq_orders = request.json.get('orders', [])

        for item in faq_orders:
            faq_id = item.get('id')
            new_order = item.get('order')

            if faq_id and new_order is not None:
                faq = FAQ.query.get(faq_id)
                if faq:
                    faq.order = new_order

        db.session.commit()

        user = get_current_user()
        user_email = user.companyemail if user else 'unknown'
        log_with_route(logging.INFO, f"FAQs reordered by {user_email}")

        return jsonify({'success': True, 'message': 'FAQs reordered successfully'})

    except Exception as e:
        db.session.rollback()
        log_with_route(logging.ERROR, f"Error reordering FAQs: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500


# Tenant Backup and Deletion Functions
def ensure_tenant_backup_directory():
    """
    Ensure the tenant backup directory exists and is properly configured at /var/log/wegweiser/tenant_backups.
    Falls back to /tmp if there are permission issues.
    """
    backup_dir = '/var/log/wegweiser/tenant_backups'

    try:
        # First try the preferred location
        os.makedirs(backup_dir, mode=0o755, exist_ok=True)

        # Verify we can actually write to it
        test_file = os.path.join(backup_dir, '.write_test')
        try:
            with open(test_file, 'w') as f:
                f.write('test')
            os.remove(test_file)
            log_with_route(logging.INFO, f"Using tenant backup directory: {backup_dir}")
        except Exception as e:
            log_with_route(logging.WARNING, f"Cannot write to {backup_dir}: {str(e)}")
            raise

    except Exception as e:
        # Fall back to /tmp
        backup_dir = '/tmp/wegweiser_tenant_backups'
        os.makedirs(backup_dir, mode=0o755, exist_ok=True)
        log_with_route(logging.INFO, f"Using fallback tenant backup directory: {backup_dir}")

    return backup_dir


def backup_tenant_data(tenant_uuid):
    """
    Create a complete backup of all tenant-related data before deletion.
    Returns the path to the backup file.
    """
    tenant = Tenants.query.get(tenant_uuid)
    if not tenant:
        raise ValueError(f"Tenant {tenant_uuid} not found")

    # Initialize backup dictionary
    backup_data = {
        "tenant_info": {},
        "organisations": [],
        "groups": [],
        "devices": [],
        "related_data": {}
    }

    # Get tenant name for the filename
    tenant_name = tenant.tenantname or "unknown_tenant"

    # Backup main tenant info
    tenant_mapper = inspect(Tenants)
    for column in tenant_mapper.columns:
        value = getattr(tenant, column.key)
        if isinstance(value, UUID):
            value = str(value)
        backup_data["tenant_info"][column.key] = value

    # Backup all organisations under this tenant
    organisations = Organisations.query.filter_by(tenantuuid=tenant_uuid).all()
    for org in organisations:
        org_data = {}
        org_mapper = inspect(Organisations)
        for column in org_mapper.columns:
            value = getattr(org, column.key)
            if isinstance(value, UUID):
                value = str(value)
            org_data[column.key] = value
        backup_data["organisations"].append(org_data)

    # Backup all groups under this tenant
    groups = Groups.query.filter_by(tenantuuid=tenant_uuid).all()
    for group in groups:
        group_data = {}
        group_mapper = inspect(Groups)
        for column in group_mapper.columns:
            value = getattr(group, column.key)
            if isinstance(value, UUID):
                value = str(value)
            group_data[column.key] = value
        backup_data["groups"].append(group_data)

    # Backup all devices under this tenant
    devices = Devices.query.filter_by(tenantuuid=tenant_uuid).all()
    for device in devices:
        device_data = {}
        device_mapper = inspect(Devices)
        for column in device_mapper.columns:
            value = getattr(device, column.key)
            if isinstance(value, UUID):
                value = str(value)
            device_data[column.key] = value
        backup_data["devices"].append(device_data)

    # Define all related tables to backup
    related_tables = {
        "tenant_metadata": (TenantMetadata, "tenantuuid"),
        "organization_metadata": (OrganizationMetadata, "orguuid"),
        "group_metadata": (GroupMetadata, "groupuuid"),
        "ai_memories": (AIMemory, "tenantuuid"),
        "contexts": (Context, "tenant_uuid"),  # Note: uses tenant_uuid with underscore
        "conversations": (Conversations, "tenantuuid"),
        "wegcoin_transactions": (WegcoinTransaction, "tenantuuid"),
        "snippets": (Snippets, "tenantuuid"),
        "user_x_organisation": (UserXOrganisation, "orguuid"),
        "tags": (Tags, "tenantuuid"),
        "tags_x_tenants": (TagsXTenants, "tenantuuid"),
        "tags_x_orgs": (TagsXOrgs, "orguuid"),
        "tags_x_groups": (TagsXGroups, "groupuuid"),
        "tags_x_devices": (TagsXDevices, "deviceuuid"),
        "messages": (Messages, "entityuuid")
    }

    # Backup accounts for this tenant first
    accounts = Accounts.query.filter_by(tenantuuid=tenant_uuid).all()
    backup_data["accounts"] = []
    account_uuids = []
    for account in accounts:
        account_data = {}
        account_mapper = inspect(Accounts)
        for column in account_mapper.columns:
            value = getattr(account, column.key)
            if isinstance(value, UUID):
                value = str(value)
            account_data[column.key] = value
        backup_data["accounts"].append(account_data)
        account_uuids.append(account.useruuid)

    # Backup all account-related data for accounts in this tenant
    if account_uuids:
        # Email verifications
        backup_data["email_verifications"] = []
        email_verifications = EmailVerification.query.filter(
            EmailVerification.user_uuid.in_(account_uuids)
        ).all()
        for verification in email_verifications:
            verification_data = {}
            verification_mapper = inspect(EmailVerification)
            for column in verification_mapper.columns:
                value = getattr(verification, column.key)
                if isinstance(value, UUID):
                    value = str(value)
                verification_data[column.key] = value
            backup_data["email_verifications"].append(verification_data)

        # Two-factor authentication
        backup_data["user_two_factor"] = []
        two_factor_records = UserTwoFactor.query.filter(
            UserTwoFactor.user_uuid.in_(account_uuids)
        ).all()
        for record in two_factor_records:
            record_data = {}
            record_mapper = inspect(UserTwoFactor)
            for column in record_mapper.columns:
                value = getattr(record, column.key)
                if isinstance(value, UUID):
                    value = str(value)
                record_data[column.key] = value
            backup_data["user_two_factor"].append(record_data)

        # Profiles
        backup_data["profiles"] = []
        profiles = Profiles.query.filter(
            Profiles.account_id.in_(account_uuids)
        ).all()
        for profile in profiles:
            profile_data = {}
            profile_mapper = inspect(Profiles)
            for column in profile_mapper.columns:
                value = getattr(profile, column.key)
                if isinstance(value, UUID):
                    value = str(value)
                profile_data[column.key] = value
            backup_data["profiles"].append(profile_data)

        # MFA
        backup_data["mfa"] = []
        mfa_records = MFA.query.filter(
            MFA.useruuid.in_(account_uuids)
        ).all()
        for mfa in mfa_records:
            mfa_data = {}
            mfa_mapper = inspect(MFA)
            for column in mfa_mapper.columns:
                value = getattr(mfa, column.key)
                if isinstance(value, UUID):
                    value = str(value)
                mfa_data[column.key] = value
            backup_data["mfa"].append(mfa_data)

        # RSS Feeds
        backup_data["rss_feeds"] = []
        rss_feeds = RSSFeed.query.filter(
            RSSFeed.user_id.in_(account_uuids)
        ).all()
        for feed in rss_feeds:
            feed_data = {}
            feed_mapper = inspect(RSSFeed)
            for column in feed_mapper.columns:
                value = getattr(feed, column.key)
                if isinstance(value, UUID):
                    value = str(value)
                feed_data[column.key] = value
            backup_data["rss_feeds"].append(feed_data)

        # Tags X Accounts
        backup_data["tags_x_accounts"] = []
        tags_accounts = TagsXAccounts.query.filter(
            TagsXAccounts.accountuuid.in_(account_uuids)
        ).all()
        for tag_account in tags_accounts:
            tag_account_data = {}
            tag_account_mapper = inspect(TagsXAccounts)
            for column in tag_account_mapper.columns:
                value = getattr(tag_account, column.key)
                if isinstance(value, UUID):
                    value = str(value)
                tag_account_data[column.key] = value
            backup_data["tags_x_accounts"].append(tag_account_data)
    else:
        # Initialize empty arrays if no accounts
        backup_data["email_verifications"] = []
        backup_data["user_two_factor"] = []
        backup_data["profiles"] = []
        backup_data["mfa"] = []
        backup_data["rss_feeds"] = []
        backup_data["tags_x_accounts"] = []

    # Backup data from each related table
    for table_name, (model, filter_column) in related_tables.items():
        backup_data["related_data"][table_name] = []

        # Get all relevant UUIDs for filtering
        filter_values = []
        if filter_column == "tenantuuid":
            filter_values = [tenant_uuid]
        elif filter_column == "orguuid":
            filter_values = [org["orguuid"] for org in backup_data["organisations"]]
        elif filter_column == "groupuuid":
            filter_values = [group["groupuuid"] for group in backup_data["groups"]]
        elif filter_column == "deviceuuid":
            filter_values = [device["deviceuuid"] for device in backup_data["devices"]]
        elif filter_column == "entityuuid":
            # For messages, we need to check all entity types
            filter_values = ([tenant_uuid] +
                           [org["orguuid"] for org in backup_data["organisations"]] +
                           [group["groupuuid"] for group in backup_data["groups"]] +
                           [device["deviceuuid"] for device in backup_data["devices"]])

        if not filter_values:
            continue

        # Query the table with appropriate filters
        if filter_column == "entityuuid" and model == Messages:
            # Special handling for Messages table
            results = model.query.filter(
                model.entityuuid.in_(filter_values)
            ).all()
        else:
            # Standard filtering
            filter_attr = getattr(model, filter_column)
            results = model.query.filter(filter_attr.in_(filter_values)).all()

        for row in results:
            row_data = {}
            mapper = inspect(model)
            for column in mapper.columns:
                value = getattr(row, column.key)
                if isinstance(value, UUID):
                    value = str(value)
                elif isinstance(value, bytes):
                    value = value.decode('utf-8', errors='ignore')
                row_data[column.key] = value
            backup_data["related_data"][table_name].append(row_data)

    # Special handling for HealthScoreHistory (uses entity_uuid and entity_type)
    backup_data["related_data"]["health_score_history"] = []
    all_entity_uuids = ([str(tenant_uuid)] +
                       [org["orguuid"] for org in backup_data["organisations"]] +
                       [group["groupuuid"] for group in backup_data["groups"]] +
                       [device["deviceuuid"] for device in backup_data["devices"]])

    if all_entity_uuids:
        health_history_results = HealthScoreHistory.query.filter(
            HealthScoreHistory.entity_uuid.in_(all_entity_uuids)
        ).all()

        for row in health_history_results:
            row_data = {}
            mapper = inspect(HealthScoreHistory)
            for column in mapper.columns:
                value = getattr(row, column.key)
                if isinstance(value, UUID):
                    value = str(value)
                elif isinstance(value, bytes):
                    value = value.decode('utf-8', errors='ignore')
                row_data[column.key] = value
            backup_data["related_data"]["health_score_history"].append(row_data)

    # Special handling for SnippetsHistory (related through snippetuuid)
    backup_data["related_data"]["snippets_history"] = []
    snippet_uuids = [snippet["snippetuuid"] for snippet in backup_data["related_data"]["snippets"]]

    if snippet_uuids:
        snippets_history_results = SnippetsHistory.query.filter(
            SnippetsHistory.snippetuuid.in_(snippet_uuids)
        ).all()

        for row in snippets_history_results:
            row_data = {}
            mapper = inspect(SnippetsHistory)
            for column in mapper.columns:
                value = getattr(row, column.key)
                if isinstance(value, UUID):
                    value = str(value)
                elif isinstance(value, bytes):
                    value = value.decode('utf-8', errors='ignore')
                row_data[column.key] = value
            backup_data["related_data"]["snippets_history"].append(row_data)

    # Backup all device-related data for devices in this tenant
    device_uuids = [device["deviceuuid"] for device in backup_data["devices"]]
    if device_uuids:
        device_related_tables = {
            "device_metadata": DeviceMetadata,
            "device_battery": DeviceBattery,
            "device_drives": DeviceDrives,
            "device_memory": DeviceMemory,
            "device_networks": DeviceNetworks,
            "device_status": DeviceStatus,
            "device_users": DeviceUsers,
            "device_partitions": DevicePartitions,
            "device_cpu": DeviceCpu,
            "device_gpu": DeviceGpu,
            "device_bios": DeviceBios,
            "device_collector": DeviceCollector,
            "device_printers": DevicePrinters,
            "device_pci_devices": DevicePciDevices,
            "device_usb_devices": DeviceUsbDevices,
            "device_drivers": DeviceDrivers,
            "device_connectivity": DeviceConnectivity,
            "device_realtime_data": DeviceRealtimeData,
            "device_realtime_history": DeviceRealtimeHistory
        }

        for table_name, model in device_related_tables.items():
            backup_data["related_data"][table_name] = []
            results = model.query.filter(model.deviceuuid.in_(device_uuids)).all()

            for row in results:
                row_data = {}
                mapper = inspect(model)
                for column in mapper.columns:
                    value = getattr(row, column.key)
                    if isinstance(value, UUID):
                        value = str(value)
                    elif isinstance(value, bytes):
                        value = value.decode('utf-8', errors='ignore')
                    row_data[column.key] = value
                backup_data["related_data"][table_name].append(row_data)

    # Ensure backup directory exists
    backup_dir = ensure_tenant_backup_directory()

    # Create filename with timestamp
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    safe_tenant_name = "".join(x for x in tenant_name if x.isalnum() or x in ('-', '_'))
    filename = f"tenant_{safe_tenant_name}_{tenant_uuid}_{timestamp}.json"
    filepath = os.path.join(backup_dir, filename)

    # Write backup to file
    with open(filepath, 'w') as f:
        json.dump(backup_data, f, indent=2, default=str)

    log_with_route(logging.INFO, f"Created tenant backup at {filepath}")
    return filepath


def delete_tenant_cascade(tenant_uuid):
    """
    Delete a tenant and all its related data with proper error handling and logging.
    """
    try:
        tenant = Tenants.query.get(tenant_uuid)
        if not tenant:
            raise ValueError(f"Tenant {tenant_uuid} not found")

        tenant_name = tenant.tenantname  # Get name before deletion for the message

        # Get all devices under this tenant for device-specific cleanup
        devices = Devices.query.filter_by(tenantuuid=tenant_uuid).all()
        device_uuids = [device.deviceuuid for device in devices]

        # Delete device-related data first
        if device_uuids:
            device_related_deletions = [
                (DeviceMetadata, "device metadata"),
                (DeviceBattery, "device battery info"),
                (DeviceDrives, "device drive info"),
                (DeviceMemory, "device memory info"),
                (DeviceNetworks, "device network info"),
                (DeviceStatus, "device status info"),
                (DeviceUsers, "device user info"),
                (DevicePartitions, "device partition info"),
                (DeviceCpu, "device CPU info"),
                (DeviceGpu, "device GPU info"),
                (DeviceBios, "device BIOS info"),
                (DeviceCollector, "device collector info"),
                (DevicePrinters, "device printer info"),
                (DevicePciDevices, "device PCI device info"),
                (DeviceUsbDevices, "device USB device info"),
                (DeviceDrivers, "device driver info"),
                (DeviceRealtimeData, "device realtime data"),
                (DeviceRealtimeHistory, "device realtime history"),
                (DeviceConnectivity, "device connectivity info")
            ]

            for model, description in device_related_deletions:
                deleted = model.query.filter(model.deviceuuid.in_(device_uuids)).delete(synchronize_session=False)
                log_with_route(logging.DEBUG, f"Deleted {deleted} {description} records for tenant {tenant_uuid}")

        # Delete devices themselves
        deleted_devices = Devices.query.filter_by(tenantuuid=tenant_uuid).delete()
        log_with_route(logging.DEBUG, f"Deleted {deleted_devices} devices for tenant {tenant_uuid}")

        # Get organisation and group UUIDs for cleanup
        organisations = Organisations.query.filter_by(tenantuuid=tenant_uuid).all()
        org_uuids = [org.orguuid for org in organisations]

        groups = Groups.query.filter_by(tenantuuid=tenant_uuid).all()
        group_uuids = [group.groupuuid for group in groups]

        # Create list of all entity UUIDs for later use
        all_entity_uuids = [tenant_uuid] + org_uuids + group_uuids + device_uuids

        # Delete related data for organisations and groups
        if org_uuids:
            # Delete organization metadata
            deleted = OrganizationMetadata.query.filter(OrganizationMetadata.orguuid.in_(org_uuids)).delete(synchronize_session=False)
            log_with_route(logging.DEBUG, f"Deleted {deleted} organization metadata records for tenant {tenant_uuid}")

            # Delete user-organization associations
            deleted = UserXOrganisation.query.filter(UserXOrganisation.orguuid.in_(org_uuids)).delete(synchronize_session=False)
            log_with_route(logging.DEBUG, f"Deleted {deleted} user-organization associations for tenant {tenant_uuid}")

            # Delete organization tags
            deleted = TagsXOrgs.query.filter(TagsXOrgs.orguuid.in_(org_uuids)).delete(synchronize_session=False)
            log_with_route(logging.DEBUG, f"Deleted {deleted} organization tag associations for tenant {tenant_uuid}")

        if group_uuids:
            # Delete group metadata
            deleted = GroupMetadata.query.filter(GroupMetadata.groupuuid.in_(group_uuids)).delete(synchronize_session=False)
            log_with_route(logging.DEBUG, f"Deleted {deleted} group metadata records for tenant {tenant_uuid}")

            # Delete group tags
            deleted = TagsXGroups.query.filter(TagsXGroups.groupuuid.in_(group_uuids)).delete(synchronize_session=False)
            log_with_route(logging.DEBUG, f"Deleted {deleted} group tag associations for tenant {tenant_uuid}")

        if device_uuids:
            # Delete device tags
            deleted = TagsXDevices.query.filter(TagsXDevices.deviceuuid.in_(device_uuids)).delete(synchronize_session=False)
            log_with_route(logging.DEBUG, f"Deleted {deleted} device tag associations for tenant {tenant_uuid}")

        # Delete messages for all entities in this tenant FIRST (before conversations)
        deleted_messages = Messages.query.filter(Messages.entityuuid.in_(all_entity_uuids)).delete(synchronize_session=False)
        log_with_route(logging.DEBUG, f"Deleted {deleted_messages} messages for tenant {tenant_uuid}")

        # Delete tenant-level related data (conversations can now be deleted safely)
        tenant_related_deletions = [
            (TenantMetadata, "tenant metadata", "tenantuuid"),
            (AIMemory, "AI memories", "tenantuuid"),
            (Context, "contexts", "tenant_uuid"),  # Note: uses tenant_uuid with underscore
            (Conversations, "conversations", "tenantuuid"),
            (WegcoinTransaction, "wegcoin transactions", "tenantuuid"),
            (Snippets, "snippets", "tenantuuid"),
            (TagsXTenants, "tenant tag associations", "tenantuuid"),
            (Tags, "tags", "tenantuuid")  # Delete tags themselves last
        ]

        for model, description, field_name in tenant_related_deletions:
            if field_name == "tenant_uuid":
                deleted = model.query.filter_by(tenant_uuid=tenant_uuid).delete()
            else:
                deleted = model.query.filter_by(tenantuuid=tenant_uuid).delete()
            log_with_route(logging.DEBUG, f"Deleted {deleted} {description} records for tenant {tenant_uuid}")

        # Special handling for HealthScoreHistory (uses entity_uuid and entity_type)
        deleted_health_history = HealthScoreHistory.query.filter(
            HealthScoreHistory.entity_uuid.in_(all_entity_uuids)
        ).delete(synchronize_session=False)
        log_with_route(logging.DEBUG, f"Deleted {deleted_health_history} health score history records for tenant {tenant_uuid}")

        # Special handling for SnippetsHistory (related through snippetuuid)
        # First get all snippet UUIDs for this tenant
        snippet_uuids = [snippet.snippetuuid for snippet in Snippets.query.filter_by(tenantuuid=tenant_uuid).all()]
        if snippet_uuids:
            deleted_snippets_history = SnippetsHistory.query.filter(
                SnippetsHistory.snippetuuid.in_(snippet_uuids)
            ).delete(synchronize_session=False)
            log_with_route(logging.DEBUG, f"Deleted {deleted_snippets_history} snippets history records for tenant {tenant_uuid}")

        # Delete groups
        deleted_groups = Groups.query.filter_by(tenantuuid=tenant_uuid).delete()
        log_with_route(logging.DEBUG, f"Deleted {deleted_groups} groups for tenant {tenant_uuid}")

        # Delete organisations
        deleted_orgs = Organisations.query.filter_by(tenantuuid=tenant_uuid).delete()
        log_with_route(logging.DEBUG, f"Deleted {deleted_orgs} organisations for tenant {tenant_uuid}")

        # Delete all account-related data for accounts in this tenant first
        account_uuids = [account.useruuid for account in Accounts.query.filter_by(tenantuuid=tenant_uuid).all()]
        if account_uuids:
            # Delete tour progress records
            deleted_tour_progress = TourProgress.query.filter(
                TourProgress.user_id.in_(account_uuids)
            ).delete(synchronize_session=False)
            log_with_route(logging.DEBUG, f"Deleted {deleted_tour_progress} tour progress records for tenant {tenant_uuid}")

            # Delete email verifications
            deleted_email_verifications = EmailVerification.query.filter(
                EmailVerification.user_uuid.in_(account_uuids)
            ).delete(synchronize_session=False)
            log_with_route(logging.DEBUG, f"Deleted {deleted_email_verifications} email verifications for tenant {tenant_uuid}")

            # Delete two-factor authentication records
            deleted_two_factor = UserTwoFactor.query.filter(
                UserTwoFactor.user_uuid.in_(account_uuids)
            ).delete(synchronize_session=False)
            log_with_route(logging.DEBUG, f"Deleted {deleted_two_factor} two-factor records for tenant {tenant_uuid}")

            # Delete profiles
            deleted_profiles = Profiles.query.filter(
                Profiles.account_id.in_(account_uuids)
            ).delete(synchronize_session=False)
            log_with_route(logging.DEBUG, f"Deleted {deleted_profiles} profiles for tenant {tenant_uuid}")

            # Delete MFA records
            deleted_mfa = MFA.query.filter(
                MFA.useruuid.in_(account_uuids)
            ).delete(synchronize_session=False)
            log_with_route(logging.DEBUG, f"Deleted {deleted_mfa} MFA records for tenant {tenant_uuid}")

            # Delete RSS feeds
            deleted_rss_feeds = RSSFeed.query.filter(
                RSSFeed.user_id.in_(account_uuids)
            ).delete(synchronize_session=False)
            log_with_route(logging.DEBUG, f"Deleted {deleted_rss_feeds} RSS feeds for tenant {tenant_uuid}")

            # Delete tags x accounts associations
            deleted_tags_accounts = TagsXAccounts.query.filter(
                TagsXAccounts.accountuuid.in_(account_uuids)
            ).delete(synchronize_session=False)
            log_with_route(logging.DEBUG, f"Deleted {deleted_tags_accounts} account tag associations for tenant {tenant_uuid}")

        # Delete accounts associated with this tenant
        deleted_accounts = Accounts.query.filter_by(tenantuuid=tenant_uuid).delete()
        log_with_route(logging.DEBUG, f"Deleted {deleted_accounts} accounts for tenant {tenant_uuid}")

        # Delete the tenant itself
        db.session.delete(tenant)
        db.session.commit()

        log_with_route(logging.INFO, f"Successfully deleted tenant {tenant_name} ({tenant_uuid})")
        return True, tenant_name

    except Exception as e:
        db.session.rollback()
        log_with_route(logging.ERROR, f"Error in cascade delete for tenant {tenant_uuid}: {str(e)}")
        raise


@admin_bp.route('/admin/tenants/test', methods=['GET'])
@admin_permission.require(http_exception=403)
def test_tenant_route():
    """Test route to verify admin blueprint is working"""
    return jsonify({'status': 'success', 'message': 'Admin tenant routes are working'})


@admin_bp.route('/admin/tenants/delete', methods=['POST'])
@admin_permission.require(http_exception=403)
def delete_tenant():
    """
    Enhanced tenant deletion endpoint that creates a backup before deletion
    """
    try:
        log_with_route(logging.INFO, f"Tenant deletion request received from user {session.get('username', 'unknown')}")

        data = request.get_json()
        log_with_route(logging.DEBUG, f"Request data: {data}")

        if not data:
            log_with_route(logging.ERROR, "No JSON data received in request")
            return jsonify({'error': 'No JSON data provided'}), 400

        tenant_uuids = data.get('tenant_uuids')
        log_with_route(logging.DEBUG, f"Tenant UUIDs to delete: {tenant_uuids}")

        if not tenant_uuids:
            log_with_route(logging.ERROR, "No tenant UUIDs provided in request")
            return jsonify({'error': 'No tenant UUIDs provided'}), 400

        success_count = 0
        error_count = 0
        results = []
        for tenant_uuid in tenant_uuids:
            try:
                # Create backup first
                backup_path = backup_tenant_data(tenant_uuid)

                # Perform cascade deletion
                success, tenant_name = delete_tenant_cascade(tenant_uuid)

                if success:
                    success_count += 1
                    flash(f'Successfully deleted tenant {tenant_name}', 'success')
                    results.append({
                        'tenant_uuid': tenant_uuid,
                        'status': 'success',
                        'backup_path': backup_path,
                        'message': f'Tenant {tenant_name} deleted successfully'
                    })

            except Exception as e:
                error_count += 1
                error_msg = str(e)
                flash(f'Error deleting tenant: {error_msg}', 'error')
                results.append({
                    'tenant_uuid': tenant_uuid,
                    'status': 'error',
                    'error': error_msg
                })
                log_with_route(logging.ERROR, f"Error deleting tenant {tenant_uuid}: {error_msg}")

        summary_message = f"Deletion complete. {success_count} tenants deleted successfully"
        if error_count > 0:
            summary_message += f", {error_count} failed"
        flash(summary_message, 'info')

        return jsonify({
            'success': success_count > 0,
            'message': summary_message,
            'results': results,
            'success_count': success_count,
            'error_count': error_count
        })

    except Exception as e:
        log_with_route(logging.ERROR, f"Unexpected error in tenant deletion: {str(e)}")
        import traceback
        log_with_route(logging.ERROR, f"Traceback: {traceback.format_exc()}")
        return jsonify({'error': f'Unexpected error: {str(e)}'}), 500


# Tour Management Routes
@admin_bp.route('/admin/tours')
@admin_permission.require(http_exception=403)
def manage_tours():
    """Render the tour management page."""
    user = get_current_user()
    user_email = user.companyemail if user else 'unknown'
    log_with_route(logging.INFO, f"Tour management page accessed by {user_email}.")

    # Get all tours directly from database (bypass utility function for now)
    try:
        all_tours_db = GuidedTour.query.all()
        log_with_route(logging.INFO, f"Direct DB query found {len(all_tours_db)} tours")

        # Convert to dict format directly
        tours = [tour.to_dict() for tour in all_tours_db]
        log_with_route(logging.INFO, f"Converted to {len(tours)} tour dicts")

        # Get statistics
        total_users = db.session.query(Accounts).count()
        total_completions = db.session.query(TourProgress).filter_by(is_completed=True).count()

        return render_template('administration/admin_tours.html',
                             tours=tours,
                             total_users=total_users,
                             total_completions=total_completions)
    except Exception as e:
        log_with_route(logging.ERROR, f"Error in manage_tours: {str(e)}")
        return f"Error loading tours: {str(e)}", 500


@admin_bp.route('/admin/tours/create', methods=['POST'])
@admin_permission.require(http_exception=403)
def create_tour_route():
    """Create a new guided tour."""
    try:
        user = get_current_user()
        user_email = user.companyemail if user else 'unknown'
        user_id = user.useruuid if user else None

        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400

        # Extract tour data
        page_identifier = data.get('page_identifier')
        page_title = data.get('page_title')
        tour_name = data.get('tour_name')
        tour_description = data.get('tour_description')
        auto_start = data.get('auto_start', False)
        steps = data.get('steps', [])

        if not all([page_identifier, page_title, tour_name, steps]):
            return jsonify({'error': 'Missing required fields'}), 400

        # Create the tour
        tour = create_tour(
            page_identifier=page_identifier,
            page_title=page_title,
            tour_name=tour_name,
            steps=steps,
            tour_description=tour_description,
            auto_start=auto_start,
            created_by=user_id
        )

        if tour:
            log_with_route(logging.INFO, f"Tour created by {user_email}: {tour_name} for page {page_identifier}")
            return jsonify({'success': True, 'tour_id': str(tour.tour_id)})
        else:
            return jsonify({'error': 'Failed to create tour'}), 500

    except Exception as e:
        log_with_route(logging.ERROR, f"Error creating tour: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500


@admin_bp.route('/admin/tours/<tour_id>')
@admin_permission.require(http_exception=403)
def get_tour_route(tour_id):
    """Get tour details."""
    try:
        tour = GuidedTour.query.get(tour_id)
        if not tour:
            return jsonify({'error': 'Tour not found'}), 404

        return jsonify({'success': True, 'tour': tour.to_dict()})

    except Exception as e:
        log_with_route(logging.ERROR, f"Error getting tour {tour_id}: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500


@admin_bp.route('/admin/tours/<tour_id>/toggle', methods=['POST'])
@admin_permission.require(http_exception=403)
def toggle_tour_status_route(tour_id):
    """Toggle tour active status."""
    try:
        user = get_current_user()
        user_email = user.companyemail if user else 'unknown'

        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400

        is_active = data.get('is_active')
        if is_active is None:
            return jsonify({'error': 'Missing is_active field'}), 400

        tour = GuidedTour.query.get(tour_id)
        if not tour:
            return jsonify({'error': 'Tour not found'}), 404

        old_status = tour.is_active
        tour.is_active = is_active
        tour.updated_at = int(time.time())
        db.session.commit()

        status = 'activated' if is_active else 'deactivated'
        log_with_route(logging.INFO, f"Tour {status} by {user_email}: {tour.tour_name} (was {old_status}, now {is_active})")

        # Verify the change was saved
        updated_tour = GuidedTour.query.get(tour_id)
        log_with_route(logging.INFO, f"Verification: Tour {tour_id} is_active = {updated_tour.is_active if updated_tour else 'NOT FOUND'}")

        return jsonify({'success': True, 'is_active': is_active})

    except Exception as e:
        log_with_route(logging.ERROR, f"Error toggling tour status {tour_id}: {str(e)}")
        db.session.rollback()
        return jsonify({'error': 'Internal server error'}), 500


@admin_bp.route('/admin/tours/<tour_id>', methods=['DELETE'])
@admin_permission.require(http_exception=403)
def delete_tour_route(tour_id):
    """Delete a guided tour."""
    try:
        user = get_current_user()
        user_email = user.companyemail if user else 'unknown'

        tour = GuidedTour.query.get(tour_id)
        if not tour:
            return jsonify({'error': 'Tour not found'}), 404

        tour_name = tour.tour_name

        # Delete associated progress records
        TourProgress.query.filter_by(tour_id=tour_id).delete()

        # Delete the tour
        db.session.delete(tour)
        db.session.commit()

        log_with_route(logging.INFO, f"Tour deleted by {user_email}: {tour_name}")

        return jsonify({'success': True, 'message': 'Tour deleted successfully'})

    except Exception as e:
        log_with_route(logging.ERROR, f"Error deleting tour {tour_id}: {str(e)}")
        db.session.rollback()
        return jsonify({'error': 'Internal server error'}), 500


@admin_bp.route('/admin/tours/<tour_id>/update', methods=['POST'])
@admin_permission.require(http_exception=403)
def update_tour_route(tour_id):
    """Update an existing guided tour."""
    try:
        user = get_current_user()
        user_email = user.companyemail if user else 'unknown'

        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400

        tour = GuidedTour.query.get(tour_id)
        if not tour:
            return jsonify({'error': 'Tour not found'}), 404

        # Extract tour data
        page_title = data.get('page_title')
        tour_name = data.get('tour_name')
        tour_description = data.get('tour_description')
        auto_start = data.get('auto_start', False)
        is_active = data.get('is_active', False)
        steps = data.get('steps', [])

        if not all([page_title, tour_name, steps]):
            return jsonify({'error': 'Missing required fields'}), 400

        # Validate steps
        from app.utilities.guided_tour_manager import validate_tour_steps
        if not validate_tour_steps(steps):
            return jsonify({'error': 'Invalid tour steps'}), 400

        # Update the tour
        tour.page_title = page_title
        tour.tour_name = tour_name
        tour.tour_description = tour_description
        tour.auto_start = auto_start
        tour.is_active = is_active
        tour.steps = steps
        tour.updated_at = int(time.time())
        tour.version += 1

        db.session.commit()

        log_with_route(logging.INFO, f"Tour updated by {user_email}: {tour_name} (v{tour.version})")
        return jsonify({'success': True, 'tour_id': str(tour.tour_id), 'version': tour.version})

    except Exception as e:
        log_with_route(logging.ERROR, f"Error updating tour {tour_id}: {str(e)}")
        db.session.rollback()
        return jsonify({'error': 'Internal server error'}), 500
