# Filepath: app/routes/settings/settings.py
from flask import render_template, redirect, url_for, session, request, jsonify
import logging
from app.models import db, MFA, Accounts, Tenants, Organisations, Groups
from app.models.tenants import get_default_analysis_toggles
from app.utilities.app_logging_helper import log_with_route
from app.utilities.app_access_login_required import login_required
from app.tasks.base.definitions import AnalysisDefinitions
from . import settings_bp
from app.utilities.guided_tour_manager import get_tour_for_page


@settings_bp.route('/')
@login_required
def settings_index():
    if 'user_id' not in session or 'tenant_uuid' not in session:
        return redirect(url_for('login_bp.login'))

    tenant_uuid = session.get('tenant_uuid')
    tenant = Tenants.query.get(tenant_uuid)

    if not tenant:
        log_with_route(logging.ERROR, f"No tenant found for UUID: {tenant_uuid}")
        return "Tenant not found", 400

    if tenant.analysis_toggles is None:
        tenant.analysis_toggles = get_default_analysis_toggles()
        db.session.commit()

    # Get all analysis configurations
    configs = AnalysisDefinitions.get_all_configs()
    analysis_groups = tenant.get_analysis_groups()
    global_enabled = tenant.recurring_analyses_enabled

    # Add descriptions and costs to each analysis in the groups
    for group_name, analyses in analysis_groups.items():
        for analysis in analyses:
            config = configs.get(analysis['type'], {})
            analysis['description'] = config.get('description', 'No description available')
            analysis['cost'] = config.get('cost', 1)  # Default to 1 Wegcoin if not specified

    # Guided tour data for Settings page (use dummy when none exists)
    tour_data = get_tour_for_page('settings', session.get('user_id')) or {
        'is_active': True,
        'page_identifier': 'settings',
        'tour_name': 'Quick Tour',
        'tour_config': {},
        'steps': [{'id': 'welcome', 'title': 'Welcome', 'text': 'This is a placeholder tour.'}],
        'user_progress': {'completed_steps': [], 'is_completed': False}
    }

    return render_template('settings/index.html',
                         analysis_groups=analysis_groups,
                         global_enabled=global_enabled,
                         tour_data=tour_data)


@settings_bp.route('/toggle_analysis', methods=['POST'])
@login_required
def toggle_analysis():
    log_with_route(logging.INFO, f"Toggle request received - Form data: {request.form}")

    if 'tenant_uuid' not in session:
        return jsonify({'success': False, 'error': 'No tenant association'}), 400

    tenant = Tenants.query.get(session.get('tenant_uuid'))
    if not tenant:
        return jsonify({'success': False, 'error': 'Tenant not found'}), 404

    analysis_type = request.form.get('analysis_type')
    enabled = request.form.get('enabled') == 'true'

    log_with_route(logging.INFO, f"Before update - Toggles: {tenant.analysis_toggles}")

    try:
        if analysis_type == 'global':
            if enabled:
                tenant.enable_all_analyses()
            else:
                tenant.disable_all_analyses()
        else:
            tenant.set_analysis_enabled(analysis_type, enabled)

        db.session.commit()

        # Query the tenant again to ensure we get the updated state
        db.session.refresh(tenant)
        log_with_route(logging.INFO, f"After update - Toggles: {tenant.analysis_toggles}")

        return jsonify({
            'success': True,
            'analysis_type': analysis_type,
            'enabled': enabled,
            'global_enabled': tenant.recurring_analyses_enabled,
            'toggles': tenant.analysis_toggles
        })

    except Exception as e:
        db.session.rollback()
        log_with_route(logging.ERROR, f"Toggle failed: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e),
            'analysis_type': analysis_type
        }), 500


@settings_bp.route('/exclusions')
@login_required
def exclusions_index():
    """Analysis exclusions configuration page"""
    if 'user_id' not in session or 'tenant_uuid' not in session:
        return redirect(url_for('login_bp.login'))

    tenant_uuid = session.get('tenant_uuid')
    tenant = Tenants.query.get(tenant_uuid)

    if not tenant:
        log_with_route(logging.ERROR, f"No tenant found for UUID: {tenant_uuid}")
        return "Tenant not found", 400

    # Get analysis groups for the dropdown
    configs = AnalysisDefinitions.get_all_configs()
    analysis_groups = tenant.get_analysis_groups()

    # Add descriptions to each analysis in the groups
    for group_name, analyses in analysis_groups.items():
        for analysis in analyses:
            config = configs.get(analysis['type'], {})
            analysis['description'] = config.get('description', 'No description available')

    # Get organisations for the tenant
    organisations = Organisations.query.filter_by(tenantuuid=tenant_uuid).order_by(Organisations.orgname).all()

    # Get groups for the tenant with org names
    groups = db.session.query(
        Groups.groupuuid,
        Groups.groupname,
        Organisations.orgname.label('org_name')
    ).join(
        Organisations, Groups.orguuid == Organisations.orguuid
    ).filter(
        Groups.tenantuuid == tenant_uuid
    ).order_by(Organisations.orgname, Groups.groupname).all()

    return render_template('settings/exclusions.html',
                         tenant_uuid=tenant_uuid,
                         analysis_groups=analysis_groups,
                         organisations=organisations,
                         groups=groups)


@settings_bp.route('/reset_mfa', methods=['POST'])
@login_required
def reset_mfa():
    if 'user_id' not in session:
        return redirect(url_for('login_bp.login'))

    user_id = session['user_id']
    account = Accounts.query.get(user_id)

    # Delete old MFA
    MFA.query.filter_by(useruuid=account.useruuid).delete()
    db.session.commit()

    # Setup new MFA
    secret = setup_mfa(account)

    # Redirect to MFA setup page
    return redirect(url_for('mfa.setup'))