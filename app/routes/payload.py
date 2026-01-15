# Filepath: app/routes/payload.py
from flask import Blueprint, request, jsonify, current_app
from sqlalchemy.dialects.postgresql import insert
import json
import os
import time
import logging
from jsonschema import validate, ValidationError
from random import randrange
import shutil
import uuid
from app.models import db, Devices, Organisations, Groups, \
    DeviceStatus, DeviceBattery, DeviceMemory, \
    DeviceNetworks, DeviceDrives, DeviceUsers, DevicePartitions, \
    DeviceCpu, DeviceGpu, DeviceBios, DeviceCollector, Tags, \
	TagsXDevices, Tenants, DevicePrinters, DeviceDrivers, \
	Conversations, Messages
import requests
from app import csrf
from sqlalchemy.exc import IntegrityError
from app.utilities.app_logging_helper import log_with_route

# Import scheduleDefaultSnippets function
def scheduleDefaultSnippets(deviceUuid, hardwareinfo=None):
	"""Schedule default snippets for a device"""
	from app.routes.devices.devices import scheduleDefaultSnippets as schedule_func
	return schedule_func(deviceUuid, hardwareinfo)


payload_bp = Blueprint('payload_bp', __name__)
serverAddr = 'https://app.wegweiser.tech'

################## SENDAUDIT ##################

@payload_bp.route('/payload/sendaudit', methods=['POST'])
@csrf.exempt
def receive_audit():
	debugMode = False

	# Get the root directory of the Flask project
	project_root = os.path.dirname(current_app.root_path)
	logsDir = os.path.join(project_root, 'logs')
	queueDir = os.path.join(project_root, 'payloads', 'queue')
	invalidDir = os.path.join(project_root, 'payloads', 'invalid')
	payloadAuditSchemaFile = os.path.join(project_root, 'includes', 'payloadAuditSchema.json')

	checkDir(logsDir)
	checkDir(queueDir)
	checkDir(invalidDir)
	log_with_route(logging.INFO, '/payload/sendaudit begins...', '/payload/sendaudit')

	try:
		data = request.get_json()
		if debugMode:
			log_with_route(logging.DEBUG, f'Received data: {data}', '/payload/sendaudit')
	except Exception as e:
		log_with_route(logging.ERROR, f'Failed to receive JSON. Reason: {e}', '/payload/sendaudit')
		return jsonify({"status": "error", "data": str(e)}), 502

	payloadAuditSchema = readJsonSchema(payloadAuditSchemaFile)
	if not payloadAuditSchema:
		log_with_route(
			logging.ERROR,
			f'Cannot validate payload: schema not available at {payloadAuditSchemaFile}',
			'/payload/sendaudit'
		)
		return jsonify({"status": "error", "data": "server schema not available"}), 500

	status, deviceDataDict = validateData(data, payloadAuditSchema)
	if status:
		deviceUuid = deviceDataDict['data']['device']['deviceUuid']
		result = writeJsonFile(queueDir, deviceDataDict, deviceUuid, 'audit')
		if result:
			return jsonify({"status": "success", "data": 'ok'}), 200
		else:
			return jsonify({"status": "error", "data": 'failed'}), 200
	else:
		writeBadFile(invalidDir, data, 'audit')
		return jsonify({"status": "error", "data": 'invalid JSON data'}), 500

################## SENDEVENTLOG ##################

@payload_bp.route('/payload/sendeventlog', methods=['POST'])
@csrf.exempt
def receive_eventlog():
    from werkzeug.utils import secure_filename

    # Get the root directory of the Flask project
    project_root            = os.path.dirname(current_app.root_path)
    logsDir					= os.path.join(project_root, 'logs')
    queueDir                = os.path.join(project_root, 'payloads', 'queue')
    invalidDir              = os.path.join(project_root, 'payloads', 'invalid')

    checkDir(logsDir)
    checkDir(queueDir)
    checkDir(invalidDir)
    log_with_route(logging.INFO, '/payload/sendeventlog begins...', '/payload/sendeventlog')

    # Get client IP for logging
    client_ip = request.headers.get('X-Forwarded-For', request.remote_addr)
    log_with_route(logging.INFO, f'Event log upload request from IP: {client_ip}', '/payload/sendeventlog')

    if 'file' not in request.files:
        log_with_route(logging.ERROR, f'No File received from IP: {client_ip}', '/payload/sendeventlog')
        return jsonify({"status": "error", "data": 'No File received'}), 400

    file = request.files['file']
    log_with_route(logging.DEBUG, f'filename: {file.filename} from IP: {client_ip}', '/payload/sendeventlog')

    if not file or file.filename == '':
        # Generate a unique filename for empty/invalid files
        invalid_filename = f"invalid_eventlog_{int(time.time())}.unknown"
        file_path = os.path.join(invalidDir, invalid_filename)
        if file:
            file.save(file_path)
        log_with_route(logging.ERROR, f'Invalid or empty eventlog file from IP: {client_ip}', '/payload/sendeventlog')
        return jsonify({"status": "error", "data": 'Invalid file type'}), 400

    # Validate file extension
    if not file.filename.endswith('.zip'):
        log_with_route(logging.ERROR, f'Invalid file extension for eventlog: {file.filename} from IP: {client_ip}', '/payload/sendeventlog')
        return jsonify({"status": "error", "data": 'Only .zip files allowed for eventlogs'}), 400

    # Secure the filename
    original_filename = secure_filename(file.filename)
    if not original_filename:
        original_filename = "eventlog.zip"

    # Create secure filename with timestamp
    base_name = original_filename.replace('.zip', '')
    filename = f"{base_name}.{int(time.time())}.eventlog.zip"
    file_path = os.path.join(queueDir, filename)

    # Ensure the file path is within the queue directory
    if not os.path.abspath(file_path).startswith(os.path.abspath(queueDir)):
        log_with_route(logging.ERROR, f'Path traversal attempt detected for eventlog from IP: {client_ip}')
        return jsonify({"status": "error", "data": 'Invalid file path'}), 400

    try:
        log_with_route(logging.INFO, f'Saving eventlog: {file_path} from IP: {client_ip}')
        file.save(file_path)
        log_with_route(logging.INFO, f'Successfully saved eventlog from IP: {client_ip}')
        return jsonify({"status": "success", "data": 'ok'}), 200
    except Exception as e:
        log_with_route(logging.ERROR, f'Error saving eventlog from IP: {client_ip}: {str(e)}')
        return jsonify({"status": "error", "data": 'Failed to save file'}), 500

################## SENDMSINFO ##################

@payload_bp.route('/payload/sendmsinfo', methods=['POST'])
@csrf.exempt
def receive_msinfo():
    # Get the root directory of the Flask project
    project_root            = os.path.dirname(current_app.root_path)
    logsDir					= os.path.join(project_root, 'logs')
    queueDir                = os.path.join(project_root, 'payloads', 'queue')
    invalidDir              = os.path.join(project_root, 'payloads', 'invalid')

    checkDir(logsDir)
    checkDir(queueDir)
    checkDir(invalidDir)
    log_with_route(logging.INFO, '/payload/sendmsinfo begins...')

    if 'file' not in request.files:
        log_with_route(logging.INFO, f'No File received')
        return jsonify({"status": "error", "data": 'No File received'}), 502
    file = request.files['file']
    log_with_route(logging.DEBUG, f'filename: {file.filename}')
    if file.filename == '':
        file_path = os.path.join(invalidDir, filename)
        file.save(file_path)
        log_with_route(logging.ERROR, 'Invalid file type.')
        return jsonify({"status": "error", "data": 'Invalid file type'}), 502
    if file and (file.filename).endswith('.nfo.zip'):
        filename    = f"{file.filename.split('.nfo.zip')[0]}.{str(time.time())}.msinfo.nfo.zip"
        file_path   = os.path.join(queueDir, filename)
        log_with_route(logging.INFO, f'Saving {file_path}')
        file.save(file_path)
        return jsonify({"status": "success", "data": 'ok'}), 200

################## SENDFILE ##################

@payload_bp.route('/payload/sendfile', methods=['POST'])
@csrf.exempt  # Required for distributed agent communication
def receive_file():
    from werkzeug.utils import secure_filename
    import uuid

    # Get the root directory of the Flask project
    project_root            = os.path.dirname(current_app.root_path)
    logsDir					= os.path.join(project_root, 'logs')
    queueDir                = os.path.join(project_root, 'payloads', 'queue')
    invalidDir              = os.path.join(project_root, 'payloads', 'invalid')

    checkDir(logsDir)
    checkDir(queueDir)
    checkDir(invalidDir)
    log_with_route(logging.INFO, '/payload/sendfile begins...')

    # Get client IP for logging
    client_ip = request.headers.get('X-Forwarded-For', request.remote_addr)
    log_with_route(logging.INFO, f'File upload request from IP: {client_ip}')

    log_with_route(logging.DEBUG, f'request.headers(): {request.headers}')

    # Validate deviceUuid header (agent sends as 'deviceuuid' lowercase)
    deviceUuid = request.headers.get('deviceuuid') or request.headers.get('deviceUuid')
    if not deviceUuid:
        log_with_route(logging.ERROR, f'No deviceUuid in headers from IP: {client_ip}')
        return jsonify({"status": "error", "data": 'No deviceuuid specified'}), 400

    # Validate deviceUuid format (should be a valid UUID)
    try:
        uuid.UUID(deviceUuid)
    except ValueError:
        log_with_route(logging.ERROR, f'Invalid deviceUuid format: {deviceUuid} from IP: {client_ip}')
        return jsonify({"status": "error", "data": 'Invalid deviceuuid format'}), 400

    log_with_route(logging.INFO, f'deviceUuid: {deviceUuid} from IP: {client_ip}')

    # Check for file in request
    if 'file' not in request.files:
        log_with_route(logging.ERROR, f'No File received from device: {deviceUuid}, IP: {client_ip}')
        return jsonify({"status": "error", "data": 'No File received'}), 400

    file = request.files['file']
    log_with_route(logging.DEBUG, f'filename: {file.filename} from device: {deviceUuid}')

    # Validate file exists and has content
    if not file or file.filename == '':
        # Generate a unique filename for empty/invalid files
        invalid_filename = f"invalid_{deviceUuid}_{int(time.time())}.unknown"
        file_path = os.path.join(invalidDir, invalid_filename)
        if file:
            file.save(file_path)
        log_with_route(logging.ERROR, f'Invalid or empty file from device: {deviceUuid}, IP: {client_ip}')
        return jsonify({"status": "error", "data": 'Invalid file type'}), 400

    # Secure the original filename to prevent path traversal
    original_filename = secure_filename(file.filename)
    if not original_filename:
        original_filename = "unknown_file"

    # Basic file size validation (reasonable limit for agent payloads)
    MAX_SIZE = 50 * 1024 * 1024  # 50MB limit - adjust based on your typical payload sizes
    file.seek(0, 2)  # Seek to end
    file_size = file.tell()
    file.seek(0)  # Reset to beginning

    if file_size > MAX_SIZE:
        log_with_route(logging.ERROR, f'File too large: {file_size} bytes from device: {deviceUuid}, IP: {client_ip}')
        return jsonify({"status": "error", "data": 'File too large'}), 413

    if file_size == 0:
        log_with_route(logging.ERROR, f'Empty file from device: {deviceUuid}, IP: {client_ip}')
        return jsonify({"status": "error", "data": 'Empty file'}), 400

    # Create secure filename with timestamp
    timestamp = int(time.time())
    secure_filename_part = f"{deviceUuid}.{timestamp}.{original_filename}"
    file_path = os.path.join(queueDir, f'{secure_filename_part}|{original_filename}')

    # Ensure the file path is within the queue directory (additional safety)
    if not os.path.abspath(file_path).startswith(os.path.abspath(queueDir)):
        log_with_route(logging.ERROR, f'Path traversal attempt detected from device: {deviceUuid}, IP: {client_ip}')
        return jsonify({"status": "error", "data": 'Invalid file path'}), 400

    try:
        log_with_route(logging.INFO, f'Saving file: {file_path} (size: {file_size} bytes) from device: {deviceUuid}')
        file.save(file_path)
        log_with_route(logging.INFO, f'Successfully saved file from device: {deviceUuid}, IP: {client_ip}')
        return jsonify({"status": "success", "data": 'ok'}), 200
    except Exception as e:
        log_with_route(logging.ERROR, f'Error saving file from device: {deviceUuid}, IP: {client_ip}: {str(e)}')
        return jsonify({"status": "error", "data": 'Failed to save file'}), 500

################## SENDAGENTSTATUS ##################

@payload_bp.route('/payload/sendagentstatus', methods=['POST'])
@csrf.exempt
def receive_status():
	pass




################## SEND WEGLOG ##################

@payload_bp.route('/payload/sendweglog', methods=['POST'])
def receive_weglog():
    pass

################## PROCESSPAYLOADS ##################

@payload_bp.route('/payload/processpayloads', methods=['GET'])
@csrf.exempt
def processpayloads():
    # Log the processing request for security monitoring
    client_ip = request.headers.get('X-Forwarded-For', request.remote_addr)
    log_with_route(logging.INFO, f'Payload processing request from IP: {client_ip}')
    startTime = time.time()

    # Get the root directory of the Flask project
    project_root            = os.path.dirname(current_app.root_path)
    logsDir                 = os.path.join(project_root, 'logs')
    queueDir                = os.path.join(project_root, 'payloads', 'queue')
    invalidDir              = os.path.join(project_root, 'payloads', 'invalid')
    noDeviceUuidDir         = os.path.join(project_root, 'payloads', 'noDeviceUuid')
    ophanedCollectorsDir    = os.path.join(project_root, 'payloads', 'ophanedCollectors')
    successfulImportDir     = os.path.join(project_root, 'payloads', 'sucessfulImport')
    deviceFilesDir          = os.path.join(project_root, 'deviceFiles')

    checkDir(logsDir)
    checkDir(queueDir)
    checkDir(invalidDir)
    checkDir(successfulImportDir)
    checkDir(noDeviceUuidDir)
    checkDir(ophanedCollectorsDir)
    checkDir(deviceFilesDir)

    log_with_route(logging.INFO, '/payload/processpayloads begins...')

    log_with_route(logging.INFO, 'processing payloads...')
    payloadstoProcessList   = getPayloadQueue(queueDir)
    itemsToProcess = len(payloadstoProcessList)
    for filename in payloadstoProcessList:
        full_path = os.path.join(queueDir, filename)
        log_with_route(logging.DEBUG, f'Processing file: {filename}')

        # CRITICAL: Initialize auditDict for EACH file to prevent data leakage between files
        auditDict = None

        # Check if file still exists (race condition protection)
        if not os.path.exists(full_path):
            log_with_route(logging.DEBUG, f'File {full_path} no longer exists, likely processed by another worker. Skipping.')
            continue

        try:
            if filename.endswith('.audit.json'):           ## PROCESS AUDIT DATA
                log_with_route(logging.DEBUG, f'Processing: {full_path}')
                deviceUuid, \
                    groupUuid  = validatePayloadJson(full_path)
                if deviceUuid:
                    isValidDevice = getDeviceValidity(deviceUuid)
                else:
                    log_with_route(logging.DEBUG, f'Renaming {full_path} to {os.path.join(noDeviceUuidDir, os.path.basename(full_path))}')
                    os.rename(full_path, os.path.join(noDeviceUuidDir, os.path.basename(full_path)))
                    continue

                if not isValidDevice:
                    log_with_route(logging.WARNING, f'{deviceUuid} does not exist in database. Attempting to re-register it.')
                    auditDict = getAuditDict(full_path)
                    registration_success = reregisterOrphanedDevice(deviceUuid, auditDict)

                    if registration_success:
                        log_with_route(logging.INFO, f"Successfully re-registered device {deviceUuid}, continuing with metadata processing")
                        isValidDevice = True
                    else:
                        log_with_route(logging.ERROR, f"Failed to re-register device {deviceUuid} - original group not found or other error occurred")
                        log_with_route(logging.DEBUG, f'Moving {full_path} to {os.path.join(ophanedCollectorsDir, os.path.basename(full_path))}')
                        os.rename(full_path, os.path.join(ophanedCollectorsDir, os.path.basename(full_path)))
                        continue

                # Now that the device is validated or re-registered, continue with processing
                if not auditDict:  # If we haven't loaded it yet during re-registration
                    auditDict = getAuditDict(full_path)
                log_with_route(logging.DEBUG, f'######### AUDITDICT #########')
                log_with_route(logging.DEBUG, f'{json.dumps(auditDict, indent=4)}')
                upsertDeviceStatus(deviceUuid, auditDict)
                log_with_route(logging.INFO, 'upsertDeviceStatus completed')
                upsertDeviceBattery(deviceUuid, auditDict)
                log_with_route(logging.INFO, 'upsertDeviceBattery completed')
                upsertDeviceMemory(deviceUuid, auditDict)
                log_with_route(logging.INFO, 'upsertDeviceMemory completed')
                upsertDeviceNetworks(deviceUuid, auditDict)
                log_with_route(logging.INFO, 'upsertDeviceNetworks completed')
                upsertDeviceUsers(deviceUuid, auditDict)
                log_with_route(logging.INFO, 'upsertDeviceUsers completed')
                upsertDevicePartitions(deviceUuid, auditDict)
                log_with_route(logging.INFO, 'upsertDevicePartitions completed')
                upsertDeviceDrives(deviceUuid, auditDict)
                log_with_route(logging.INFO, 'upsertDeviceDrives completed')
                upsertDeviceCpu(deviceUuid, auditDict)
                log_with_route(logging.INFO, 'upsertDeviceCpu completed')
                upsertDeviceGpu(deviceUuid, auditDict)
                log_with_route(logging.INFO, 'upsertDeviceGpu completed')
                upsertDeviceBios(deviceUuid, auditDict)
                log_with_route(logging.INFO, 'upsertDeviceBios completed')
                upsertDeviceColl(deviceUuid, auditDict)
                log_with_route(logging.INFO, 'upsertDeviceColl completed')
                upsertDevicePrinters(deviceUuid, auditDict)
                log_with_route(logging.INFO, 'upsertDevicePrinters completed')
                upsertDeviceDrivers(deviceUuid, auditDict)
                log_with_route(logging.INFO, 'upsertDeviceDrivers completed')
                log_with_route(logging.DEBUG, f'Renaming {full_path} to {os.path.join(successfulImportDir, os.path.basename(full_path))}')
                if os.path.exists(full_path):
                    os.renames(full_path, os.path.join(successfulImportDir, os.path.basename(full_path)))
                else:
                    log_with_route(logging.ERROR, f'File {full_path} does not exist, unable to move.')

                autoAssignTags(auditDict, deviceUuid)

            elif filename.endswith('.zip'):        ## PROCESS ZIPS
                log_with_route(logging.DEBUG, f'Processing zip file: {full_path}')
                deviceUuid = os.path.basename(full_path).split('.')[0]
                log_with_route(logging.INFO, f'deviceUuid: {deviceUuid}')
                unzipResult = unzipPayload(deviceFilesDir, full_path, deviceUuid)
                if unzipResult == False:
                    log_with_route(logging.DEBUG, f'Renaming {full_path} to {os.path.join(invalidDir, os.path.basename(full_path))}')
                    if not os.path.exists(invalidDir):
                        os.makedirs(invalidDir)
                    if os.path.exists(full_path):
                        os.renames(full_path, os.path.join(invalidDir, os.path.basename(full_path)))
                    else:
                        log_with_route(logging.ERROR, f'File {full_path} does not exist, unable to move to invalid directory.')
                else:
                    log_with_route(logging.DEBUG, f'Renaming {full_path} to {os.path.join(successfulImportDir, os.path.basename(full_path))}')
                    if not os.path.exists(successfulImportDir):
                        os.makedirs(successfulImportDir)
                    if os.path.exists(full_path):
                        os.renames(full_path, os.path.join(successfulImportDir, os.path.basename(full_path)))
                    else:
                        log_with_route(logging.ERROR, f'File {full_path} does not exist, unable to move to successful directory.')

            else:         ## PROCESS OTHER FILES
                log_with_route(logging.DEBUG, f'Processing other file: {filename}')
                try:
                    # Split only the filename part
                    file_parts = filename.split('|')
                    if len(file_parts) == 2:
                        original_name = file_parts[1]
                        device_uuid = file_parts[0].split('.')[0]
                    else:
                        original_name = filename
                        device_uuid = filename.split('.')[0]

                    log_with_route(logging.INFO, f'deviceUuid: {device_uuid}')

                    # Create target directory
                    target_dir = os.path.join(deviceFilesDir, device_uuid)
                    os.makedirs(target_dir, exist_ok=True)

                    target_path = os.path.join(target_dir, original_name)
                    source_path = os.path.join(queueDir, filename)

                    log_with_route(logging.DEBUG, f'Moving {source_path} to {target_path}')

                    if os.path.exists(source_path):
                        shutil.move(source_path, target_path)
                        log_with_route(logging.INFO, f'Successfully moved file to {target_path}')
                    else:
                        log_with_route(logging.ERROR, f'Source file not found: {source_path}')

                except Exception as e:
                    log_with_route(logging.ERROR, f'Error processing file {filename}: {str(e)}', exc_info=True)
                    continue

        except Exception as e:
            log_with_route(logging.ERROR, f'Error processing file {filename}: {str(e)}', exc_info=True)
            continue

    execTime = time.time() - startTime
    log_with_route(logging.INFO, f'Processed {itemsToProcess} payload(s) in {execTime} seconds.' )
    return jsonify({'success': f'Processed {itemsToProcess} payload(s) in {execTime} seconds.'}), 200


################## ADDITIONAL FUNCTIONS ##################

def unzipPayload(deviceFilesDir, payload, deviceUuid):
	import zipfile
	deviceFolder = f'{deviceFilesDir}/{deviceUuid}'
	log_with_route(logging.DEBUG, f'deviceFolder: {deviceFolder}')
	checkDir(deviceFolder)
	log_with_route(logging.INFO, f'Attempting to unzip {payload} to {deviceFolder}')
	try:
		with zipfile.ZipFile(payload, 'r') as zipf:
			zipf.extractall(deviceFolder)
		return(True)
	except Exception as e:
		log_with_route(logging.ERROR, f'Failed to unzip {payload} to {deviceFolder}. Reason: {e}')
		return(False)

def upsertDeviceStatus(deviceUuid, auditDict):
	log_with_route(logging.INFO, f'Attempting to upsert Device Status for {deviceUuid}')
	if 'systemmodel' not in auditDict['data']['system']:
		auditDict['data']['system']['systemmodel'] = 'n/a'
	if 'systemlocale' not in auditDict['data']['system']:
		auditDict['data']['system']['systemlocale'] = 'n/a'
	if 'systemmanufacturer' not in auditDict['data']['system']:
		auditDict['data']['system']['systemmanufacturer'] = 'n/a'
	upsertDeviceStatusSql = insert(DeviceStatus).values(
		deviceuuid     		= deviceUuid,
		last_update     	= int(time.time()),
		last_json     		= auditDict['data']['device']['systemtime'],
		agent_platform  	= auditDict['data']['system']['devicePlatform'],
		system_name      	= auditDict['data']['system']['systemName'],
		logged_on_user    	= auditDict['data']['system']['currentUser'],
		cpu_usage        	= auditDict['data']['system']['cpuUsage'],
		cpu_count        	= auditDict['data']['system']['cpuCount'],
		boot_time        	= auditDict['data']['system']['bootTime'],
        publicIp			= auditDict['data']['system']['publicIp'],
        system_model		= auditDict['data']['system']['systemmodel'],
		system_locale		= auditDict['data']['system']['systemlocale'],
		system_manufacturer = auditDict['data']['system']['systemmanufacturer']

	).on_conflict_do_update (
		index_elements=['deviceuuid'],
		set_= dict(
			last_update     	= int(time.time()),
			last_json     		= auditDict['data']['device']['systemtime'],
			agent_platform  	= auditDict['data']['system']['devicePlatform'],
			system_name      	= auditDict['data']['system']['systemName'],
			logged_on_user    	= auditDict['data']['system']['currentUser'],
			cpu_usage        	= auditDict['data']['system']['cpuUsage'],
			cpu_count        	= auditDict['data']['system']['cpuCount'],
			boot_time        	= auditDict['data']['system']['bootTime'],
            publicIp			= auditDict['data']['system']['publicIp'],
            system_model		= auditDict['data']['system']['systemmodel'],
			system_locale		= auditDict['data']['system']['systemlocale'],
			system_manufacturer = auditDict['data']['system']['systemmanufacturer']
		)
	)
	try:
		db.session.execute(upsertDeviceStatusSql)
		db.session.commit()
		log_with_route(logging.INFO, 'Upserting Device Status processed')
	except Exception as e:
		log_with_route(logging.ERROR, f'error upserting payload: Reason: {e}')
		log_with_route(logging.ERROR, f'Rolling back transaction...')
		db.session.rollback()
		log_with_route(logging.ERROR, f'Transaction rolled back.')

def upsertDeviceCpu(deviceUuid, auditDict):
	log_with_route(logging.INFO, f'Attempting to upsert Device Cpu for {deviceUuid}')
	if 'cpu' not in auditDict['data']:
		auditDict['data']['cpu'] 			= {}
		auditDict['data']['cpu']['cpuname'] = 'n/a'

	# Extract CPU metrics if available
	cpu_metrics_json = auditDict['data']['cpu'].get('cpu_metrics', None)

	upsertDeviceCpuSql = insert(DeviceCpu).values(
		deviceuuid			= deviceUuid,
		last_update    		= int(time.time()),
		last_json   		= auditDict['data']['device']['systemtime'],
		cpu_name			= auditDict['data']['cpu']['cpuname'],
		cpu_metrics_json	= cpu_metrics_json

	).on_conflict_do_update (
		index_elements=['deviceuuid'],
		set_= dict(
			deviceuuid			= deviceUuid,
			last_update    		= int(time.time()),
			last_json   		= auditDict['data']['device']['systemtime'],
			cpu_name			= auditDict['data']['cpu']['cpuname'],
			cpu_metrics_json	= cpu_metrics_json
		)
	)
	try:
		db.session.execute(upsertDeviceCpuSql)
		db.session.commit()
		log_with_route(logging.INFO, 'Upserting DeviceCpu processed')
	except Exception as e:
		log_with_route(logging.ERROR, f'error upserting DeviceCpu: Reason: {e}')
		log_with_route(logging.ERROR, f'Rolling back transaction...')
		db.session.rollback()
		log_with_route(logging.ERROR, f'Transaction rolled back.')

def upsertDeviceGpu(deviceUuid, auditDict):
	log_with_route(logging.INFO, f'Attempting to upsert Device Gpu for {deviceUuid}')
	if 'gpuinfo' not in auditDict['data']:
		auditDict['data']['gpuinfo'] 				= {}
		auditDict['data']['gpuinfo']['gpuvendor'] 	= 'n/a'
		auditDict['data']['gpuinfo']['gpuproduct']	= 'n/a'
		auditDict['data']['gpuinfo']['gpucolour']	= 'n/a'
		auditDict['data']['gpuinfo']['gpuhres']		= 'n/a'
		auditDict['data']['gpuinfo']['gpuvres']		= 'n/a'

	# Helper function to convert to integer or None if invalid
	def safe_int(value, default=None):
		"""Convert value to int, return default if conversion fails or value is 'No data found'"""
		if value in (None, 'No data found', 'n/a', ''):
			return default
		try:
			return int(value)
		except (ValueError, TypeError):
			return default

	# Sanitize integer fields - convert "No data found" to None for integer columns
	gpu_colour = safe_int(auditDict['data']['gpuinfo'].get('gpucolour'))
	gpu_hres = safe_int(auditDict['data']['gpuinfo'].get('gpuhres'))
	gpu_vres = safe_int(auditDict['data']['gpuinfo'].get('gpuvres'))
	# Clamp colour depth to signed 32-bit integer range to avoid overflow
	if gpu_colour is not None and gpu_colour > 2147483647:
		gpu_colour = 2147483647


	upsertDeviceGpuSql = insert(DeviceGpu).values(
		deviceuuid			= deviceUuid,
		last_update    		= int(time.time()),
		last_json   		= auditDict['data']['device']['systemtime'],
		gpu_vendor			= auditDict['data']['gpuinfo']['gpuvendor'],
		gpu_product			= auditDict['data']['gpuinfo']['gpuproduct'],
		gpu_colour			= gpu_colour,
		gpu_hres			= gpu_hres,
		gpu_vres			= gpu_vres

	).on_conflict_do_update (
		index_elements=['deviceuuid'],
		set_= dict(
			deviceuuid			= deviceUuid,
			last_update    		= int(time.time()),
			last_json   		= auditDict['data']['device']['systemtime'],
			gpu_vendor			= auditDict['data']['gpuinfo']['gpuvendor'],
			gpu_product			= auditDict['data']['gpuinfo']['gpuproduct'],
            gpu_colour			= gpu_colour,
            gpu_hres			= gpu_hres,
            gpu_vres			= gpu_vres
		)
	)
	try:
		db.session.execute(upsertDeviceGpuSql)
		db.session.commit()
		log_with_route(logging.INFO, 'Upserting DeviceGpu processed')
	except Exception as e:
		log_with_route(logging.ERROR, f'error upserting DeviceGpu: Reason: {e}')
		log_with_route(logging.ERROR, f'Rolling back transaction...')
		db.session.rollback()
		log_with_route(logging.ERROR, f'Transaction rolled back.')

def upsertDeviceBios(deviceUuid, auditDict):
	log_with_route(logging.INFO, f'Attempting to upsert Device bios for {deviceUuid}')
	if 'bios' not in auditDict['data']:
		auditDict['data']['bios'] 					= {}
		auditDict['data']['bios']['biosvendor']		= 'n/a'
		auditDict['data']['bios']['serialnumber']	= 'n/a'
		auditDict['data']['bios']['biosversion']	= 'n/a'
	upsertDeviceBiosSql = insert(DeviceBios).values(
		deviceuuid			= deviceUuid,
		last_update    		= int(time.time()),
		last_json   		= auditDict['data']['device']['systemtime'],
		bios_vendor			= auditDict['data']['bios']['biosvendor'],
		bios_name			= 'n/a',
		bios_serial			= auditDict['data']['bios']['serialnumber'],
		bios_version		= auditDict['data']['bios']['biosversion']

	).on_conflict_do_update (
		index_elements=['deviceuuid'],
		set_= dict(
			deviceuuid			= deviceUuid,
			last_update    		= int(time.time()),
			last_json   		= auditDict['data']['device']['systemtime'],
			bios_vendor			= auditDict['data']['bios']['biosvendor'],
			bios_name			= 'n/a',
			bios_serial			= auditDict['data']['bios']['serialnumber'],
			bios_version		= auditDict['data']['bios']['biosversion']
		)
	)
	try:
		db.session.execute(upsertDeviceBiosSql)
		db.session.commit()
		log_with_route(logging.INFO, 'Upserting DeviceBios processed')
	except Exception as e:
		log_with_route(logging.ERROR, f'error upserting DeviceBios: Reason: {e}')
		log_with_route(logging.ERROR, f'Rolling back transaction...')
		db.session.rollback()
		log_with_route(logging.ERROR, f'Transaction rolled back.')

def upsertDeviceColl(deviceUuid, auditDict):
	log_with_route(logging.INFO, f'Attempting to upsert Device Collector for {deviceUuid}')
	if 'collector' not in auditDict['data']:
		auditDict['data']['collector'] 						= {}
		auditDict['data']['collector']['collversion']		= 0
		auditDict['data']['collector']['collinstalldir']   	= 'collector needs upgrade'
	upsertDeviceCollSql = insert(DeviceCollector).values(
		deviceuuid			= deviceUuid,
		last_update    		= int(time.time()),
		last_json   		= auditDict['data']['device']['systemtime'],
		coll_version		= auditDict['data']['collector']['collversion'],
		coll_install_dir   	= auditDict['data']['collector']['collinstalldir']
	).on_conflict_do_update (
		index_elements=['deviceuuid'],
		set_= dict(
			deviceuuid			= deviceUuid,
			last_update    		= int(time.time()),
			last_json   		= auditDict['data']['device']['systemtime'],
			coll_version		= auditDict['data']['collector'].get('collversion', 0),
			coll_install_dir   	= auditDict['data']['collector'].get('collinstalldir', 'collector needs upgrade')
		)
	)
	try:
		db.session.execute(upsertDeviceCollSql)
		db.session.commit()
		log_with_route(logging.INFO, 'Upserting DeviceCollector processed')
	except Exception as e:
		log_with_route(logging.ERROR, f'error upserting DeviceCollector: Reason: {e}')
		log_with_route(logging.ERROR, f'Rolling back transaction...')
		db.session.rollback()
		log_with_route(logging.ERROR, f'Transaction rolled back.')

def upsertDeviceAgent(deviceUuid, data):
	log_with_route(logging.INFO, f'Attempting to upsert Device Agent for {deviceUuid}')
	if 'agent' not in data['data']:
		data['data']['agent'] 						= {}
		data['data']['agent']['agentversion']		= 0
		data['data']['agent']['agentinstalldir']   = 'agent needs upgrade'
	upsertDeviceAgentSql = insert(DeviceCollector).values(
		deviceuuid			= deviceUuid,
		last_update    		= int(time.time()),
		agent_version		= data['data']['agent']['agentversion'],
		agent_install_dir   = data['data']['agent']['agentinstalldir']
	).on_conflict_do_update (
		index_elements=['deviceuuid'],
		set_= dict(
			deviceuuid			= deviceUuid,
			last_update    		= int(time.time()),
			last_json   		= data['data']['device']['systemtime'],
			agent_version		= data['data']['agent']['agentversion'],
			agent_install_dir   = data['data']['agent']['agentinstalldir']
		)
	)
	try:
		db.session.execute(upsertDeviceAgentSql)
		db.session.commit()
		log_with_route(logging.INFO, 'Upserting DeviceAgent processed')
	except Exception as e:
		log_with_route(logging.ERROR, f'error upserting DeviceAgent: Reason: {e}')
		log_with_route(logging.ERROR, f'Rolling back transaction...')
		db.session.rollback()
		log_with_route(logging.ERROR, f'Transaction rolled back.')


def upsertDeviceBattery(deviceUuid, auditDict):
	log_with_route(logging.INFO, f'Attempting to upsert Device Battery for {deviceUuid}')
	# Sanitize secsLeft to numeric to avoid DB integer errors
	battery_data = auditDict.get('data', {}).get('battery', {})
	def _sanitize_secs(value):
		if value in (None, 'N/A', 'n/a', 'No data found', ''):
			return -1
		try:
			return int(value)
		except (ValueError, TypeError):
			return -1
	secs_remaining_val = _sanitize_secs(battery_data.get('secsLeft'))

	upsertDeviceBatterySql = insert(DeviceBattery).values(
		deviceuuid			= deviceUuid,
		last_update    		= int(time.time()),
		last_json   		= auditDict['data']['device']['systemtime'],
		battery_installed	= auditDict['data']['battery']['installed'],
		percent_charged   	= auditDict['data']['battery']['pcCharged'],
		secs_remaining   	= secs_remaining_val,
		on_mains_power		= auditDict['data']['battery']['powerPlug']
	).on_conflict_do_update (
		index_elements=['deviceuuid'],
		set_= dict(
			deviceuuid			= deviceUuid,
			last_update    		= int(time.time()),
			last_json   		= auditDict['data']['device']['systemtime'],
			battery_installed	= auditDict['data']['battery']['installed'],
			percent_charged   	= auditDict['data']['battery']['pcCharged'],
			secs_remaining   	= secs_remaining_val,
			on_mains_power		= auditDict['data']['battery']['powerPlug']
		)
	)
	try:
		db.session.execute(upsertDeviceBatterySql)
		db.session.commit()
		log_with_route(logging.INFO, 'Upserting DeviceBattery processed')
	except Exception as e:
		log_with_route(logging.ERROR, f'error upserting DeviceBattery: Reason: {e}')
		log_with_route(logging.ERROR, f'Rolling back transaction...')
		db.session.rollback()
		log_with_route(logging.ERROR, f'Transaction rolled back.')

def upsertDeviceMemory(deviceUuid, auditDict):
	log_with_route(logging.INFO, f'Attempting to upsert DeviceMemory for {deviceUuid}')
	totalMemory			= auditDict['data']['memory']['total']
	availableMemory		= auditDict['data']['memory']['available']
	usedMemory			= auditDict['data']['memory']['used']
	freeMemory			= auditDict['data']['memory']['free']
	memUsedPercent    	= (usedMemory/totalMemory) * 100
	memFreePercent    	= 100 - memUsedPercent
	cacheMemory        	= totalMemory - freeMemory - usedMemory

	# Extract memory metrics if available
	memory_metrics_json = auditDict['data']['memory'].get('memory_metrics', None)

	upsertDeviceMemorySql = insert(DeviceMemory).values(
		deviceuuid				= deviceUuid,
		last_update    			= int(time.time()),
		last_json   			= auditDict['data']['device']['systemtime'],
		total_memory			= totalMemory,
		available_memory   		= availableMemory,
		used_memory   			= usedMemory,
		free_memory				= freeMemory,
		mem_used_percent		= memUsedPercent,
		mem_free_percent		= memFreePercent,
		cache_memory			= cacheMemory,
		memory_metrics_json		= memory_metrics_json
	).on_conflict_do_update (
		index_elements=['deviceuuid'],
		set_= dict(
			deviceuuid				= deviceUuid,
			last_update    			= int(time.time()),
			last_json   			= auditDict['data']['device']['systemtime'],
			total_memory			= totalMemory,
			available_memory   		= availableMemory,
			used_memory   			= usedMemory,
			free_memory				= freeMemory,
			mem_used_percent		= memUsedPercent,
			mem_free_percent		= memFreePercent,
			cache_memory			= cacheMemory,
			memory_metrics_json		= memory_metrics_json
		)
	)
	try:
		db.session.execute(upsertDeviceMemorySql)
		db.session.commit()
		log_with_route(logging.INFO, 'Upserting DeviceMemory processed')
	except Exception as e:
		log_with_route(logging.ERROR, f'error upserting DeviceMemory: Reason: {e}')
		log_with_route(logging.ERROR, f'Rolling back transaction...')
		db.session.rollback()
		log_with_route(logging.ERROR, f'Transaction rolled back.')

def upsertDeviceNetworks(deviceUuid, auditDict):
	log_with_route(logging.INFO, f'Attempting to upsert DeviceNetworks for {deviceUuid}')
	for network in auditDict['data']['networkList']:
		for key, value in network.items():
			log_with_route(logging.INFO, f'Processing key: {key}')
			address_4           = value.get('address4', 'Not Present')
			netmask_4           = value.get('netmask4', 'Not Present')
			broadcast_4         = value.get('broadcast4', 'Not Present')
			address_6           = value.get('address6', 'Not Present')
			netmask_6           = value.get('netmask6', 'Not Present')
			broadcast_6         = value.get('broadcast6', 'Not Present')
			if not address_4:
				address_4 = 'Not Present'
			if not netmask_4:
				netmask_4 = 'Not Present'
			if not broadcast_4:
				broadcast_4 = 'Not Present'
			if not address_6:
				address_6 = 'Not Present'
			if not netmask_6:
				netmask_6 = 'Not Present'
			if not broadcast_6:
				broadcast_6 = 'Not Present'

			upsertDeviceNetworksSql = insert(DeviceNetworks).values(
				deviceuuid 		    = deviceUuid,
				last_update 	    = int(time.time()),
				last_json 		    = auditDict['data']['device']['systemtime'],
				network_name        = key,
				if_is_up            = value['ifIsUp'],
				if_speed            = value['ifSpeed'],
				if_mtu              = value['ifMtu'],
				bytes_sent          = value['bytesSent'],
				bytes_rec           = value['bytesRecv'],
				err_in              = value['errIn'],
				err_out             = value['errOut'],
				address_4           = address_4,
				netmask_4           = netmask_4,
				broadcast_4         = broadcast_4,
				address_6           = address_6,
				netmask_6           = netmask_6,
				broadcast_6         = broadcast_6
			).on_conflict_do_update (
				index_elements=['deviceuuid', 'network_name'],
				set_= dict(
						deviceuuid 		    = deviceUuid,
						last_update 	    = int(time.time()),
						last_json 		    = auditDict['data']['device']['systemtime'],
						network_name        = key,
						if_is_up            = value['ifIsUp'],
						if_speed            = value['ifSpeed'],
						if_mtu              = value['ifMtu'],
						bytes_sent          = value['bytesSent'],
						bytes_rec           = value['bytesRecv'],
						err_in              = value['errIn'],
						err_out             = value['errOut'],
						address_4           = address_4,
						netmask_4           = netmask_4,
						broadcast_4         = broadcast_4,
						address_6           = address_6,
						netmask_6           = netmask_6,
						broadcast_6         = broadcast_6
				)
			)
			try:
				db.session.execute(upsertDeviceNetworksSql)
				db.session.commit()
				log_with_route(logging.INFO, 'Upserting DeviceNetworks processed')
			except Exception as e:
				log_with_route(logging.ERROR, f'Error upserting DeviceNetworks: Reason: {e}')
				log_with_route(logging.ERROR, f'Rolling back transaction...')
				db.session.rollback()
				log_with_route(logging.ERROR, f'Transaction rolled back.')

def upsertDeviceUsers(deviceUuid, auditDict):
	log_with_route(logging.INFO, f'Attempting to upsert DeviceUsers for {deviceUuid}')
	for user in auditDict['data']['Users']:
		for key, value in user.items():
			log_with_route(logging.INFO, f'Processing key: {key}')

			upsertDeviceUsersSql = insert(DeviceUsers).values(
                deviceuuid 		    = deviceUuid,
                last_update 	    = int(time.time()),
                last_json 		    = auditDict['data']['device']['systemtime'],
                users_name        	= value['username'],
                terminal            = value['terminal'],
                host            	= value['host'],
                loggedin           	= value['loggedIn'],
                pid          		= value['pid']
			).on_conflict_do_update (
				index_elements=['deviceuuid', 'users_name'],
					set_= dict(
					deviceuuid 		    = deviceUuid,
					last_update 	    = int(time.time()),
					last_json 		    = auditDict['data']['device']['systemtime'],
					users_name        	= value['username'],
					terminal            = value['terminal'],
					host            	= value['host'],
					loggedin           	= value['loggedIn'],
					pid          		= value['pid']
				)
			)
			try:
				db.session.execute(upsertDeviceUsersSql)
				db.session.commit()
				log_with_route(logging.INFO, 'Upserting DeviceUsers processed')
			except Exception as e:
				log_with_route(logging.ERROR, f'Error upserting DeviceUsers: Reason: {e}')
				log_with_route(logging.ERROR, f'Rolling back transaction...')
				db.session.rollback()
				log_with_route(logging.ERROR, f'Transaction rolled back.')

def upsertDevicePartitions(deviceUuid, auditDict):
	if 'partitions' in auditDict['data']:
		log_with_route(logging.INFO, f'Attempting to upsert DevicePartitions for {deviceUuid}')
		for partition in auditDict['data']['partitions']:
			for key, value in partition.items():
				log_with_route(logging.INFO, f'Processing key: {key}')

				upsertDevicePartitionsSql = insert(DevicePartitions).values(
					deviceuuid 		    = deviceUuid,
					last_update 	    = int(time.time()),
					last_json 		    = auditDict['data']['device']['systemtime'],
					partition_name      = key,
					partition_device    = value['device'],
					partition_fs_type   = value['fstype']
				).on_conflict_do_update (
					index_elements=['deviceuuid', 'partition_name'],
						set_= dict(
								deviceuuid 		    = deviceUuid,
								last_update 	    = int(time.time()),
								last_json 		    = auditDict['data']['device']['systemtime'],
								partition_name      = key,
								partition_device    = value['device'],
								partition_fs_type   = value['fstype']
					)
				)
				try:
					db.session.execute(upsertDevicePartitionsSql)
					db.session.commit()
					log_with_route(logging.INFO, 'Upserting DevicePartitions processed')
				except Exception as e:
					log_with_route(logging.ERROR, f'Error upserting DevicePartitions: Reason: {e}')
					log_with_route(logging.ERROR, f'Rolling back transaction...')
					db.session.rollback()
					log_with_route(logging.ERROR, f'Transaction rolled back.')
	else:
		log_with_route(logging.INFO, 'No DevicePartitions data to process')

def upsertDeviceDrives(deviceUuid, auditDict):
	log_with_route(logging.INFO, f'Attempting to upsert DeviceDrives for {deviceUuid}')

	# Check if drives data exists
	if 'drives' not in auditDict['data']:
		log_with_route(logging.WARNING, f'No drives data found for device {deviceUuid}')
		return

	for drive in auditDict['data']['drives']:
		# Validate required drive fields
		required_fields = ['name', 'total', 'used', 'free', 'usedPer', 'freePer']
		if not all(field in drive for field in required_fields):
			log_with_route(logging.ERROR, f'Missing required fields in drive data: {drive}')
			continue

		log_with_route(logging.INFO, f'Processing drive: {drive["name"]}')

		upsertDeviceDriveSql = insert(DeviceDrives).values(
			deviceuuid 		        = deviceUuid,
			last_update 	        = int(time.time()),
			last_json 		        = auditDict['data']['device']['systemtime'],
			drive_name              = drive['name'],
			drive_total             = drive['total'],
			drive_used              = drive['used'],
			drive_free              = drive['free'],
			drive_used_percentage   = drive['usedPer'],
			drive_free_percentage   = drive['freePer']
		).on_conflict_do_update (
			index_elements=['deviceuuid', 'drive_name'],
				set_= dict(
					deviceuuid 		        = deviceUuid,
					last_update 	        = int(time.time()),
					last_json 		        = auditDict['data']['device']['systemtime'],
					drive_name              = drive['name'],
					drive_total             = drive['total'],
					drive_used              = drive['used'],
					drive_free              = drive['free'],
					drive_used_percentage   = drive['usedPer'],
					drive_free_percentage   = drive['freePer']
			)
		)
		try:
			db.session.execute(upsertDeviceDriveSql)
			db.session.commit()
			log_with_route(logging.INFO, f'Successfully upserted drive: {drive["name"]}')
		except Exception as e:
			log_with_route(logging.ERROR, f'Error upserting drive {drive["name"]}: Reason: {e}')
			log_with_route(logging.ERROR, f'Rolling back transaction...')
			db.session.rollback()
			log_with_route(logging.ERROR, f'Transaction rolled back.')

	log_with_route(logging.INFO, f'Completed processing drives for device {deviceUuid}')

def upsertDevicePrinters(deviceUuid, auditDict):
	log_with_route(logging.INFO, f'Attempting to upsert DevicePrinters for {deviceUuid}')
	if 'printers' in auditDict['data']:
		printers_raw = auditDict['data']['printers']
		# Accept both dict and list formats from collectors
		if isinstance(printers_raw, list):
			printers_dict = {}
			for name in printers_raw:
				if isinstance(name, str) and name.strip():
					printers_dict[name.strip()] = {
						'drivername': 'unknown',
						'location': 'unknown',
						'printerstatus': 'unknown',
						'portname': 'unknown',
						'default': False
					}
		else:
			printers_dict = printers_raw if isinstance(printers_raw, dict) else {}

		if len(printers_dict) > 0:
			for printerName, printerData in printers_dict.items():
				log_with_route(logging.INFO, f'Processing key: {printerName}')
				if not 'drivername' in printerData:
					printerData['drivername'] = 'unknown'
				if not 'location' in printerData:
					printerData['location'] = 'unknown'
				if not 'printerstatus' in printerData:
					printerData['printerstatus'] = 'unknown'
				if 'port' in printerData:
					printerData['portname'] = printerData.pop('port')
				if not 'portname' in printerData:
					printerData['portname'] = 'unknown'
				if not 'default' in printerData:
					printerData['default'] = False
				log_with_route(logging.DEBUG, f'printerData: {printerData}')
				log_with_route(logging.DEBUG, f"printerData-portname: {printerData['portname']}")
				upsertDevicePrinterSql = insert(DevicePrinters).values(
					deviceuuid 		        = deviceUuid,
					last_update 	        = int(time.time()),
					last_json 		        = auditDict['data']['device']['systemtime'],
					printer_name            = printerName,
					printer_driver          = printerData['drivername'],
					printer_port			= printerData['portname'],
					printer_location        = printerData['location'],
					printer_status          = printerData['printerstatus'],
					printer_default 		= printerData['default']
				).on_conflict_do_update (
					index_elements=['deviceuuid', 'printer_name'],
						set_= dict(
							deviceuuid 		        = deviceUuid,
							last_update 	        = int(time.time()),
							last_json 		        = auditDict['data']['device']['systemtime'],
							printer_name            = printerName,
							printer_driver          = printerData['drivername'],
							printer_port			= printerData['portname'],
							printer_location        = printerData['location'],
							printer_status          = printerData['printerstatus'],
							printer_default 		= printerData['default']
					)
				)
				try:
					db.session.execute(upsertDevicePrinterSql)
					db.session.commit()
					log_with_route(logging.INFO, 'Upserting DevicePrinters processed')
				except Exception as e:
					log_with_route(logging.ERROR, f'Error upserting DevicePrinters: Reason: {e}')
					log_with_route(logging.ERROR, f'Rolling back transaction...')
					db.session.rollback()
					log_with_route(logging.ERROR, f'Transaction rolled back.')
	else:
		log_with_route(logging.INFO, 'No DevicePrinters data.')

def upsertDeviceDrivers(deviceUuid, auditDict):
	log_with_route(logging.INFO, f'Attempting to upsert DeviceDrivers for {deviceUuid}')

	# Check if device is Windows before processing driver data
	from app.models import DeviceStatus
	device_status = DeviceStatus.query.filter_by(deviceuuid=deviceUuid).first()
	if not device_status or not device_status.agent_platform.startswith('Windows'):
		platform = device_status.agent_platform if device_status else 'Unknown'
		log_with_route(logging.INFO, f'Skipping driver data processing for non-Windows device {deviceUuid} (platform: {platform})')
		return

	if 'drivers' in auditDict['data']:
		drivers_raw = auditDict['data']['drivers']
		# Accept both dict and list formats from collectors
		if isinstance(drivers_raw, list):
			drivers_dict = {}
			for entry in drivers_raw:
				if isinstance(entry, str):
					# Format seen: "Name<spaces>Status"; take first token as name
					name = entry.strip().split()[0] if entry.strip() else None
					if not name:
						continue
					drivers_dict[name] = {
						'description': 'unknown',
						'driverpath': 'unknown',
						'drivertype': 'unknown',
						'version': 'unknown',
						'driverdate': 0
					}
		else:
			drivers_dict = drivers_raw if isinstance(drivers_raw, dict) else {}

		if len(drivers_dict) > 0:
			for driverName, driverData in drivers_dict.items():
				log_with_route(logging.INFO, f'Processing key: {driverName}')
				# Ensure required keys exist with safe defaults
				if 'driverdate' not in driverData:
					driverData['driverdate'] = 0
				for req in ['description','driverpath','drivertype','version']:
					if req not in driverData:
						driverData[req] = 'unknown'

				upsertDeviceDriversSql = insert(DeviceDrivers).values(
					deviceuuid 		        = deviceUuid,
					last_update 	        = int(time.time()),
					last_json 		        = auditDict['data']['device']['systemtime'],
					driver_name            	= driverName,
					driver_description      = driverData['description'],
					driver_path				= driverData['driverpath'],
					driver_type        		= driverData['drivertype'],
					driver_version         	= driverData['version'],
					driver_date				= driverData['driverdate']
				).on_conflict_do_update (
					index_elements=['deviceuuid', 'driver_name'],
						set_= dict(
							deviceuuid 		        = deviceUuid,
							last_update 	        = int(time.time()),
							last_json 		        = auditDict['data']['device']['systemtime'],
							driver_name            	= driverName,
							driver_description      = driverData['description'],
							driver_path				= driverData['driverpath'],
							driver_type        		= driverData['drivertype'],
							driver_version         	= driverData['version'],
							driver_date				= driverData['driverdate']
							)
				)
				try:
					db.session.execute(upsertDeviceDriversSql)
					db.session.commit()
					log_with_route(logging.INFO, 'Upserting DeviceDrivers processed')
				except Exception as e:
					log_with_route(logging.ERROR, f'Error upserting DeviceDrivers: Reason: {e}')
					log_with_route(logging.ERROR, f'Rolling back transaction...')
					db.session.rollback()
					log_with_route(logging.ERROR, f'Transaction rolled back.')
	else:
		log_with_route(logging.INFO, 'No DeviceDrivers data.')

def validatePayloadJson(payload):
	log_with_route(logging.INFO, f'Validating: {payload}')
	try:
		with open(payload, 'r') as f:
			tmpDict = json.load(f)
		log_with_route(logging.INFO, f'{payload} is valid JSON')
		deviceUuid  = tmpDict['data']['device']['deviceUuid']
		groupUuid = tmpDict['data']['device'].get('groupUuid', '999999999-9999-9999-9999-999999999999')
		log_with_route(logging.INFO, f'deviceUuid: {deviceUuid} | groupUuid: {groupUuid}')
		return(deviceUuid, groupUuid)
	except Exception as e:
		log_with_route(logging.ERROR, f'{payload} is invalid payload. Reason: {e}')
		return(None, None)

def getAuditDict(auditFile):
    log_with_route(logging.INFO, f'Getting auditDict from {auditFile}')
    try:
        with open(auditFile, 'r') as f:
            auditDict = json.load(f)
        log_with_route(logging.INFO, f'Successfully read {auditFile} into auditDict')
        log_with_route(logging.DEBUG, f'auditDict: {auditDict}')
        return(auditDict)
    except Exception as e:
        log_with_route(logging.ERROR, f'Failed to open {auditFile}')

def getPayloadQueue(queueDir):
    payloadstoProcessList = []
    log_with_route(logging.INFO, f'Getting list of files from: {queueDir}')
    try:
        for payloadFile in os.listdir(queueDir):
            # Get the full path but preserve the original filename format
            full_path = os.path.join(queueDir, payloadFile)
            if os.path.isfile(full_path):  # Only add if it's a file
                payloadstoProcessList.append(payloadFile)

        log_with_route(logging.DEBUG, f'payloadstoProcessList: {payloadstoProcessList}')
        return payloadstoProcessList
    except Exception as e:
        log_with_route(logging.ERROR, f'Error reading directory {queueDir}: {str(e)}')
        return []

def getDeviceValidity(deviceUuid):
    log_with_route(logging.INFO, f'Validating device: {deviceUuid}')
    try:
        isValidDevice = Devices.query.filter_by(deviceuuid=deviceUuid).first()
    except Exception as e:
        log_with_route(logging.ERROR, f'Failed to query device: {deviceUuid}. Reason: {e}')
        return(False)
    if isValidDevice:
        log_with_route(logging.INFO, f'device {deviceUuid} found in devices table.')
        return(True)
    else:
        log_with_route(logging.ERROR, f'device {deviceUuid} not found in devices table.')
        return(False)

def reregisterOrphanedDevice(deviceUuid, audit_data=None):
    """Attempt to re-register a device that was deleted, with strict tenant isolation"""
    log_with_route(logging.INFO, f'Attempting to re-register orphaned device: {deviceUuid}')

    # First, try to restore from backup if available
    from app.utilities.device_restore import find_device_backup, restore_device_from_backup

    backup_path = find_device_backup(deviceUuid)
    if backup_path:
        log_with_route(logging.INFO, f'Found backup for device {deviceUuid}, attempting full restoration from backup')
        success, message = restore_device_from_backup(deviceUuid, backup_path)
        if success:
            log_with_route(logging.INFO, f'Successfully restored device {deviceUuid} from backup: {message}')
            return True
        else:
            log_with_route(logging.WARNING, f'Failed to restore device {deviceUuid} from backup: {message}. Falling back to basic re-registration.')
            # Fall through to basic re-registration below

    # If no backup or backup restoration failed, use basic re-registration from audit data
    log_with_route(logging.INFO, f'No backup found for device {deviceUuid}, attempting basic re-registration from audit data')

    try:
        # Extract device name, hardware info, and especially the group UUID from audit data
        device_name = None
        hardware_info = None
        group_uuid = None

        if audit_data and isinstance(audit_data, dict):
            if 'data' in audit_data and 'device' in audit_data['data']:
                if 'deviceName' in audit_data['data']['device']:
                    device_name = audit_data['data']['device']['deviceName']
                elif 'systemName' in audit_data['data'].get('system', {}):
                    device_name = audit_data['data']['system']['systemName']

                # Try to get hardware info
                if 'hardwareinfo' in audit_data['data']['device']:
                    hardware_info = audit_data['data']['device']['hardwareinfo']
                elif 'devicePlatform' in audit_data['data'].get('system', {}):
                    hardware_info = audit_data['data']['system']['devicePlatform']

                # CRITICAL: Must have the original groupUuid to prevent tenant bleed
                if 'groupUuid' in audit_data['data']['device']:
                    group_uuid = audit_data['data']['device']['groupUuid']

        # Default values if not found in audit
        if not device_name:
            device_name = f"Reconnected-{deviceUuid}"

        if not hardware_info:
            hardware_info = "Unknown Platform"

        # CRITICAL SECURITY CHECK: We MUST have a valid group UUID that exists in the database
        # to prevent tenant bleed - never assign to a random group
        if not group_uuid:
            log_with_route(logging.ERROR, f"No groupUuid found in audit data for device {deviceUuid}, cannot re-register")
            return False

        # Verify the group exists
        group = Groups.query.filter_by(groupuuid=group_uuid).first()
        if not group:
            log_with_route(logging.ERROR, f"Group {group_uuid} specified in audit data no longer exists, cannot re-register device {deviceUuid}")
            return False

        # Create the device only if we have the original group
        new_device = Devices(
            deviceuuid=deviceUuid,
            devicename=device_name,
            hardwareinfo=hardware_info,
            groupuuid=group_uuid,
            orguuid=group.orguuid,
            tenantuuid=group.tenantuuid,
            created_at=int(time.time())
        )

        db.session.add(new_device)

        # Create a system message for the reconnection
        system_useruuid = '00000000-0000-0000-0000-000000000000'

        # Get or create a conversation for the device
        conversation_uuid = str(uuid.uuid4())
        conversation = Conversations(
            conversationuuid=conversation_uuid,
            tenantuuid=group.tenantuuid,
            entityuuid=deviceUuid,
            entity_type='device',
            last_updated=int(time.time())
        )
        db.session.add(conversation)

        # Create a message for the device re-registration
        message = Messages(
            messageuuid=str(uuid.uuid4()),
            conversationuuid=conversation_uuid,
            useruuid=system_useruuid,
            tenantuuid=group.tenantuuid,
            entityuuid=deviceUuid,
            entity_type='device',
            title="Device Re-registered",
            content=f"Device '{device_name}' has reconnected after being deleted. It has been automatically re-registered in its original group '{group.groupname}'",
            is_read=False,
            created_at=int(time.time()),
            message_type='chat'
        )

        db.session.add(message)
        db.session.commit()

        log_with_route(logging.INFO, f"Successfully re-registered device: {deviceUuid} in its original group {group_uuid}")

        # Schedule default snippets for the device
        try:
            scheduleDefaultSnippets(deviceUuid, hardware_info)
            log_with_route(logging.INFO, f'Successfully scheduled default snippets for {deviceUuid}')
        except Exception as e:
            log_with_route(logging.ERROR, f'Error scheduling default snippets: {str(e)}')

        return True

    except Exception as e:
        db.session.rollback()
        log_with_route(logging.ERROR, f'Failed to re-register device: {str(e)}')
        return False

def readJsonSchema(payloadAuditSchemaFile):
	log_with_route(logging.INFO, f'Reading payloadAuditSchema file: {payloadAuditSchemaFile}')

	payloadAuditSchema = None
	try:
		with open(payloadAuditSchemaFile, 'r') as f:
			payloadAuditSchema = json.load(f)
		log_with_route(logging.INFO, 'payloadAuditSchema read successfully.')
	except Exception as e:
		log_with_route(logging.ERROR, f'Failed to read {payloadAuditSchemaFile}. Reason: {e}')
		return None

	if not isinstance(payloadAuditSchema, dict):
		log_with_route(
			logging.ERROR,
			f'Invalid schema type in {payloadAuditSchemaFile}: expected object/dict, got {type(payloadAuditSchema).__name__}'
		)
		return None

	return payloadAuditSchema

def validateData(data, payloadAuditSchema):
    log_with_route(logging.INFO, 'Validating data...')
    try:
        validate(instance=data, schema=payloadAuditSchema)
        log_with_route(logging.INFO, 'Received JSON is valid.')
        return True, data
    except ValidationError as e:
        log_with_route(logging.ERROR, f'Received JSON is invalid. Reason: {e}')
        return False, data

def writeBadFile(badDir, data, type):
    outFile = os.path.join(badDir, f'{time.time()}.{type}.json')
    try:
        with open(outFile, 'w') as f:
            f.write(json.dumps(data))
        log_with_route(logging.INFO, f'Bad data written to: {outFile}')
        return True
    except Exception as e:
        log_with_route(logging.ERROR, f'Failed to write bad data to {outFile}. Reason: {e}')
        return False

def writeJsonFile(queueDir, jsonData, deviceUuid, type):
    outFile = os.path.join(queueDir, f'{deviceUuid}.{time.time()}.{type}.json')
    try:
        with open(outFile, 'w') as f:
            f.write(json.dumps(jsonData, indent=4))
        log_with_route(logging.INFO, f'Data written to: {outFile}')
        return True
    except Exception as e:
        log_with_route(logging.ERROR, f'Failed to write to {outFile}. Reason: {e}')
        return False

def checkDir(dirToCheck):
    if os.path.isdir(dirToCheck):
        pass
    else:
        log_with_route(logging.INFO, f'{dirToCheck} does not exist. Creating...')
        try:
            os.makedirs(dirToCheck, mode=0o775, exist_ok=True)
            # Set proper ownership to avoid permission issues
            import pwd
            import grp
            try:
                uid = pwd.getpwnam('wegweiser').pw_uid
                gid = grp.getgrnam('www-data').gr_gid
                os.chown(dirToCheck, uid, gid)
            except (KeyError, PermissionError) as perm_err:
                log_with_route(logging.WARNING, f'Could not set ownership on {dirToCheck}: {perm_err}')
            log_with_route(logging.INFO, f'{dirToCheck} created with proper permissions.')
        except Exception as e:
            log_with_route(logging.ERROR, f'Failed to create {dirToCheck}. Reason: {e}')

def sendJsonPayloadFlask(endpoint, payload, mode):
	url 		= f'{serverAddr}{endpoint}'
	log_with_route(logging.INFO, f'Attempting to connect to {url}')
	log_with_route(logging.INFO, f'sending: {json.dumps(payload)}')
	headers 	= {'Content-Type': 'application/json'}
	if mode == 'POST':
		response 	= requests.post(url, headers=headers, data=json.dumps(payload))
	elif mode == 'DELETE':
		response 	= requests.delete(url, headers=headers, data=json.dumps(payload))
	return(response)

def createTagDirect(tenantuuid, tagvalue):
	"""Create a tag directly without HTTP request to avoid recursion"""
	from app.models import Tags
	from sqlalchemy.dialects.postgresql import insert
	from sqlalchemy.exc import IntegrityError
	import uuid
	import time

	log_with_route(logging.INFO, f'Creating tag directly: {tagvalue} for tenant: {tenantuuid}')

	# Check if the tag already exists
	tag = Tags.query.filter_by(tagvalue=tagvalue, tenantuuid=tenantuuid).first()
	if not tag:
		# Create the new tag
		taguuid = str(uuid.uuid4())
		insertNewTagSql = insert(Tags).values(
			taguuid=taguuid,
			tenantuuid=tenantuuid,
			tagvalue=tagvalue,
			created_at=int(time.time())
		)
		try:
			db.session.execute(insertNewTagSql)
			db.session.commit()
			log_with_route(logging.INFO, f'New tag created directly: {tagvalue} with UUID: {taguuid}')
			return taguuid
		except IntegrityError as e:
			db.session.rollback()
			if 'duplicate key value violates unique constraint' in str(e.orig):
				# Tag was created by another process, fetch it
				tag = Tags.query.filter_by(tagvalue=tagvalue, tenantuuid=tenantuuid).first()
				if tag:
					return tag.taguuid
				log_with_route(logging.ERROR, f'Tag {tagvalue} creation failed with duplicate constraint')
				return None
			else:
				log_with_route(logging.ERROR, f'Error creating tag directly: {e}')
				return None
	else:
		log_with_route(logging.INFO, f'Tag already exists: {tagvalue} with UUID: {tag.taguuid}')
		return tag.taguuid

def assignTagDirect(deviceuuid, taguuid):
	"""Assign a tag to device directly without HTTP request to avoid recursion"""
	from app.models import TagsXDevices
	from sqlalchemy.dialects.postgresql import insert
	import time

	log_with_route(logging.INFO, f'Assigning tag directly: {taguuid} to device: {deviceuuid}')

	upsertAssignTagSql = insert(TagsXDevices).values(
		taguuid=taguuid,
		deviceuuid=deviceuuid,
		created_at=int(time.time())
	).on_conflict_do_update(
		index_elements=['deviceuuid', 'taguuid'],
		set_=dict(
			created_at=int(time.time())
		)
	)
	try:
		db.session.execute(upsertAssignTagSql)
		db.session.commit()
		log_with_route(logging.INFO, f'Tag {taguuid} assigned directly to device {deviceuuid}')
		return True
	except Exception as e:
		log_with_route(logging.ERROR, f'Error assigning tag directly: {e}')
		db.session.rollback()
		return False

def removeOldAutoTags(deviceUuid):
	"""Remove existing auto-assigned platform/OS tags before assigning new ones"""
	from app.models import TagsXDevices, Tags

	deviceUuid = str(deviceUuid)
	log_with_route(logging.INFO, f'Removing old auto-assigned tags for {deviceUuid}...')

	try:
		# Get all tag assignments for this device
		tag_assignments = TagsXDevices.query.filter_by(deviceuuid=deviceUuid).all()

		for assignment in tag_assignments:
			# Get the tag details
			tag = Tags.query.filter_by(taguuid=assignment.taguuid).first()
			if tag and '(auto)' in tag.tagvalue:
				# Check if it's a platform/OS tag that should be replaced
				if any(prefix in tag.tagvalue for prefix in ['Platform:', 'OSVersion:', 'OSSubVersion:']):
					log_with_route(logging.INFO, f'Removing old auto tag: {tag.tagvalue}')
					db.session.delete(assignment)

		db.session.commit()
		log_with_route(logging.INFO, f'Successfully removed old auto-assigned tags for {deviceUuid}')

	except Exception as e:
		log_with_route(logging.ERROR, f'Error removing old auto tags for {deviceUuid}: {e}')
		db.session.rollback()

def autoAssignTags(auditDict, deviceUuid):
	deviceUuid = str(deviceUuid)
	log_with_route(logging.INFO, f'Auto-assigning tags for {deviceUuid}...')

	# Remove existing auto-assigned platform/OS tags before assigning new ones
	removeOldAutoTags(deviceUuid)

	# Be defensive: devicePlatform may not contain 3 dash-separated parts
	platform_str = str(auditDict.get('data', {}).get('system', {}).get('devicePlatform', 'Unknown'))
	parts = platform_str.split('-') if platform_str else []
	platform_main = parts[0] if len(parts) > 0 and parts[0] else 'Unknown'
	platform_ver = parts[1] if len(parts) > 1 and parts[1] else 'Unknown'
	platform_subver = parts[2] if len(parts) > 2 and parts[2] else 'Unknown'

	devicePlatformTag = f"Platform: {platform_main} (auto)"
	log_with_route(logging.DEBUG, f'devicePlatformTag: {devicePlatformTag}')
	assignTags(deviceUuid, devicePlatformTag)
	osLevelTag = f"OSVersion: {platform_ver} (auto)"
	log_with_route(logging.DEBUG, f'osLevelTag: {osLevelTag}')
	assignTags(deviceUuid, osLevelTag)
	osSubVersionTag = f"OSSubVersion: {platform_subver} (auto)"
	log_with_route(logging.DEBUG, f'osSubVersionTag: {osSubVersionTag}')
	assignTags(deviceUuid, osSubVersionTag)

def assignTags(deviceuuid, tagValueToCreate):
	log_with_route(logging.INFO, f'Assigning tag {tagValueToCreate} to {deviceuuid}')
	tenantResult = Devices.query.filter_by(deviceuuid=deviceuuid).first()
	if not tenantResult:
		log_with_route(logging.ERROR, f'tenantuuid for deviceuuid {deviceuuid} not found')
		return(False)
	else:
		tenantuuid = tenantResult.tenantuuid
		log_with_route(logging.INFO, f'tenantuuid for deviceuuid {deviceuuid} is {tenantuuid}')
		tagExists  = Tags.query.filter_by(tenantuuid=tenantuuid, tagvalue=tagValueToCreate).first()
		log_with_route(logging.DEBUG, f'tagExists: {tagExists}')
		if not tagExists: # create a new tag
			log_with_route(logging.INFO, f'tag {tagValueToCreate} does not exist for tenantuuid {tenantuuid}')
			# Use direct function call instead of HTTP request to avoid recursion
			tagUuid = createTagDirect(str(tenantuuid), tagValueToCreate)
			if tagUuid:
				log_with_route(logging.INFO, f'Successfully created tag: {tagValueToCreate} | newTagUuid: {tagUuid}')
			else:
				log_with_route(logging.ERROR, f'Failed to create tag: {tagValueToCreate}')
				return(False)
		else: # tag already exists, get the taguuid
			tagUuid = str(tagExists.taguuid)

		# Use direct function call instead of HTTP request to avoid recursion
		success = assignTagDirect(str(deviceuuid), str(tagUuid))
		if success:
			log_with_route(logging.INFO, f'Successfully assigned tag: {tagUuid} to deviceuuid: {deviceuuid}')
			return(True)
		else:
			log_with_route(logging.ERROR, f'Failed to assigned tag: {tagUuid} to deviceuuid: {deviceuuid}')
			return(False)

@payload_bp.route('/payload/serverroles', methods=['POST'])
@csrf.exempt
def receive_server_roles():
    try:
        data = request.get_json()
        device_uuid = data.get('deviceuuid')
        server_roles = data.get('ServerRoles', [])

        if not device_uuid:
            return jsonify({"status": "error", "data": "deviceuuid is required"}), 400

        if not server_roles:
            return jsonify({"status": "error", "data": "ServerRoles data is required"}), 400

        # Validate device UUID
        device = Devices.query.filter_by(deviceuuid=device_uuid).first()
        if not device:
            return jsonify({"status": "error", "data": "Invalid device UUID"}), 400

        tenant_uuid = device.tenantuuid

        for role in server_roles:
            role_name = role.get('Name')
            if role_name:
                tag_value = f"ServerRole: {role_name}"
                assign_tag_to_device(tenant_uuid, device_uuid, tag_value)

        return jsonify({"status": "success", "data": "Server roles processed and tags assigned"}), 200

    except Exception as e:
        log_with_route(logging.ERROR, f"Error processing server roles: {str(e)}", exc_info=True)
        return jsonify({"status": "error", "data": str(e)}), 500

def assign_tag_to_device(tenant_uuid, device_uuid, tag_value):
    try:
        # Check if tag exists for this tenant
        tag = Tags.query.filter_by(
            tagvalue=tag_value,
            tenantuuid=tenant_uuid
        ).first()

        if not tag:
            # Create new tag with tenant-specific unique constraint
            tag_uuid = str(uuid.uuid4())
            try:
                new_tag = Tags(
                    taguuid=tag_uuid,
                    tenantuuid=tenant_uuid,
                    tagvalue=tag_value,
                    created_at=int(time.time())
                )
                db.session.add(new_tag)
                db.session.commit()
                log_with_route(logging.INFO, f"Created new tag '{tag_value}' with UUID {tag_uuid}")
            except IntegrityError as e:
                db.session.rollback()
                # If concurrent insert happened, get the existing tag
                tag = Tags.query.filter_by(
                    tagvalue=tag_value,
                    tenantuuid=tenant_uuid
                ).first()
                if not tag:
                    log_with_route(logging.ERROR, f"Failed to create or find tag '{tag_value}'")
                    raise
                tag_uuid = tag.taguuid
        else:
            tag_uuid = tag.taguuid
            log_with_route(logging.INFO, f"Using existing tag '{tag_value}' with UUID {tag_uuid}")

        # Assign tag to device using upsert
        try:
            device_tag = TagsXDevices(
                taguuid=tag_uuid,
                deviceuuid=device_uuid,
                created_at=int(time.time())
            )
            db.session.merge(device_tag)
            db.session.commit()
            log_with_route(logging.INFO, f"Assigned tag '{tag_value}' to device {device_uuid}")
            return True
        except Exception as e:
            db.session.rollback()
            log_with_route(logging.ERROR, f"Failed to assign tag to device: {str(e)}")
            raise

    except Exception as e:
        log_with_route(logging.ERROR, f"Error in assign_tag_to_device: {str(e)}", exc_info=True)
        raise








