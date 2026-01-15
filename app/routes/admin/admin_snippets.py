# Filepath: app/routes/admin/admin_snippets.py
# app/routes/admin_snippets.py
from flask import Blueprint, render_template, request, jsonify, current_app, flash
from flask_principal import Permission, RoleNeed
from app.forms.snippet_form import SnippetForm
import tempfile
import os
import time
import uuid
from app.models import db, Snippets, SnippetsSchedule, Devices
from app.utilities.app_logging_helper import log_with_route
import logging
import json
from werkzeug.utils import secure_filename
from datetime import datetime

admin_snippets_bp = Blueprint('admin_snippets_bp', __name__)
admin_permission = Permission(RoleNeed('admin'))

@admin_snippets_bp.route('/admin/snippets', methods=['GET', 'POST'])
@admin_permission.require(http_exception=403)
def manage_snippets():
    form = SnippetForm()
    
    # Populate device choices
    devices = Devices.query.all()
    form.target_devices.choices = [('ALL', 'All Devices'), ('TEST', 'Test Device')] + \
                                [(str(d.deviceuuid), d.devicename) for d in devices]
    
    if form.validate_on_submit():
        try:
            # Create necessary directories
            project_root = os.path.dirname(current_app.root_path)
            unsigned_dir = os.path.join(project_root, 'snippets', 'unSigned')
            signed_dir = os.path.join(project_root, 'snippets', '00000000-0000-0000-0000-000000000000')
            os.makedirs(unsigned_dir, exist_ok=True)
            os.makedirs(signed_dir, exist_ok=True)

            # Save private key temporarily
            key_file = tempfile.NamedTemporaryFile(delete=False)
            form.private_key.data.save(key_file.name)

            # Create wrapper script
            if form.script_type.data == 'powershell':
                wrapper = create_powershell_wrapper(form.script_content.data, form.metalogos_type.data)
            else:
                wrapper = create_python_wrapper(form.script_content.data, form.metalogos_type.data)

            # Save wrapper script
            script_path = os.path.join(unsigned_dir, f"{form.snippet_name.data}.py")
            with open(script_path, 'w') as f:
                f.write(wrapper)

            # Sign the script
            snippet_uuid = sign_script(script_path, key_file.name, signed_dir)

            # Create snippet record
            snippet = Snippets(
                snippetuuid=snippet_uuid,
                tenantuuid='00000000-0000-0000-0000-000000000000',
                snippetname=form.snippet_name.data,
                created_at=int(time.time()),
                max_exec_secs=form.max_exec_secs.data
            )
            db.session.add(snippet)

            # Create schedule if recurrence specified
            if form.schedule_recurrence.data:
                recurrence, interval = recStringToSeconds(form.schedule_recurrence.data)
                next_execution = int(time.time())
                
                # Handle different target device selections
                target_devices = []
                if form.target_devices.data == 'ALL':
                    target_devices = devices  # All devices from the database
                elif form.target_devices.data == 'TEST':
                    # Handle test device case if needed
                    pass
                else:
                    # Single device selected
                    device = Devices.query.filter_by(deviceuuid=form.target_devices.data).first()
                    if device:
                        target_devices = [device]
                
                # Create a schedule for each target device
                for device in target_devices:
                    schedule = SnippetsSchedule(
                        scheduleuuid=str(uuid.uuid4()),
                        snippetuuid=snippet_uuid,
                        deviceuuid=device.deviceuuid,
                        recurrence=recurrence,
                        interval=interval,
                        nextexecution=next_execution,
                        inprogress=False,
                        enabled=True
                    )
                    db.session.add(schedule)

            db.session.commit()
            flash('Snippet created successfully', 'success')

        except Exception as e:
            db.session.rollback()
            log_with_route(logging.ERROR, f"Error creating snippet: {str(e)}")
            flash(f'Error creating snippet: {str(e)}', 'error')

        finally:
            # Clean up
            if os.path.exists(key_file.name):
                os.unlink(key_file.name)

    snippets = Snippets.query.all()
    for snippet in snippets:
        snippet.formatted_date = datetime.fromtimestamp(snippet.created_at).strftime('%Y-%m-%d %H:%M:%S')

    return render_template('administration/admin_snippets.html', form=form, snippets=snippets)

def create_python_wrapper(script_content, metalogos_type):
    return f'''
import os
import json
from logzero import logger

def getAppDirs():
    if platform.system() == 'Windows':
        appDir = 'c:\\\\program files (x86)\\\\Wegweiser\\\\'
    else:
        appDir = '/opt/Wegweiser/'
    logDir = os.path.join(appDir, 'Logs', '')
    configDir = os.path.join(appDir, 'Config', '')
    filesDir = os.path.join(appDir, 'files', '')
    scriptsDir = os.path.join(appDir, 'Scripts', '')
    tempDir = os.path.join(appDir, 'Temp', '')
    return(appDir, logDir, configDir, tempDir, filesDir, scriptsDir)

def getDeviceUuid():
    appDir, logDir, configDir, tempDir, filesDir, scriptsDir = getAppDirs()
    with open(os.path.join(configDir, 'agent.config')) as f:
        agentConfigDict = json.load(f)
    deviceUuid = agentConfigDict['deviceuuid']
    if 'serverAddr' in agentConfigDict:
        host = agentConfigDict['serverAddr']
    else:
        host = 'app.wegweiser.tech'
    return(deviceUuid, host)

try:
    deviceUuid, host = getDeviceUuid()
    
    # Script content
    {script_content}
    
    body = {{
        'deviceuuid': deviceUuid,
        'metalogos_type': '{metalogos_type}',
        'metalogos': data
    }}
    
    url = f'https://{{host}}/ai/device/metadata'
    headers = {{'Content-Type': 'application/json'}}
    response = requests.post(url, headers=headers, data=json.dumps(body))
    print(f"Data collected and sent. Response: {{response.status_code}}")
    
except Exception as e:
    print(f"Error during execution: {{str(e)}}")
'''

def create_powershell_wrapper(script_content, metalogos_type):
    return f'''
import os
import subprocess
import json
import platform
import requests
import tempfile

def getAppDirs():
    if platform.system() == 'Windows':
        appDir = 'c:\\\\program files (x86)\\\\Wegweiser\\\\'
    else:
        appDir = '/opt/Wegweiser/'
    logDir = os.path.join(appDir, 'Logs', '')
    configDir = os.path.join(appDir, 'Config', '')
    filesDir = os.path.join(appDir, 'files', '')
    scriptsDir = os.path.join(appDir, 'Scripts', '')
    tempDir = os.path.join(appDir, 'Temp', '')
    return(appDir, logDir, configDir, tempDir, filesDir, scriptsDir)

def getDeviceUuid():
    appDir, logDir, configDir, tempDir, filesDir, scriptsDir = getAppDirs()
    with open(os.path.join(configDir, 'agent.config')) as f:
        agentConfigDict = json.load(f)
    deviceUuid = agentConfigDict['deviceuuid']
    if 'serverAddr' in agentConfigDict:
        host = agentConfigDict['serverAddr']
    else:
        host = 'app.wegweiser.tech'
    return(deviceUuid, host)

if platform.system() == 'Windows':
    try:
        deviceUuid, host = getDeviceUuid()
        
        ps_script = """
{script_content}
"""
        
        # Save PowerShell script
        ps_file = tempfile.NamedTemporaryFile(delete=False, suffix='.ps1')
        ps_file.write(ps_script.encode())
        ps_file.close()
        
        # Execute PowerShell script
        command = ['powershell.exe', '-ExecutionPolicy', 'Bypass', '-File', ps_file.name]
        result = subprocess.run(command, 
                             stdout=subprocess.PIPE, 
                             stderr=subprocess.PIPE, 
                             universal_newlines=True)
        
        try:
            data = json.loads(result.stdout)
        except json.JSONDecodeError:
            data = {{
                "error": "Failed to parse JSON output",
                "stdout": result.stdout,
                "stderr": result.stderr
            }}
        
        body = {{
            'deviceuuid': deviceUuid,
            'metalogos_type': '{metalogos_type}',
            'metalogos': data
        }}
        
        url = f'https://{{host}}/ai/device/metadata'
        headers = {{'Content-Type': 'application/json'}}
        response = requests.post(url, headers=headers, data=json.dumps(body))
        print(f"Data collected and sent. Response: {{response.status_code}}")
        
    except Exception as e:
        print(f"Error during execution: {{str(e)}}")
        
    finally:
        if os.path.exists(ps_file.name):
            os.unlink(ps_file.name)
else:
    print("Not a Windows system - PowerShell execution skipped")
'''

def sign_script(script_path, key_path, output_dir):
    # Import signing utilities
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.asymmetric import padding
    from cryptography.hazmat.primitives.serialization import load_pem_private_key
    from cryptography.hazmat.backends import default_backend
    import base64

    # Read private key
    with open(key_path, 'rb') as f:
        private_key = load_pem_private_key(f.read(), password=None, backend=default_backend())

    # Read and encode script
    with open(script_path, 'rb') as f:
        script_content = f.read()
        encoded_content = base64.b64encode(script_content)

    # Sign content
    signature = private_key.sign(
        encoded_content,
        padding.PKCS1v15(),
        hashes.SHA256()
    )
    encoded_signature = base64.b64encode(signature).decode()

    # Create snippet JSON
    snippet_uuid = str(uuid.uuid4())
    snippet_json = {
        'settings': {
            'snippetUuid': snippet_uuid,
            'snippetname': os.path.basename(script_path),
            'created_at': int(time.time())
        },
        'payload': {
            'payloadsig': encoded_signature,
            'payloadb64': encoded_content.decode()
        }
    }

    # Save signed snippet
    output_path = os.path.join(output_dir, f'{snippet_uuid}.json')
    with open(output_path, 'w') as f:
        json.dump(snippet_json, f)

    return snippet_uuid

def recStringToSeconds(recString):
    if recString.isdigit():
        if int(recString) == 0:
            recurrence = 0
            interval = 0
    else:
        units = {
            's': 1,
            'm': 60,
            'h': 3600,
            'd': 86400
        }
        try:
            interval = int(''.join(filter(str.isdigit, recString)))
            unit = ''.join(filter(str.isalpha, recString))
        except ValueError:
            raise ValueError(f"Invalid time format: {recString}")
        if unit not in units:
            raise ValueError(f"Unknown time unit: {unit}")
        recurrence = units[unit]
    return recurrence, interval