# Filepath: app/routes/devices/devices_tag_remove.py
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

# Logging setup
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

# Import the blueprint
from . import devices_bp

bcrypt = Bcrypt()


@devices_bp.route('/<uuid:device_uuid>/tags/<uuid:tag_uuid>', methods=['DELETE'])
@login_required
@csrf.exempt
def remove_device_tag(device_uuid, tag_uuid):
    association = TagsXDevices.query.filter_by(
        taguuid=tag_uuid, deviceuuid=device_uuid
    ).first()

    if association:
        db.session.delete(association)
        db.session.commit()
        return jsonify({"message": "Tag removed successfully"})
    else:
        return jsonify({"error": "Tag not found for this device"}), 404