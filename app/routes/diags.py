# Filepath: app/routes/diags.py
from flask import Blueprint, request, jsonify, current_app
import time
from random import randrange
import os
from app.models import db, ServerCore
import datetime
import zipfile
import base64
import json
import uuid
import asyncio
from sqlalchemy import update
from app.models import db, DeviceStatus, DeviceCollector, DeviceOSQuery
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_wtf.csrf import CSRFProtect
from app import csrf
from app.utilities.app_logging_helper import log_with_route
import logging

diags_bp = Blueprint('diags_bp', __name__)

# Initialize Flask-Limiter with default rate limits (e.g., 5 requests per minute per IP)
limiter = Limiter(
    get_remote_address,
    app=current_app,
    default_limits=["60 per minute"]
)

@diags_bp.route('/diags/ping', methods=['GET'])
def ping():
    log_with_route(logging.INFO, 'Received ping')
    timeStamp = int(time.time()) + randrange(10)
    log_with_route(logging.INFO, f'Sending pong: {timeStamp}')
    return jsonify({"status": "success", "data": f"pong", "timeStamp": timeStamp}), 200

@diags_bp.route('/diags/echo', methods=['POST'])
def echo():
    log_with_route(logging.INFO, 'Receiving echo')
    try:
        data = request.get_json()
        log_with_route(logging.INFO, f'Sent data: {data}')
    except Exception as e:
        log_with_route(logging.ERROR, f'Something went wrong. Reason: {e}')
    return jsonify({"status": "success", "echo": data}), 200

@diags_bp.route('/diags/collectorVersion', methods=['GET'])
@csrf.exempt
def returnCollectorVerion():
    log_with_route(logging.INFO, 'Receiving collectorVersion')
    try:
        serverCore = ServerCore.query.first()
    except Exception as e:
        log_with_route(logging.ERROR, f'Something went wrong. Reason: {e}')
    if serverCore:
        serverCollectorVersion = serverCore.collector_version
        serverHashPy = serverCore.collector_hash_py
        serverHashWin = serverCore.collector_hash_win
        log_with_route(logging.INFO, f'serverCollectorVersion: {serverCollectorVersion}')
        return jsonify({"status": "success",
                        "serverCollectorVersion": serverCollectorVersion,
                        "serverHashPy": serverHashPy,
                        "serverHashWin": serverHashWin}), 200
    else:
        log_with_route(logging.ERROR, f'Failed to get serverCollectorVersion')
        return jsonify({"status": "error", "serverCollectorVersion": '0'}), 400

@diags_bp.route('/diags/agentversion', methods=['GET'])
@csrf.exempt
def returnAgentVerion():
    log_with_route(logging.INFO, 'Receiving agentVersion')
    try:
        serverCore = ServerCore.query.first()
    except Exception as e:
        log_with_route(logging.ERROR, f'Something went wrong. Reason: {e}')
    if serverCore:
        serverAgentVersion = serverCore.agent_version
        serverAgentHashPy = serverCore.agent_hash_py
        serverAgentHashWin = serverCore.agent_hash_win
        log_with_route(logging.INFO, f'serverAgentVersion: {serverAgentVersion}')
        return jsonify({"status": "success",
                        "serverAgentVersion": serverAgentVersion,
                        "serverAgentHashPy": serverAgentHashPy,
                        "serverAgentHashWin": serverAgentHashWin}), 200
    else:
        log_with_route(logging.ERROR, f'Failed to get serverAgentVersion')
        return jsonify({"status": "error", "serverAgentVersion": '0'}), 400

@diags_bp.route('/diags/persistentagentversion', methods=['GET'])
@csrf.exempt
def returnPersistentAgentVersion():
    log_with_route(logging.INFO, 'Receiving persistentAgentVersion')
    try:
        serverCore = ServerCore.query.first()
    except Exception as e:
        log_with_route(logging.ERROR, f'Something went wrong. Reason: {e}')
    if serverCore:
        # Use dedicated persistent agent fields if available, fallback to agent fields
        serverPersistentAgentVersion = getattr(serverCore, 'persistent_agent_version', None) or serverCore.agent_version
        serverPersistentAgentHashPy = getattr(serverCore, 'persistent_agent_hash_py', None) or serverCore.agent_hash_py
        serverPersistentAgentHashLinux = getattr(serverCore, 'persistent_agent_hash_linux', None) or serverCore.agent_hash_py
        serverPersistentAgentHashMacos = getattr(serverCore, 'persistent_agent_hash_macos', None) or serverCore.agent_hash_py
        log_with_route(logging.INFO, f'serverPersistentAgentVersion: {serverPersistentAgentVersion}')
        return jsonify({"status": "success",
                        "persistent_agent_version": serverPersistentAgentVersion,
                        "persistent_agent_hash_py": serverPersistentAgentHashPy,
                        "persistent_agent_hash_linux": serverPersistentAgentHashLinux,
                        "persistent_agent_hash_macos": serverPersistentAgentHashMacos}), 200
    else:
        log_with_route(logging.ERROR, f'Failed to get serverPersistentAgentVersion')
        return jsonify({"status": "error", "persistent_agent_version": '0'}), 400

@diags_bp.route('/diags/serverpubkey', methods=['GET'])
@csrf.exempt
def returnServerPubKey():
    """Return server public key from file"""
    log_with_route(logging.INFO, 'Receiving serverpubkey')
    try:
        project_root = os.path.dirname(current_app.root_path)
        pubkey_file = os.path.join(project_root, 'includes', 'serverPubKey.pem')

        if not os.path.exists(pubkey_file):
            log_with_route(logging.ERROR, f'Public key file not found: {pubkey_file}')
            return jsonify({"status": "error", "message": "Public key not found"}), 404

        with open(pubkey_file, 'r') as f:
            pubkey_pem = f.read()

        log_with_route(logging.INFO, 'Successfully returned server public key')
        return jsonify({
            "status": "success",
            "serverpubpem": pubkey_pem
        }), 200
    except Exception as e:
        log_with_route(logging.ERROR, f'Failed to get server public key: {e}')
        return jsonify({"status": "error", "message": str(e)}), 500

@diags_bp.route('/diags/getserverpublickey', methods=['GET'])
@csrf.exempt  # Only use this if you intentionally want to bypass CSRF for this route
def returnServerPublicKey():
    log_with_route(logging.INFO, 'Receiving getserverpublickey')
    try:
        serverCore = ServerCore.query.first()
    except Exception as e:
        log_with_route(logging.ERROR, f'Something went wrong. Reason: {e}')
    if serverCore:
        log_with_route(logging.DEBUG, f'serverCore: {serverCore}')
        try:
            serverPubKeyPem = serverCore.server_public_key
            log_with_route(logging.INFO, f'serverPubKeyPem: {serverPubKeyPem}')
        except Exception as e:
            log_with_route(logging.ERROR, f'Failed to get value. Reason: {e}')
        try:
            serverPubKeyPemb64 = base64.b64encode(serverPubKeyPem.encode())
        except Exception as e:
            log_with_route(logging.ERROR, f'failed to b64. Reason: {e}')
        log_with_route(logging.DEBUG, f'serverpublickey (b64): {serverPubKeyPemb64}')
        return jsonify({"status": "success",
                        "serverpublickey": serverPubKeyPemb64.decode('utf-8')}), 200
    else:
        log_with_route(logging.ERROR, f'Failed to get serverPubKeyPem')
        return jsonify({"status": "error", "serverPubKeyPem": '0'}), 400

@diags_bp.route('/diags/keys/rotate', methods=['POST'])
@csrf.exempt
def rotate_server_keys():
    """Broadcast server public keys to all tenant agents via NATS for real-time key rotation"""
    log_with_route(logging.INFO, 'Receiving key rotation request')

    try:
        # Get current and old server public keys from files
        project_root = os.path.dirname(current_app.root_path)
        current_key_path = os.path.join(project_root, 'includes', 'serverPubKey.pem')
        old_key_path = os.path.join(project_root, 'includes', 'old', 'serverPubKey.pem')

        current_key_pem = None
        old_key_pem = None

        # Try to load current key
        if os.path.exists(current_key_path):
            with open(current_key_path, 'r') as f:
                current_key_pem = f.read()
            log_with_route(logging.INFO, f'Loaded current key from {current_key_path}')
        else:
            log_with_route(logging.WARNING, f'Current key not found at {current_key_path}')

        # Try to load old key for backward compatibility
        if os.path.exists(old_key_path):
            with open(old_key_path, 'r') as f:
                old_key_pem = f.read()
            log_with_route(logging.INFO, f'Loaded old key from {old_key_path}')
        else:
            log_with_route(logging.DEBUG, f'Old key not found at {old_key_path}')

        # At least current key must be available
        if not current_key_pem:
            log_with_route(logging.ERROR, 'Current server public key not available')
            return jsonify({"status": "error", "message": "Current server public key not available"}), 400

        # Trigger automatic snippet re-signing with new keys
        resigned_count = 0
        resign_failed_count = 0
        try:
            log_with_route(logging.INFO, 'Attempting to auto-resign all snippets with new keys...')

            # Get all snippet JSON files
            snippet_repo = os.path.join(project_root, 'snippets', '00000000-0000-0000-0000-000000000000')
            if os.path.exists(snippet_repo):
                snippet_files = [f for f in os.listdir(snippet_repo) if f.endswith('.json')]
                log_with_route(logging.INFO, f'Found {len(snippet_files)} snippets to re-sign')

                for snippet_file in snippet_files:
                    try:
                        snippet_path = os.path.join(snippet_repo, snippet_file)
                        snippet_uuid = os.path.splitext(snippet_file)[0]

                        # Load snippet JSON
                        with open(snippet_path, 'r') as f:
                            snippet_data = json.load(f)

                        # Extract payload to re-sign
                        if 'data' in snippet_data and 'payload' in snippet_data['data']:
                            payload_b64 = snippet_data['data']['payload']['payloadb64']
                        elif 'payload' in snippet_data:
                            payload_b64 = snippet_data['payload']['payloadb64']
                        else:
                            log_with_route(logging.WARNING, f'Skipping snippet {snippet_uuid}: invalid structure')
                            resign_failed_count += 1
                            continue

                        # Load private key and re-sign
                        from cryptography.hazmat.primitives.serialization import load_pem_private_key
                        from cryptography.hazmat.primitives import hashes
                        from cryptography.hazmat.primitives.asymmetric import padding
                        from cryptography.hazmat.backends import default_backend
                        import base64

                        private_key_path = os.path.join(project_root, 'includes', 'serverPrivKey.pem')
                        with open(private_key_path, 'rb') as f:
                            private_key = load_pem_private_key(
                                f.read(),
                                password=None,
                                backend=default_backend()
                            )

                        # Decode and sign the payload
                        payload = base64.b64decode(payload_b64)
                        signature = private_key.sign(
                            payload,
                            padding.PKCS1v15(),
                            hashes.SHA256()
                        )
                        encoded_signature = base64.b64encode(signature).decode()

                        # Update snippet with new signature
                        if 'data' in snippet_data and 'payload' in snippet_data['data']:
                            snippet_data['data']['payload']['payloadsig'] = encoded_signature
                        else:
                            snippet_data['payload']['payloadsig'] = encoded_signature

                        snippet_data['resigned_at'] = int(time.time())

                        # Save updated snippet
                        with open(snippet_path, 'w') as f:
                            json.dump(snippet_data, f)

                        resigned_count += 1
                        log_with_route(logging.DEBUG, f'Re-signed snippet: {snippet_uuid}')

                    except Exception as e:
                        log_with_route(logging.ERROR, f'Failed to re-sign snippet {snippet_uuid}: {e}')
                        resign_failed_count += 1

                log_with_route(logging.INFO, f'Snippet re-signing complete: {resigned_count} success, {resign_failed_count} failed')
            else:
                log_with_route(logging.WARNING, f'Snippet repository not found: {snippet_repo}')

        except Exception as e:
            log_with_route(logging.ERROR, f'Failed to auto-resign snippets: {e}')

        # Import NATS manager and get all tenants
        from app.utilities.nats_manager import nats_manager, NATSPublisher
        from app.models import Tenants, Devices

        # Get all tenants (they all should receive key rotations)
        try:
            all_tenants = db.session.query(Tenants).all()
            log_with_route(logging.INFO, f'Found {len(all_tenants)} tenants')

            nats_publisher = NATSPublisher(nats_manager)
            published_count = 0
            failed_count = 0

            for tenant in all_tenants:
                try:
                    # Get all devices for this tenant (for logging purposes)
                    devices = db.session.query(Devices).filter(Devices.tenantuuid == tenant.tenantuuid).all()

                    # Prepare key rotation payload
                    payload = {
                        "event": "KEY_ROTATION",
                        "keys": {
                            "current": current_key_pem
                        },
                        "timestamp": int(time.time()),
                        "rotation_id": str(uuid.uuid4())
                    }

                    # Include old key if available
                    if old_key_pem:
                        payload["keys"]["old"] = old_key_pem

                    # Publish to tenant-level broadcast subject
                    # This pattern allows all devices to subscribe to one subject
                    tenant_keys_subject = f"tenant.{tenant.tenantuuid}.keys.rotation"

                    # Use NATS directly for broadcast
                    import asyncio
                    async def publish_key_rotation():
                        nc = await nats_manager.get_connection(tenant.tenantuuid)
                        subject = f"tenant.{tenant.tenantuuid}.keys.rotation"
                        message_data = json.dumps(payload).encode()
                        await nc.publish(subject, message_data)
                        return True

                    # Try to publish asynchronously if event loop exists, otherwise skip NATS publish
                    # (this is acceptable for admin endpoint - fallback is API polling)
                    try:
                        loop = asyncio.get_event_loop()
                        if loop.is_running():
                            log_with_route(logging.INFO, f'Event loop running, scheduling NATS publish for tenant {tenant.tenantuuid}')
                            asyncio.ensure_future(publish_key_rotation())
                        else:
                            asyncio.run(publish_key_rotation())
                            published_count += 1
                    except RuntimeError:
                        # No event loop, use asyncio.run
                        try:
                            asyncio.run(publish_key_rotation())
                            published_count += 1
                        except Exception as e:
                            log_with_route(logging.WARNING, f'Failed to publish to NATS for tenant {tenant.tenantuuid}: {e}')
                            failed_count += 1

                    log_with_route(logging.INFO, f'Published key rotation for tenant {tenant.tenantuuid} ({len(devices)} devices)')

                except Exception as e:
                    log_with_route(logging.ERROR, f'Failed to publish for tenant {tenant.tenantuuid}: {e}')
                    failed_count += 1

            return jsonify({
                "status": "success",
                "message": f"Key rotation completed successfully",
                "tenants_targeted": len(all_tenants),
                "published": published_count,
                "failed": failed_count,
                "rotation_id": str(uuid.uuid4()),
                "snippets_resigned": resigned_count,
                "snippets_resign_failed": resign_failed_count,
                "notes": "Persistent agents will receive keys via NATS. Scheduled agents will refresh via API polling. All snippets have been automatically re-signed with new keys."
            }), 200

        except Exception as e:
            log_with_route(logging.ERROR, f'Failed to get tenants: {e}')
            return jsonify({"status": "error", "message": f"Failed to broadcast keys: {str(e)}"}), 500

    except Exception as e:
        log_with_route(logging.ERROR, f'Key rotation endpoint error: {e}')
        import traceback
        log_with_route(logging.ERROR, traceback.format_exc())
        return jsonify({"status": "error", "message": str(e)}), 500


@diags_bp.route('/diags/archivelogs', methods=['GET'])
@limiter.limit("10 per minute")  # Specific rate limit for this endpoint
def archiveLogs():
    # Restrict access to localhost (127.0.0.1)
    callingAddr = request.headers.getlist("X-Forwarded-For")[0]
    validAddresses = ['127.0.0.1', '81.150.150.132']
    if callingAddr not in validAddresses:
        log_with_route(logging.ERROR, f'Unauthorized access attempt to /diags/archivelogs/ from |{callingAddr}|.')
        return jsonify({"status": "error", f"called from disallowed address": '0'}), 403

    project_root = os.path.dirname(current_app.root_path)
    logsDir = os.path.join(project_root, 'logs')
    checkDir(logsDir)
    log_with_route(logging.INFO, 'Receiving archivelogs')

    archiveStatus = True
    now = datetime.datetime.now()
    prettyDate = now.strftime('%Y.%m.%d-%H:%M:%S')
    zipName = os.path.join(logsDir, prettyDate) + '.zip'
    with zipfile.ZipFile(zipName, 'w', compression=zipfile.ZIP_DEFLATED) as zipf:
        for logf in os.listdir(logsDir):
            if logf.endswith('.log'):
                log_with_route(logging.DEBUG, f'Found: {os.path.join(logsDir, logf)}')
                log_with_route(logging.INFO, f'Attempting to zip {os.path.join(logsDir, logf)} to {zipName}')
                try:
                    zipf.write(os.path.join(logsDir, logf), f'{prettyDate}_{logf}')
                except Exception as e:
                    log_with_route(logging.ERROR, f'Failed to zip {os.path.join(logsDir, logf)} to {zipName}. Reason: {e}')
                    archiveStatus = False
                log_with_route(logging.INFO, f'Attempting to remove {os.path.join(logsDir, logf)}')
                try:
                    os.remove(os.path.join(logsDir, logf))
                except Exception as e:
                    log_with_route(logging.ERROR, f'Failed to remove {os.path.join(logsDir, logf)}. Reason: {e}')
                    archiveStatus = False
    if archiveStatus == True:
        return jsonify({"status": "success", "data": 'Log archiving complete'}), 200
    else:
        return jsonify({"status": "error", "data": 'Failed to archive logs'}), 500

@diags_bp.route('/diags/testserversigning', methods=['GET'])
@csrf.exempt  # Only use this if you intentionally want to bypass CSRF for this route
def testServerSigning():
    log_with_route(logging.INFO, 'Receiving testserversigning')
    testSignFile = '/opt/wegweiser/includes/testSignFile.json'
    privateKeyFile = '/opt/wegweiser/includes/serverPrivKey.pem'
    from cryptography.hazmat.backends import default_backend
    from cryptography.hazmat.primitives.serialization import load_pem_private_key
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.asymmetric import padding
    import base64
    log_with_route(logging.DEBUG, f'Reading privateKeyFile: {privateKeyFile}')
    with open(privateKeyFile, 'rb') as keyFile:
        privateKey = load_pem_private_key(keyFile.read(), password=None, backend=default_backend())
    log_with_route(logging.DEBUG, f'Reading testSignFile: {testSignFile}')
    with open(testSignFile, 'rb') as f:
        testSignFileBytes = f.read()
    try:
        signature = privateKey.sign(
            testSignFileBytes,
            padding.PKCS1v15(),
            hashes.SHA256()
        )
    except Exception as e:
        log_with_route(logging.ERROR, f'Failed to sign. Reason: {e}')
    b64Sig = base64.b64encode(signature)
    log_with_route(logging.DEBUG, f'signature: {signature} | {type(signature)}')
    log_with_route(logging.DEBUG, f'b64Sig: {b64Sig} | {type(b64Sig)}')
    b64Payload = base64.b64encode(testSignFileBytes)
    log_with_route(logging.DEBUG, f'b64Payload: {b64Payload} | {type(b64Payload)}')

    snippetDict = {}
    snippetDict['payload'] = {}
    snippetDict['payload']['payloadsigb64'] = b64Sig.decode('utf-8')
    snippetDict['payload']['payloadb64'] = b64Payload.decode('utf-8')
    log_with_route(logging.DEBUG, f'snippetDict: {snippetDict}')
    return jsonify({"status": "success", "data": snippetDict}), 200

@diags_bp.route('/diags/checkin/<deviceuuid>', methods=['POST'])
@csrf.exempt
def doCheckin(deviceuuid):
    log_with_route(logging.INFO, f'Receiving checkin for {deviceuuid}')

    try:
        data = request.get_json()
        log_with_route(logging.INFO, f'Received checkin data: {data}')
    except Exception as e:
        log_with_route(logging.ERROR, f'Something went wrong. Reason: {e}')
        return jsonify({"status": "success", "Check in complete": data}), 200

    updateAgentDetailsSql = (
        update(DeviceCollector)
        .where(DeviceCollector.deviceuuid == deviceuuid)
        .values(
            last_update=int(time.time()),
            coll_version=data['agentVersion'],
            coll_install_dir=data['agentInstDir']
        )
    )

    updateLastUpdateSql = (
        update(DeviceStatus)
        .where(DeviceStatus.deviceuuid == deviceuuid)
        .values(
            last_update=int(time.time()),
        )
    )
    try:
        db.session.execute(updateLastUpdateSql)
        db.session.commit()
        log_with_route(logging.INFO, 'Updating DeviceStatus.last_update processed')
    except Exception as e:
        log_with_route(logging.ERROR, f'Error updating DeviceStatus.last_update: Reason: {e}')
        log_with_route(logging.ERROR, f'Rolling back transaction...')
        db.session.rollback()
        log_with_route(logging.ERROR, f'Transaction rolled back.')
        return jsonify({"status": "error", "data": 'Failed to check in(1)'}), 500

    try:
        db.session.execute(updateAgentDetailsSql)
        db.session.commit()
        log_with_route(logging.INFO, 'Updating DeviceCollector.details processed')
    except Exception as e:
        log_with_route(logging.ERROR, f'Error updating DeviceCollector.details: Reason: {e}')
        log_with_route(logging.ERROR, f'Rolling back transaction...')
        db.session.rollback()
        log_with_route(logging.ERROR, f'Transaction rolled back.')
        return jsonify({"status": "error", "data": 'Failed to check in (2)'}), 500
    return jsonify({"status": "success", "data": 'Check-in complete.'}), 200


@diags_bp.route('/diags/osquery/<deviceuuid>', methods=['POST'])
@csrf.exempt
def update_osquery_data(deviceuuid):
    log_with_route(logging.INFO, f'Receiving osquery data for {deviceuuid}')
    
    try:
        data = request.get_json()
        log_with_route(logging.INFO, f'Processing osquery data with sections: {", ".join(data.keys())}')
        
        for query_name, query_data in data.items():
            try:
                DeviceOSQuery.store_query_result(
                    deviceuuid=deviceuuid,
                    query_name=query_name,
                    data=query_data
                )
            except Exception as e:
                log_with_route(logging.ERROR, f'Error storing {query_name}: {str(e)}')
                db.session.rollback()
                continue
        
        return jsonify({"status": "success"}), 200
        
    except Exception as e:
        log_with_route(logging.ERROR, f'Failed to process osquery data: {str(e)}')
        return jsonify({"status": "error", "message": str(e)}), 500


####################### HELPER FUNCTIONS #######################

def checkDir(dirToCheck):
    if os.path.isdir(dirToCheck):
        log_with_route(logging.INFO, f'{dirToCheck} already exists.')
    else:
        log_with_route(logging.INFO, f'{dirToCheck} does not exist. Creating...')
        try:
            os.makedirs(dirToCheck)
            log_with_route(logging.INFO, f'{dirToCheck} created.')
        except Exception as e:
            log_with_route(logging.ERROR, f'Failed to create {dirToCheck}. Reason: {e}')