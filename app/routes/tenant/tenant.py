# Filepath: app/routes/tenant/tenant.py
# Filepath: app/routes/ui.py
from flask import Blueprint, session, render_template, request, redirect, url_for, flash, current_app, jsonify, g
from app.utilities.app_access_role_required import role_required
from app.utilities.app_access_login_required import login_required
from app.forms.tenant_profile import TenantProfileForm
from werkzeug.utils import secure_filename
from app.utilities.notifications import create_notification
from app.forms.chat_form import ChatForm
# Removed unused imports - now using task system
from markupsafe import Markup
from flask import render_template_string
from app.models import TenantMetadata
from datetime import datetime, timedelta



# Utilities for device management
from app.utilities.ui_devices_printers import fetch_printers_by_device
from app.utilities.ui_devices_eventlogs import fetch_event_logs_by_device
from app.utilities.ui_devices_devicetable import get_devices_table_data
from app.utilities.ui_devices_devicedetails import get_device_details

# Utilities for wegcoin balance and AI task statuses
from app.utilities.ui_wegcoins_currencystate import get_tenant_wegcoin_balance

# Logging
from app.utilities.app_logging_helper import log_with_route
import logging

# Models and database
from app.models import db, Accounts, Tenants, Organisations, Devices, Groups, Roles, UserXOrganisation, DeviceMetadata, HealthScoreHistory
from flask_mail import Message
from app import mail, master_permission, admin_or_master_permission

# SQLAlchemy imports
from sqlalchemy import text, desc
from sqlalchemy.exc import SQLAlchemyError, IntegrityError

# Utilities
from datetime import datetime, timezone
from uuid import UUID
from flask_bcrypt import Bcrypt
from markupsafe import Markup
bcrypt = Bcrypt()

# Misc
import json
import time
import os
import secrets
import string
import uuid
from dotenv import load_dotenv
from collections import defaultdict

from app.utilities.guided_tour_manager import get_tour_for_page

# Import CSV import blueprint
from app.routes.tenant.csv_import import csv_import_bp


# Load environment variables
load_dotenv()

# Set the logging flag based on the environment variable
LOG_DEVICES_TABLE = os.getenv('LOG_DEVICES_TABLE', 'False').lower() == 'true'


tenant_bp = Blueprint('tenant', __name__)

# Register the CSV import blueprint
tenant_bp.register_blueprint(csv_import_bp)

################## Endpoints ##################

@tenant_bp.route('/tenant/overview')
@login_required
def get_tenants_overview():
    current_user = Accounts.query.get(session.get('user_id'))
    tenant_uuid = session.get('tenant_uuid')

    if not tenant_uuid:
        log_with_route(logging.ERROR, "No tenant associated with the current user", route='/tenant/overview')
        flash("No tenant associated with the current user", "error")
        return redirect(url_for('login_bp.login'))

    tenant = Tenants.query.get(tenant_uuid)
    if not tenant:
        log_with_route(logging.ERROR, "Tenant not found", route='/tenant/overview')
        flash("Tenant not found", "error")
        return redirect(url_for('login_bp.login'))

    try:
        tenant_overview = tenant.get_overview()
        if not tenant_overview:
            log_with_route(logging.ERROR, "Overview data missing", route='/tenant/overview')
            flash("Overview data missing", "error")
            return redirect(url_for('dashboard_bp.dashboard'))

        # Fetch Wegcoin balance and total spent
        wegcoin_data = get_tenant_wegcoin_balance(tenant_uuid)
        tenant_overview['wegcoin_count'] = wegcoin_data['wegcoin_count']
        tenant_overview['total_wegcoins_spent'] = wegcoin_data['total_wegcoins_spent']

        # Fetch pending and processed counts
        utility_status = get_pending_and_processed_counts(tenant_uuid)
        tenant_overview['pending_count'] = utility_status.get('pending_count', 0)
        tenant_overview['processed_count'] = utility_status.get('processed_count', 0)

        # Add the recurring_analyses_enabled value from the tenant object
        tenant_overview['recurring_analyses_enabled'] = tenant.recurring_analyses_enabled

        # Filter organizations based on user's role and permissions
        if current_user.role.rolename in ['admin', 'master']:
            authorized_orgs = tenant_overview['org_details']
        else:
            user_org_ids = [str(uo.orguuid) for uo in current_user.organisations]
            authorized_orgs = [org for org in tenant_overview['org_details'] if org['orguuid'] in user_org_ids]

        tenant_overview['org_details'] = authorized_orgs

        # Filter users based on role
        if current_user.role.rolename in ['admin', 'master']:
            tenant_users = Accounts.query.filter_by(tenantuuid=tenant_uuid).all()
        else:
            tenant_users = [current_user]

        # Fetch AI recommendations from processed analyses or create pending task
        ai_recommendations = get_or_create_tenant_analysis(
            tenant_uuid, 'tenant-ai-recommendations', tenant
        )

        # Guided tour data for Tenant Overview (use dummy when none exists)
        tour_data = get_tour_for_page('tenant-overview', session.get('user_id')) or {
            'is_active': True,
            'page_identifier': 'tenant-overview',
            'tour_name': 'Quick Tour',
            'tour_config': {},
            'steps': [{'id': 'welcome', 'title': 'Welcome', 'text': 'This is a placeholder tour.'}],
            'user_progress': {'completed_steps': [], 'is_completed': False}
        }

        return render_template(
            'tenant/index.html',
            tenant_overview=tenant_overview,
            tenant_users=tenant_users,
            current_user=current_user,
            ai_recommendations=ai_recommendations,
            tour_data=tour_data
        )

    except Exception as e:
        log_with_route(logging.ERROR, f"Error fetching tenant overview: {str(e)}", route='tenant/overview', exc_info=True)
        flash("An error occurred while fetching tenant overview", "error")
        return redirect(url_for('dashboard_bp.dashboard'))


@tenant_bp.route('/tenant/toggle_recurring_analyses/<tenant_id>', methods=['POST'])
@login_required
def toggle_recurring_analyses(tenant_id):
    tenant = Tenants.query.get(tenant_id)
    if not tenant:
        flash('Tenant not found', 'error')
        return jsonify({'success': False, 'error': 'Tenant not found'}), 404

    # Toggle the recurring analyses based on the incoming AJAX data
    data = request.get_json()
    tenant.recurring_analyses_enabled = data.get('enabled', False)

    try:
        db.session.commit()
        if tenant.recurring_analyses_enabled:
            flash('Recurring analyses enabled', 'success')
        else:
            flash('Recurring analyses disabled', 'success')
        return jsonify({'success': True, 'recurring_analyses_enabled': tenant.recurring_analyses_enabled})
    except Exception as e:
        db.session.rollback()
        flash('Error updating recurring analyses status', 'error')
        return jsonify({'success': False, 'error': 'An error occurred while updating the status'}), 500



@tenant_bp.route('/tenant/update', methods=['POST'])
@login_required
def update_tenant():
    tenant_uuid = session.get('tenant_uuid')
    if not tenant_uuid:
        log_with_route(logging.ERROR, "Unauthorized access attempt")
        flash('Unauthorized access', 'danger')
        return redirect(url_for('ui.get_tenants_overview'))

    tenant = db.session.query(Tenants).filter_by(tenantuuid=tenant_uuid).first()
    if not tenant:
        log_with_route(logging.ERROR, "Tenant not found during update")
        flash('Tenant not found', 'danger')
        return redirect(url_for('ui.get_tenants_overview'))

    tenant.address = request.form.get('address')
    tenant.email = request.form.get('email')
    tenant.phone = request.form.get('phone')

    # Handling file upload for logo
    logo = request.files.get('logo')
    if logo:
        logo_filename = f"{tenant.tenantuuid}.png"
        logo_path = os.path.join('static/images/tenants', tenant.tenantuuid, logo_filename)
        os.makedirs(os.path.dirname(logo_path), exist_ok=True)
        logo.save(os.path.join(current_app.root_path, logo_path))
        tenant.logo_path = logo_path

    db.session.commit()
    log_with_route(logging.INFO, f"Tenant {tenant_uuid} updated successfully")
    flash('Tenant information updated successfully', 'success')
    return redirect(url_for('ui.get_tenants_overview'))


@tenant_bp.route('/tenant/profile', methods=['GET', 'POST'])
@login_required
@role_required(['admin', 'master'])
def tenant_profile():
    tenant_uuid = session.get('tenant_uuid')
    tenant = Tenants.query.get(tenant_uuid)

    if not tenant:
        log_with_route(logging.ERROR, f"Tenant not found for UUID: {tenant_uuid}")
        flash('Tenant not found', 'error')
        return redirect(url_for('dashboard_bp.dashboard'))

    form = TenantProfileForm(obj=tenant)

    # Guided tour data for Tenant Profile (use dummy when none exists)
    tour_data = get_tour_for_page('tenant-profile', session.get('user_id')) or {
        'is_active': True,
        'page_identifier': 'tenant-profile',
        'tour_name': 'Quick Tour',
        'tour_config': {},
        'steps': [{'id': 'welcome', 'title': 'Welcome', 'text': 'This is a placeholder tour.'}],
        'user_progress': {'completed_steps': [], 'is_completed': False}
    }

    if request.method == 'GET':
        form.company_size.data = tenant.company_size
        form.primary_focus.data = tenant.primary_focus
        form.rmm_type.data = tenant.rmm_type
        form.service_areas.data = tenant.service_areas or []
        form.specializations.data = tenant.specializations or []
        form.customer_industries.data = tenant.customer_industries or []
        form.monitoring_preferences.data = tenant.monitoring_preferences or []
        form.software_bundles.data = tenant.get_profile_data('software_bundles', 'none')
        form.remote_support.data = tenant.get_profile_data('remote_support', 'none')
        form.psa_service_desk.data = tenant.get_profile_data('psa_service_desk', 'none')
        form.bdr.data = tenant.get_profile_data('bdr', 'none')
        form.dns_filtering.data = tenant.get_profile_data('dns_filtering', 'none')
        form.email_security.data = tenant.get_profile_data('email_security', 'none')
        form.endpoint_protection.data = tenant.get_profile_data('endpoint_protection', 'none')
        form.security_suites.data = tenant.get_profile_data('security_suites', 'none')
        form.it_documentation.data = tenant.get_profile_data('it_documentation', 'none')
        form.network_monitoring.data = tenant.get_profile_data('network_monitoring', 'none')
        form.communication_collaboration.data = tenant.get_profile_data('communication_collaboration', 'none')
        form.training_certification.data = tenant.get_profile_data('training_certification', 'none')
        form.asset_management.data = tenant.get_profile_data('asset_management', 'none')
        form.password_management.data = tenant.get_profile_data('password_management', 'none')
        form.voip_telephony.data = tenant.get_profile_data('voip_telephony', 'none')
        form.patch_management.data = tenant.get_profile_data('patch_management', 'none')
        form.iam.data = tenant.get_profile_data('iam', 'none')
        form.managed_print_services.data = tenant.get_profile_data('managed_print_services', 'none')
        form.vdi.data = tenant.get_profile_data('vdi', 'none')
        form.business_resources.data = tenant.get_profile_data('business_resources', 'none')
        form.cloud_management.data = tenant.get_profile_data('cloud_management', 'none')
        form.mdm.data = tenant.get_profile_data('mdm', 'none')
        form.communities_forums.data = tenant.get_profile_data('communities_forums', 'none')

        if tenant.sla_details:
            form.sla_response_time.data = tenant.sla_details.get('response_time')
            form.sla_uptime_guarantee.data = tenant.sla_details.get('uptime_guarantee')
        form.preferred_communication_style.data = tenant.preferred_communication_style

    if form.validate_on_submit():
        log_with_route(logging.INFO, "Form validated successfully")

        log_with_route(logging.DEBUG, f"Form data: {form.data}")

        # Update fields that have dedicated columns
        tenant.tenantname = form.tenantname.data
        tenant.email = form.email.data
        tenant.phone = form.phone.data
        tenant.address = form.address.data
        tenant.company_size = form.company_size.data
        tenant.primary_focus = form.primary_focus.data
        tenant.rmm_type = form.rmm_type.data
        tenant.preferred_communication_style = form.preferred_communication_style.data

        # Handle logo upload
        if form.logo.data:
            filename = secure_filename(form.logo.data.filename)
            logo_path = os.path.join(current_app.config['TENANT_LOGO_FOLDER'], str(tenant_uuid))
            try:
                os.makedirs(logo_path, exist_ok=True)
                file_path = os.path.join(logo_path, filename)
                form.logo.data.save(file_path)
                tenant.logo_path = os.path.relpath(file_path, current_app.root_path)
                log_with_route(logging.INFO, f"Logo saved to: {file_path}")
            except Exception as e:
                log_with_route(logging.ERROR, f"Error saving logo: {str(e)}", exc_info=True)
                flash('An error occurred while saving the logo', 'error')

        # Update JSON fields
        tenant.service_areas = form.service_areas.data
        tenant.specializations = form.specializations.data
        tenant.customer_industries = form.customer_industries.data
        tenant.monitoring_preferences = form.monitoring_preferences.data

        tenant.sla_details = {
            'response_time': form.sla_response_time.data,
            'uptime_guarantee': form.sla_uptime_guarantee.data
        }

        # Update profile_data for additional fields
        profile_data = {
            'software_bundles': form.software_bundles.data,
            'remote_support': form.remote_support.data,
            'psa_service_desk': form.psa_service_desk.data,
            'bdr': form.bdr.data,
            'dns_filtering': form.dns_filtering.data,
            'email_security': form.email_security.data,
            'endpoint_protection': form.endpoint_protection.data,
            'security_suites': form.security_suites.data,
            'it_documentation': form.it_documentation.data,
            'network_monitoring': form.network_monitoring.data,
            'communication_collaboration': form.communication_collaboration.data,
            'training_certification': form.training_certification.data,
            'asset_management': form.asset_management.data,
            'password_management': form.password_management.data,
            'voip_telephony': form.voip_telephony.data,
            'patch_management': form.patch_management.data,
            'iam': form.iam.data,
            'managed_print_services': form.managed_print_services.data,
            'vdi': form.vdi.data,
            'business_resources': form.business_resources.data,
            'cloud_management': form.cloud_management.data,
            'mdm': form.mdm.data,
            'communities_forums': form.communities_forums.data
        }

        log_with_route(logging.DEBUG, f"Profile data before assignment: {profile_data}")

        tenant.profile_data = profile_data

        log_with_route(logging.DEBUG, f"Profile data before save: {tenant.profile_data}")

        try:
            db.session.commit()
            log_with_route(logging.DEBUG, f"Profile data after save: {tenant.profile_data}")
            log_with_route(logging.INFO, f"Tenant profile updated successfully for UUID: {tenant_uuid}")
            flash('Tenant profile updated successfully', 'success')
        except Exception as e:
            db.session.rollback()
            log_with_route(logging.ERROR, f"Error updating tenant profile: {str(e)}", exc_info=True)
            flash('An error occurred while updating the profile', 'error')

    return render_template('tenant/tenantprofile.html', form=form, tenant=tenant, tour_data=tour_data)

@tenant_bp.route('/tenant/<uuid:tenant_uuid>/health_history')
@login_required
def get_tenant_health_history(tenant_uuid):
    try:
        tenant_info = get_tenant_info(tenant_uuid)
        history = HealthScoreHistory.query.filter_by(entity_type='tenant', entity_uuid=tenant_uuid).order_by(HealthScoreHistory.timestamp).all()

        data = aggregate_by_day(history)
        data.append({'x': datetime.utcnow().date().isoformat(), 'y': tenant_info['health_score']})

        return jsonify(data)
    except ValueError as e:
        return jsonify({'error': str(e)}), 404
    except Exception as e:
        log_with_route(logging.ERROR, f"Error in get_tenant_health_history: {str(e)}", exc_info=True)
        return jsonify({'error': 'An unexpected error occurred'}), 500

@tenant_bp.route('/tenant/<uuid:tenant_uuid>/cascading_health_history')
@login_required
def get_cascading_health_history(tenant_uuid):
    try:
        tenant_info = get_tenant_info(tenant_uuid)

        # Add logging for query execution
        log_with_route(logging.INFO, f"Fetching health history for tenant {tenant_uuid}")

        tenant_history = HealthScoreHistory.query.filter_by(entity_type='tenant', entity_uuid=tenant_uuid).order_by(HealthScoreHistory.timestamp).all()
        org_history = HealthScoreHistory.query.filter_by(entity_type='organisation').join(Organisations, HealthScoreHistory.entity_uuid == Organisations.orguuid).filter(Organisations.tenantuuid == tenant_uuid).order_by(HealthScoreHistory.timestamp).all()
        group_history = HealthScoreHistory.query.filter_by(entity_type='group').join(Groups, HealthScoreHistory.entity_uuid == Groups.groupuuid).filter(Groups.tenantuuid == tenant_uuid).order_by(HealthScoreHistory.timestamp).all()

        # Log counts to identify empty datasets
        log_with_route(logging.INFO, f"Health history counts - Tenant: {len(tenant_history)}, Org: {len(org_history)}, Group: {len(group_history)}")

        # Always ensure we have at least the current health score point for tenant
        tenant_data = aggregate_by_day(tenant_history)
        current_time = datetime.utcnow().date().isoformat()
        tenant_data.append({'x': current_time, 'y': tenant_info['health_score']})

        # If no org or group history, provide at least one data point with current time
        org_data = aggregate_by_day(org_history)
        if not org_data:
            # Calculate average org health score or use tenant score as fallback
            orgs = Organisations.query.filter_by(tenantuuid=tenant_uuid).all()
            if orgs:
                avg_org_score = sum(org.health_score or 75 for org in orgs) / len(orgs)
                org_data.append({'x': current_time, 'y': avg_org_score})
            else:
                org_data.append({'x': current_time, 'y': tenant_info['health_score']})

        group_data = aggregate_by_day(group_history)
        if not group_data:
            # Calculate average group health score or use tenant score as fallback
            groups = Groups.query.filter_by(tenantuuid=tenant_uuid).all()
            if groups:
                avg_group_score = sum(group.health_score or 75 for group in groups) / len(groups)
                group_data.append({'x': current_time, 'y': avg_group_score})
            else:
                group_data.append({'x': current_time, 'y': tenant_info['health_score']})

        result = {
            'tenant': tenant_data,
            'organisation': org_data,
            'group': group_data
        }

        # Log the structure of the response (not all data to avoid flooding logs)
        log_with_route(logging.INFO, f"Returning health history data with lengths - Tenant: {len(tenant_data)}, Org: {len(org_data)}, Group: {len(group_data)}")

        return jsonify(result)
    except ValueError as e:
        log_with_route(logging.ERROR, f"ValueError in get_cascading_health_history: {str(e)}")
        return jsonify({'error': str(e)}), 404
    except Exception as e:
        log_with_route(logging.ERROR, f"Error in get_cascading_health_history: {str(e)}", exc_info=True)
        return jsonify({'error': 'An unexpected error occurred'}), 500


@tenant_bp.route('/tenant/<uuid:tenant_uuid>/group_health_history')
@login_required
def get_group_health_history(tenant_uuid):
    try:
        history = HealthScoreHistory.query.filter_by(entity_type='group').join(
            Groups, HealthScoreHistory.entity_uuid == Groups.groupuuid
        ).filter(Groups.tenantuuid == tenant_uuid).order_by(HealthScoreHistory.timestamp).all()
        data = aggregate_by_day(history)
        return jsonify(data)
    except Exception as e:
        log_with_route(logging.ERROR, f"Error in get_group_health_history: {str(e)}", exc_info=True)
        return jsonify({'error': 'An unexpected error occurred'}), 500

@tenant_bp.route('/tenant/<uuid:tenant_uuid>/org_health_history')
@login_required
def get_org_health_history(tenant_uuid):
    try:
        history = HealthScoreHistory.query.filter_by(entity_type='organisation').join(
            Organisations, HealthScoreHistory.entity_uuid == Organisations.orguuid
        ).filter(Organisations.tenantuuid == tenant_uuid).order_by(HealthScoreHistory.timestamp).all()
        data = aggregate_by_day(history)
        return jsonify(data)
    except Exception as e:
        log_with_route(logging.ERROR, f"Error in get_org_health_history: {str(e)}", exc_info=True)
        return jsonify({'error': 'An unexpected error occurred'}), 500

@tenant_bp.route('/tenant/<uuid:tenant_uuid>/device_health_history')
@login_required
def get_device_health_history(tenant_uuid):
    try:
        history = HealthScoreHistory.query.filter_by(entity_type='device').join(
            Devices, HealthScoreHistory.entity_uuid == Devices.deviceuuid
        ).filter(Devices.tenantuuid == tenant_uuid).order_by(HealthScoreHistory.timestamp).all()
        data = aggregate_by_day(history)
        return jsonify(data)
    except Exception as e:
        log_with_route(logging.ERROR, f"Error in get_device_health_history: {str(e)}", exc_info=True)
        return jsonify({'error': 'An unexpected error occurred'}), 500


def check_metadata_freshness(created_at, hours=24):
    """Check if metadata is fresh enough (less than `hours` old)."""
    return (int(time.time()) - created_at) < (hours * 3600)

@tenant_bp.route('/tenant/ai_recommendations')
@login_required
def get_ai_recommendations():
    tenant_uuid = session.get('tenant_uuid')
    try:
        tenant = Tenants.query.get(tenant_uuid)
        if not tenant:
            return jsonify({"success": False, "error": "Tenant not found"})

        # Get recommendations using task system
        recommendations = get_or_create_tenant_analysis(
            tenant_uuid, 'tenant-ai-recommendations', tenant
        )

        if not recommendations:
            return jsonify({
                "success": False,
                "error": "AI recommendations are disabled for this tenant."
            })

        # Check if it's a placeholder message (analysis pending)
        if "being processed" in recommendations:
            return jsonify({
                "success": True,
                "recommendations": f"<p>{recommendations}</p>",
                "pending": True
            })

        # Render the recommendations as HTML
        rendered_recommendations = render_template_string(
            "{{ content | markdown | safe }}",
            content=recommendations
        )

        return jsonify({"success": True, "recommendations": rendered_recommendations})
    except Exception as e:
        log_with_route(logging.ERROR, f"Failed to get AI recommendations: {str(e)}")
        return jsonify({
            "success": False,
            "error": "Unable to load recommendations at this time."
        })


@tenant_bp.route('/tenant/ai_suggestions')
@login_required
def get_ai_suggestions():
    tenant_uuid = session.get('tenant_uuid')
    try:
        tenant = Tenants.query.get(tenant_uuid)
        if not tenant:
            return jsonify({"success": False, "error": "Tenant not found"})

        # Get suggestions using task system
        suggestions = get_or_create_tenant_analysis(
            tenant_uuid, 'tenant-ai-suggestions', tenant
        )

        if not suggestions:
            return jsonify({
                "success": False,
                "error": "AI strategic analysis is disabled for this tenant."
            })

        # Check if it's a placeholder message (analysis pending)
        if "being processed" in suggestions:
            return jsonify({
                "success": True,
                "suggestions": f"<p>{suggestions}</p>",
                "pending": True
            })

        # Render the suggestions as HTML
        rendered_content = render_template_string(
            "{{ content | markdown | safe }}",
            content=suggestions
        )
        return jsonify({"success": True, "suggestions": rendered_content})

    except Exception as e:
        log_with_route(logging.ERROR, f"Failed to get AI suggestions: {str(e)}")
        return jsonify({
            "success": False,
            "error": "Unable to load suggestions at this time."
        })





################## New helper functions for tenant overview ##################



def get_tenant_info(tenant_uuid):
    tenant = db.session.query(Tenants).filter_by(tenantuuid=tenant_uuid).first()
    if not tenant:
        raise ValueError("Tenant not found")
    return {
        'tenantname': tenant.tenantname,
        'tenantuuid': tenant.tenantuuid,
        'health_score': tenant.health_score  # Include health_score
    }


def get_org_info(tenant_uuid):
    orgs = db.session.query(Organisations).filter_by(tenantuuid=tenant_uuid).all()
    return {
        'org_count': len(orgs),
        'orgs': [{'orgname': org.orgname, 'orguuid': org.orguuid} for org in orgs]
    }

def get_group_info(tenant_uuid):
    groups = db.session.query(Groups).filter_by(tenantuuid=tenant_uuid).all()
    return {
        'group_count': len(groups),
        'groups': [{'groupname': group.groupname, 'groupuuid': group.groupuuid} for group in groups]
    }

def get_device_info(tenant_uuid):
    devices = db.session.query(Devices).filter_by(tenantuuid=tenant_uuid).all()
    return {
        'device_count': len(devices),
        'devices': [{'devicename': device.devicename, 'deviceuuid': device.deviceuuid} for device in devices]
    }

def aggregate_by_day(history):
    daily = defaultdict(list)
    for h in history:
        day = h.timestamp.date().isoformat()
        daily[day].append(h.health_score)
    return [
        {"x": day, "y": sum(scores) / len(scores)}
        for day, scores in sorted(daily.items())
    ]


def get_pending_and_processed_counts(tenant_uuid):
    """Get pending and processed analysis counts for a tenant from devicemetadata"""
    try:
        from sqlalchemy import text

        # Get pending count from devicemetadata for all devices in this tenant
        pending_count = db.session.execute(text("""
            SELECT COUNT(*) as count
            FROM devicemetadata dm
            JOIN devices d ON dm.deviceuuid = d.deviceuuid
            WHERE d.tenantuuid = :tenant_uuid
            AND dm.processing_status = 'pending'
        """), {'tenant_uuid': tenant_uuid}).scalar() or 0

        # Get processed count from devicemetadata for all devices in this tenant
        processed_count = db.session.execute(text("""
            SELECT COUNT(*) as count
            FROM devicemetadata dm
            JOIN devices d ON dm.deviceuuid = d.deviceuuid
            WHERE d.tenantuuid = :tenant_uuid
            AND dm.processing_status = 'processed'
        """), {'tenant_uuid': tenant_uuid}).scalar() or 0

        return {
            'pending_count': pending_count,
            'processed_count': processed_count
        }

    except Exception as e:
        log_with_route(logging.ERROR, f"Error getting pending and processed counts: {str(e)}", exc_info=True)
        return {'pending_count': 0, 'processed_count': 0}


def get_or_create_tenant_analysis(tenant_uuid, analysis_type, tenant):
    """Get existing processed analysis or create pending task if needed"""
    try:
        # Check if analysis is enabled for this tenant
        if not tenant.is_analysis_enabled(analysis_type):
            return None

        # Look for existing processed analysis
        existing_analysis = TenantMetadata.query.filter_by(
            tenantuuid=tenant_uuid,
            metalogos_type=analysis_type,
            processing_status='processed'
        ).order_by(TenantMetadata.analyzed_at.desc()).first()

        if existing_analysis and existing_analysis.ai_analysis:
            return existing_analysis.ai_analysis

        # Check if there's already a pending analysis
        pending_analysis = TenantMetadata.query.filter_by(
            tenantuuid=tenant_uuid,
            metalogos_type=analysis_type,
            processing_status='pending'
        ).first()

        if not pending_analysis:
            # Create new pending analysis
            new_metadata = TenantMetadata(
                tenantuuid=tenant_uuid,
                metalogos_type=analysis_type,
                metalogos={},
                processing_status='pending'
            )
            db.session.add(new_metadata)
            db.session.commit()
            log_with_route(logging.INFO, f"Created pending {analysis_type} task for tenant {tenant.tenantname}")

        # Return placeholder text for pending analysis
        return "Analysis is being processed. Please check back in a few minutes."

    except Exception as e:
        log_with_route(logging.ERROR, f"Error in get_or_create_tenant_analysis: {str(e)}")
        return "Unable to load analysis at this time."



