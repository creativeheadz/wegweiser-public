# Filepath: app/routes/devices/devices_register.py
# Filepath: app/routes/tenant/devices.py
# Flask core imports
from flask import (
    Blueprint, session, render_template, request, redirect, url_for, flash,
    current_app, jsonify, g, render_template_string
)
from flask_mail import Message
from flask_bcrypt import Bcrypt
from flask_wtf.csrf import CSRFProtect

# SQLAlchemy imports
from sqlalchemy import text, desc
from sqlalchemy.exc import SQLAlchemyError, IntegrityError
from sqlalchemy.orm import joinedload, aliased

# Standard library imports
import logging
import json
import os
import time
import uuid
from uuid import UUID
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv
from markupsafe import Markup
from werkzeug.utils import secure_filename
import secrets
import string
from .devices import *

# Models and database
from app.models import (
    db, Devices, Organisations, Groups, DeviceMetadata, HealthScoreHistory,
    Accounts, Tenants, Roles, UserXOrganisation, TenantMetadata, Tags,
    TagsXDevices, Snippets, DeviceBattery, DeviceDrives, DeviceMemory,
    DeviceNetworks, DeviceStatus, Messages
)

# Utilities
from app import csrf, mail, master_permission, admin_or_master_permission
from app.utilities.app_access_login_required import login_required
from app.utilities.app_access_role_required import role_required
from app.utilities.notifications import create_notification
from app.utilities.ui_devices_delete_device import delete_devices
from app.utilities.app_logging_helper import log_with_route
from app.utilities.ui_devices_printers import fetch_printers_by_device
from app.utilities.ui_devices_eventlogs import fetch_event_logs_by_device
from app.utilities.ui_devices_devicetable import get_devices_table_data
from app.utilities.ui_devices_devicedetails import get_device_details

from app.utilities.langchain_utils import generate_entity_suggestions, generate_tool_recommendations
from app.utilities.ui_wegcoins_currencystate import get_tenant_wegcoin_balance
from app.routes.ai.ai import get_or_create_conversation


# Forms
from app.forms.tenant_profile import TenantProfileForm
from app.forms.chat_form import ChatForm

# Load environment variables
load_dotenv()

# Logging setup - using centralized logging helper

# Import the blueprint
from . import devices_bp



bcrypt = Bcrypt()



@devices_bp.route('/register', methods=['POST'])
@csrf.exempt
def register_device():
	data = request.get_json()
	groupuuid = data['groupuuid']

	log_with_route(logging.INFO, f"Request to register a new device ({data['devicename']}) in group {groupuuid}...")

	if not groupuuid:
		log_with_route(logging.ERROR, f'No groupuuid specified. Quitting.')
		return jsonify({'error': 'groupuuid is required'}), 400

	try:
		group = Groups.query.filter_by(groupuuid=groupuuid).first()
		if not group:
			log_with_route(logging.ERROR, f'groupuuid {groupuuid} not found in database. Quitting.')
			return jsonify({'error': 'Group does not exist'}), 400
		log_with_route(logging.DEBUG, f'agentpubpem: {data.get("agentpubpem")}')
		device_uuid = str(uuid.uuid4())
		new_device = Devices(
			deviceuuid=device_uuid,
			devicename=data['devicename'],
			hardwareinfo=data.get('hardwareinfo'),
			agent_public_key=data.get('agentpubpem'),
			groupuuid=groupuuid,
			orguuid=group.orguuid,
			tenantuuid=group.tenantuuid,
			created_at=int(time.time())  # Store current time in Unix format
		)
		db.session.add(new_device)

		# Use a hardcoded UUID for system messages
		system_useruuid = '00000000-0000-0000-0000-000000000000'  # Hardcoded UUID

		# Retrieve or create a conversation for the device
		conversation = get_or_create_conversation('device', device_uuid)

		# Create a message for the new device registration
		message = Messages(
			messageuuid=str(uuid.uuid4()),  # Generating a UUID for the message
			conversationuuid=conversation.conversationuuid,  # Assign the conversationuuid
			useruuid=system_useruuid,  # Use the hardcoded UUID
			tenantuuid=group.tenantuuid,
			entityuuid=device_uuid,  # device_uuid is now the entityuuid
			entity_type='device',  # Hardcoded to 'device'
			title="New Device Registered",
			content=f"A new device '{data['devicename']}' has checked into your group '{group.groupname}'",
			is_read=False,
			created_at=int(time.time()),  # Store current time in Unix format
			message_type='chat'
		)
		db.session.add(message)
		db.session.commit()

		log_with_route(logging.INFO, f"Successfully registered new device: device_uuid: {device_uuid} | devicename: {data['devicename']} \
| tenant: {group.tenantuuid} | org: {group.orguuid}  | group: {groupuuid}")

		log_with_route(logging.INFO, f'Attempting to schedule default snippets for {device_uuid}')
		scheduleDefaultSnippets(device_uuid, data.get('hardwareinfo'))
		log_with_route(logging.INFO, f'Successfully scheduled default snippets for {device_uuid}')

		return jsonify({'success': 'device registered', 'deviceuuid': device_uuid}), 201
	except IntegrityError as e:
		log_with_route(logging.ERROR, f'IntegrityError creating new device. Rolling back... Error: {e}')
		db.session.rollback()
		log_with_route(logging.INFO, 'Rollback complete.')
		return jsonify({'error': 'Integrity error: ' + str(e)}), 400
	except Exception as e:
		log_with_route(logging.ERROR, f'Failed to register new device. Reason: {e}. Rolling back...')
		db.session.rollback()
		log_with_route(logging.INFO, 'Rollback complete.')
		return jsonify({'error': str(e)}), 500