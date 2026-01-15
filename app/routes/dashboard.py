# Filepath: app/routes/dashboard.py
from flask import render_template, session, request, redirect, url_for, flash, jsonify, Blueprint, make_response
from app.utilities.notifications import create_notification
from app.models import db, Devices, Tenants, Accounts, DeviceMetadata, WegcoinTransaction, Groups, Organisations
from sqlalchemy.exc import IntegrityError
from app.utilities.app_access_login_required import login_required
from app.utilities.guided_tour_manager import get_tour_for_page
from sqlalchemy import case
import logging
from app.utilities.app_logging_helper import log_with_route

import time

# Create the Blueprint object
dashboard_bp = Blueprint('dashboard_bp', __name__)

@dashboard_bp.route('/dashboard')
@login_required
def dashboard():
    log_with_route(logging.DEBUG, 'Accessing dashboard route')

    tenant_uuid = session.get('tenant_uuid')
    user_id = session.get('user_id')
    
    if not tenant_uuid:
        log_with_route(logging.WARNING, 'Tenant UUID not found in session. Redirecting to login.')
        flash('Tenant not found. Please log in again.', 'danger')
        return redirect(url_for('login_bp.login'))

    user = Accounts.query.get(user_id)
    if not user:
        log_with_route(logging.WARNING, 'User not found in database. Redirecting to login.')
        flash('User not found. Please log in again.', 'danger')
        return redirect(url_for('login_bp.login'))

    try:
        # Device OS counts
        mac_count = db.session.query(Devices).filter(Devices.hardwareinfo == 'Darwin', Devices.tenantuuid == tenant_uuid).count()
        windows_count = db.session.query(Devices).filter(Devices.hardwareinfo == 'Windows', Devices.tenantuuid == tenant_uuid).count()
        linux_count = db.session.query(Devices).filter(Devices.hardwareinfo == 'Linux', Devices.tenantuuid == tenant_uuid).count()
        other_count = db.session.query(Devices).filter(Devices.tenantuuid == tenant_uuid, ~Devices.hardwareinfo.in_(['Darwin', 'Windows', 'Linux'])).count()

        # Analysis Status Counts
        # Analysis Status Counts
        metadata_stats = db.session.query(
            db.func.count(case((DeviceMetadata.processing_status == 'processed', 1))).label('processed'),
            db.func.count(case((DeviceMetadata.processing_status == 'consolidated', 1))).label('consolidated'),
            db.func.count(case((DeviceMetadata.processing_status == 'failed', 1))).label('failed'),
            db.func.count(case((DeviceMetadata.processing_status == 'pending', 1))).label('pending')
        ).filter(
            DeviceMetadata.deviceuuid.in_(
                db.session.query(Devices.deviceuuid).filter_by(tenantuuid=tenant_uuid)
            )
        ).first()

        # Wegcoin stats
        wegcoin_spent = abs(db.session.query(db.func.sum(WegcoinTransaction.amount))
            .filter(WegcoinTransaction.tenantuuid == tenant_uuid, WegcoinTransaction.amount < 0)
            .scalar() or 0)

        wegcoin_balance = (db.session.query(Tenants.available_wegcoins)
            .filter(Tenants.tenantuuid == tenant_uuid)
            .scalar() or 0)

        # Organization counts
        org_count = db.session.query(Organisations).filter_by(tenantuuid=tenant_uuid).count()
        group_count = db.session.query(Groups).filter_by(tenantuuid=tenant_uuid).count()
        total_devices = mac_count + windows_count + linux_count + other_count

        # Get tour data for dashboard
        tour_data = get_tour_for_page('dashboard', user_id)

        response = make_response(render_template('dashboard/index.html',
            mac_count=mac_count,
            windows_count=windows_count,
            linux_count=linux_count,
            other_count=other_count,
            processed_count=metadata_stats.processed,
            consolidated_count=metadata_stats.consolidated,
            failed_count=metadata_stats.failed,
            pending_count=metadata_stats.pending,
            wegcoin_spent=wegcoin_spent,
            wegcoin_balance=wegcoin_balance,
            org_count=org_count,
            group_count=group_count,
            total_devices=total_devices,
            user=user,
            tour_data=tour_data
        ))
        response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'
        return response

    except IntegrityError as e:
        db.session.rollback()
        log_with_route(logging.ERROR, f"Database error occurred while accessing dashboard: {e}")
        flash('A database error occurred. Please try again later.', 'danger')
        return redirect(url_for('dashboard_bp.dashboard'))