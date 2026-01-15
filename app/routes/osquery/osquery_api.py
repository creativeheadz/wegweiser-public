# Filepath: app/routes/osquery/osquery_api.py
"""
Osquery API Routes
Handles osquery-specific commands and queries via NATS
"""

from flask import jsonify, request, session
import logging
import re
import time

from app import csrf
from app.utilities.app_logging_helper import log_with_route
from app.utilities.app_get_current_user import get_current_user
from app.utilities.app_access_login_required import login_required
from app.models import Devices, Messages, Conversations, db
from . import osquery_bp
from .nats_utils import send_nats_command, execute_async_command
import json
from app.utilities.osquery_utils import OSQueryUtility

@osquery_bp.route('/api/device/<uuid:device_uuid>/osquery', methods=['POST'])
@csrf.exempt
@login_required
def execute_osquery(device_uuid):
    """Execute osquery command on device"""
    try:
        device_uuid_str = str(device_uuid)
        user = get_current_user()
        user_email = user.companyemail if user else 'unknown'

        log_with_route(logging.INFO, f"[OSQUERY] Request received for device: {device_uuid_str} from user: {user_email}")

        # Get device and its tenant UUID directly from database
        device = Devices.query.filter_by(deviceuuid=device_uuid_str).first()
        if not device:
            log_with_route(logging.ERROR, f"[OSQUERY] Device not found: {device_uuid_str}")
            return jsonify({'error': 'Device not found'}), 404

        # Use the device's actual tenant UUID (like the working admin dashboard)
        tenantuuid = str(device.tenantuuid)
        log_with_route(logging.INFO, f"[OSQUERY] Using tenant UUID: {tenantuuid} for device: {device_uuid_str}")
        log_with_route(logging.INFO, f"[OSQUERY] Device info - Name: {device.devicename}, Online: {device.is_online}, Last heartbeat: {device.last_heartbeat}")

        data = request.get_json()
        log_with_route(logging.INFO, f"[OSQUERY] Request body: {data}")

        # Support both new format (query) and admin dashboard format (action + args)
        if 'query' in data:
            # New terminal format
            query = data.get('query', '')
            action = 'osquery'
            args = {'query': query}
        else:
            # Admin dashboard format
            action = data.get('action', '')
            args = data.get('args', {})
            query = args.get('query', '') if isinstance(args, dict) else ''

        log_with_route(logging.INFO, f"[OSQUERY] Parsed - Query: {query}, Action: {action}, Args: {args}")

        if not query:
            return jsonify({'error': 'query is required'}), 400

        # Basic query validation
        query = query.strip()
        if not query:
            return jsonify({'error': 'Empty query'}), 400

        # Security check - only allow SELECT statements, CTEs and meta commands
        query_lower = query.lower().strip()
        if not (query_lower.startswith('select') or
                query_lower.startswith('with') or
                query_lower.startswith('.tables') or
                query_lower.startswith('.schema')):
            log_with_route(logging.WARNING, f"Rejected query: {query}")
            return jsonify({
                'error': 'Only SELECT statements, CTEs (WITH ...) and meta commands (.tables, .schema) are allowed'
            }), 400

        # Normalize whitespace to avoid agents collapsing newlines without spaces
        try:
            sanitized_query = re.sub(r"\s+", " ", query).strip()
            if action == 'osquery' and isinstance(args, dict):
                args['query'] = sanitized_query
        except Exception:
            # Best effort; if regex fails we proceed with original query
            pass

        log_with_route(logging.INFO, f"[OSQUERY] Sending NATS command to subject: tenant.{tenantuuid}.device.{device_uuid_str}.command")
        log_with_route(logging.INFO, f"[OSQUERY] Command payload - Action: {action}, Args: {args}")

        # Send osquery command via NATS (using exact same format as admin dashboard)
        command_coro = send_nats_command(
            tenantuuid=tenantuuid,
            device_uuid=device_uuid_str,
            action=action,
            args=args,
            user_email=user_email
        )

        log_with_route(logging.INFO, f"[OSQUERY] Executing async command...")
        result = execute_async_command(command_coro)

        log_with_route(logging.INFO, f"[OSQUERY] Result received: {result}")

        # Save terminal history to Messages table
        try:
            # Get or create conversation for this device
            conversation = Conversations.get_or_create_conversation(
                tenantuuid=device.tenantuuid,
                entityuuid=device.deviceuuid,
                entity_type='device'
            )

            # Save query message (user)
            query_msg = Messages(
                conversationuuid=conversation.conversationuuid,
                useruuid=user.useruuid if user else None,
                tenantuuid=device.tenantuuid,
                entityuuid=device.deviceuuid,
                entity_type='device',
                title='Terminal Query',
                content=query,
                message_type='terminal'
            )
            db.session.add(query_msg)

            # Save result message (system/AI)
            result_msg = Messages(
                conversationuuid=conversation.conversationuuid,
                useruuid=None,  # System message
                tenantuuid=device.tenantuuid,
                entityuuid=device.deviceuuid,
                entity_type='device',
                title='Terminal Result',
                content=json.dumps(result),
                message_type='terminal'
            )
            db.session.add(result_msg)
            db.session.commit()

            log_with_route(logging.INFO, f"[OSQUERY] Terminal history saved successfully")
        except Exception as e:
            log_with_route(logging.ERROR, f"[OSQUERY] Failed to save terminal history: {str(e)}")
            db.session.rollback()
            # Don't fail the request if history save fails

        return jsonify(result)

    except Exception as e:
        log_with_route(logging.ERROR, f"Osquery execution error: {str(e)}")
        return jsonify({'error': str(e)}), 500

@osquery_bp.route('/api/device/<uuid:device_uuid>/osquery/tables', methods=['GET'])
@login_required
def get_osquery_tables(device_uuid):
    """Get available osquery tables for device"""
    try:
        device_uuid_str = str(device_uuid)
        user = get_current_user()
        user_email = user.companyemail if user else 'unknown'

        # Get device and its tenant UUID directly from database
        device = Devices.query.filter_by(deviceuuid=device_uuid_str).first()
        if not device:
            return jsonify({'error': 'Device not found'}), 404

        # Use the device's actual tenant UUID
        tenantuuid = str(device.tenantuuid)

        # Send .tables command via NATS
        command_coro = send_nats_command(
            tenantuuid=tenantuuid,
            device_uuid=device_uuid_str,
            action='osquery',
            args={'query': '.tables'},
            user_email=user_email
        )

        result = execute_async_command(command_coro)
        return jsonify(result)

    except Exception as e:
        log_with_route(logging.ERROR, f"Error getting osquery tables: {str(e)}")
        return jsonify({'error': str(e)}), 500

@osquery_bp.route('/api/device/<uuid:device_uuid>/osquery/schema/<table_name>', methods=['GET'])
@login_required
def get_table_schema(device_uuid, table_name):
    """Get schema for specific osquery table"""
    try:
        device_uuid_str = str(device_uuid)
        user = get_current_user()
        user_email = user.companyemail if user else 'unknown'

        # Get device and its tenant UUID directly from database
        device = Devices.query.filter_by(deviceuuid=device_uuid_str).first()
        if not device:
            return jsonify({'error': 'Device not found'}), 404

        # Use the device's actual tenant UUID
        tenantuuid = str(device.tenantuuid)

        # Send .schema command via NATS
        command_coro = send_nats_command(
            tenantuuid=tenantuuid,
            device_uuid=device_uuid_str,
            action='osquery',
            args={'query': f'.schema {table_name}'},
            user_email=user_email
        )

        result = execute_async_command(command_coro)
        return jsonify(result)

    except Exception as e:
        log_with_route(logging.ERROR, f"Error getting table schema: {str(e)}")
        return jsonify({'error': str(e)}), 500

@osquery_bp.route('/api/device/<uuid:device_uuid>/osquery/schema/prefetch', methods=['POST'])
@login_required
def prefetch_osquery_schema(device_uuid):
    """Prefetch and cache full osquery schema for a device.

    - If a recent schema snapshot exists in DeviceOSQuery (query_name='schema'), return cached status
    - Otherwise: fetch .tables, then .schema <table> for each (capped), parse columns, and store
    """
    try:
        device_uuid_str = str(device_uuid)
        user = get_current_user()
        user_email = user.companyemail if user else 'unknown'

        # Validate device and get tenant
        device = Devices.query.filter_by(deviceuuid=device_uuid_str).first()
        if not device:
            return jsonify({'success': False, 'error': 'Device not found'}), 404
        tenantuuid = str(device.tenantuuid)

        # TTL and limits
        ttl_hours = request.args.get('ttl_hours', default=24, type=int) or 24
        max_tables = request.args.get('max_tables', default=150, type=int) or 150
        ttl_seconds = ttl_hours * 3600

        # Check cached schema
        from app.models import DeviceOSQuery  # local import to avoid circulars
        cached = DeviceOSQuery.query.filter_by(deviceuuid=device_uuid_str, query_name='schema').first()
        now_ts = int(time.time())
        if cached and (now_ts - int(cached.last_updated or 0) < ttl_seconds):
            return jsonify({
                'success': True,
                'status': 'cached',
                'table_count': len(cached.query_data or []),
                'last_updated': cached.last_updated,
                'ttl_hours': ttl_hours
            })

        # Helpers
        def _parse_tables_from_result(res_obj):
            try:
                # Common shapes: {result: {output: "..."}} OR {result: [...]}
                outer = res_obj or {}
                payload = outer.get('result') if isinstance(outer, dict) else outer
                payload = payload or outer
                # Text output
                if isinstance(payload, dict) and payload.get('output'):
                    lines = str(payload.get('output') or '').split('\n')
                    names = []
                    for ln in lines:
                        s = (ln or '').strip()
                        if not s:
                            continue
                        if s.startswith('=>'):
                            s = s[2:].strip()
                        if s:
                            names.append(s)
                    return names
                # Array rows
                if isinstance(payload, list):
                    names = []
                    for row in payload:
                        if isinstance(row, dict):
                            name = row.get('name') or row.get('table_name')
                            if name:
                                names.append(name)
                    return names
            except Exception:
                pass
            return []

        def _parse_schema_output(table_name: str, text: str):
            # Extract column list from ".schema <table>" output (CREATE TABLE ...)
            try:
                if not text:
                    return []
                # Normalize and strip markers
                t = text.replace('```sql', '').replace('```', '')
                lines = [ln.strip() for ln in t.split('\n') if ln.strip()]
                cleaned = []
                for ln in lines:
                    if ln.startswith('=>'):
                        ln = ln[2:].strip()
                    cleaned.append(ln)
                joined = ' '.join(cleaned)
                # Find content inside parentheses after CREATE TABLE
                m = re.search(r'CREATE\s+TABLE\s+[^\(]+\((.*)\)', joined, flags=re.IGNORECASE)
                if not m:
                    return []
                inner = m.group(1)
                # Split by commas but keep simple types with parens (e.g., VARCHAR(255))
                parts = [p.strip() for p in inner.split(',') if p.strip()]
                cols = []
                for p in parts:
                    # Remove constraints keywords
                    p2 = re.sub(r'\s+(PRIMARY\s+KEY|HIDDEN|REQUIRED|INDEXED).*$','', p, flags=re.IGNORECASE).strip()
                    m2 = re.match(r'([A-Za-z0-9_]+)\s+([A-Za-z0-9_\(\)]+)', p2)
                    if m2:
                        cols.append({'name': m2.group(1), 'type': m2.group(2)})
                return cols
            except Exception:
                return []

        # 1) Get table names
        tables_cmd = send_nats_command(
            tenantuuid=tenantuuid,
            device_uuid=device_uuid_str,
            action='osquery',
            args={'query': '.tables'},
            user_email=user_email
        )
        tables_result = execute_async_command(tables_cmd)
        table_names = _parse_tables_from_result(tables_result)
        if not table_names:
            return jsonify({'success': False, 'error': 'Failed to enumerate tables from device'}), 502

        # Cap number of tables to avoid long prefetch
        table_names = table_names[:max_tables]

        # 2) Fetch schema per table and build snapshot
        snapshot = []
        fetched = 0
        for name in table_names:
            try:
                schema_cmd = send_nats_command(
                    tenantuuid=tenantuuid,
                    device_uuid=device_uuid_str,
                    action='osquery',
                    args={'query': f'.schema {name}'},
                    user_email=user_email
                )
                schema_res = execute_async_command(schema_cmd)
                payload = schema_res.get('result') if isinstance(schema_res, dict) else schema_res
                text = None
                if isinstance(payload, dict) and payload.get('output'):
                    text = payload.get('output')
                elif isinstance(schema_res, dict) and schema_res.get('output'):
                    text = schema_res.get('output')
                else:
                    # Sometimes agents may return rows; skip if not text
                    text = ''
                cols = _parse_schema_output(name, text)
                if cols:
                    snapshot.append({'name': name, 'columns': cols})
                    fetched += 1
            except Exception:
                continue

        # 3) Store snapshot
        from app.models.device_osquery import DeviceOSQuery as DevOSQ
        DevOSQ.store_query_result(deviceuuid=device_uuid_str, query_name='schema', data=snapshot)

        return jsonify({
            'success': True,
            'status': 'prefetched',
            'table_count': len(snapshot),
            'fetched_tables': fetched,
            'requested_tables': len(table_names),
            'ttl_hours': ttl_hours
        })

    except Exception as e:
        log_with_route(logging.ERROR, f"Error prefetching osquery schema: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500


@osquery_bp.route('/api/device/<uuid:device_uuid>/osquery/nl2sql', methods=['POST'])
@csrf.exempt
@login_required
def translate_osquery_nl2sql(device_uuid):
    """Translate natural language to a safe osquery SQL statement.
    Returns JSON: { sql: "..." } or { error: "..." }
    """
    try:
        device_uuid_str = str(device_uuid)
        user = get_current_user()
        user_email = getattr(user, 'companyemail', 'unknown') if user else 'unknown'
        log_with_route(logging.INFO, f"[OSQUERY] NL2SQL request for device: {device_uuid_str} from user: {user_email}")

        # Validate device exists and belongs to tenant scope implicitly via auth
        device = Devices.query.filter_by(deviceuuid=device_uuid_str).first()
        if not device:
            return jsonify({'error': 'Device not found'}), 404

        data = request.get_json() or {}
        text = (data.get('text') or '').strip()
        if not text:
            return jsonify({'error': 'text is required'}), 400

        util = OSQueryUtility(device_uuid_str)
        raw_sql = (util.translate_to_sql(text) or '').strip()
        if not raw_sql:
            return jsonify({'error': 'Failed to translate query'}), 400

        # Sanitize and extract the first SQL statement from any LLM preamble/code fences
        s = raw_sql.replace('```sql', '').replace('```', '').strip()
        lower_all = s.lower()
        pos_select = lower_all.find('select')
        pos_with = lower_all.find('with')
        pos_candidates = [p for p in (pos_select, pos_with) if p != -1]
        if pos_candidates:
            start = min(pos_candidates)
            s = s[start:].strip()
        # Trim after code fence if any
        if '```' in s:
            s = s.split('```')[0].strip()
        # Keep only the first statement if multiple are present
        semi_idx = s.find(';')
        if semi_idx != -1:
            s = s[:semi_idx + 1].strip()

        # Normalize whitespace (convert newlines/tabs to single spaces)
        s = re.sub(r"\s+", " ", s).strip()

        sql = s

        lower = sql.strip().lower()
        # Allow SELECT, CTEs that start with WITH, and meta commands
        if not (lower.startswith('select') or lower.startswith('with') or lower.startswith('.tables') or lower.startswith('.schema')):
            log_with_route(logging.WARNING, f"[OSQUERY] Unsafe translation rejected: {sql}")
            return jsonify({'error': 'Only SELECT statements, CTEs (WITH ...) and meta commands (.tables/.schema) are allowed'}), 400

        return jsonify({'sql': sql})
    except Exception as e:
        log_with_route(logging.ERROR, f"[OSQUERY] NL2SQL error: {str(e)}")
        return jsonify({'error': str(e)}), 500


@osquery_bp.route('/api/device/<uuid:device_uuid>/terminal_history', methods=['GET'])
@login_required
def get_terminal_history(device_uuid):
    """Get terminal session history for device"""
    try:
        device_uuid_str = str(device_uuid)
        user = get_current_user()

        log_with_route(logging.INFO, f"[TERMINAL] Fetching terminal history for device: {device_uuid_str}")

        # Get device to ensure it exists and user has access
        device = Devices.query.filter_by(deviceuuid=device_uuid_str).first()
        if not device:
            return jsonify({'error': 'Device not found'}), 404

        # Get conversation for this device
        conversation = Conversations.query.filter_by(
            entityuuid=device_uuid,
            entity_type='device'
        ).first()

        if not conversation:
            log_with_route(logging.INFO, f"[TERMINAL] No conversation found for device {device_uuid_str}")
            return jsonify({"history": []})

        # Get terminal messages only (not chat messages)
        messages = Messages.query.filter_by(
            conversationuuid=conversation.conversationuuid,
            message_type='terminal'
        ).order_by(Messages.sequence_id.asc()).all()

        # Return last 100 terminal messages (50 query/result pairs)
        history = []
        for msg in messages[-100:]:
            history.append({
                "content": msg.content,
                "is_query": msg.useruuid is not None,
                "timestamp": msg.created_at,
                "message_uuid": str(msg.messageuuid)
            })

        log_with_route(logging.INFO, f"[TERMINAL] Retrieved {len(history)} terminal messages")
        return jsonify({"history": history})

    except Exception as e:
        log_with_route(logging.ERROR, f"Error getting terminal history: {str(e)}")
        return jsonify({'error': str(e)}), 500
