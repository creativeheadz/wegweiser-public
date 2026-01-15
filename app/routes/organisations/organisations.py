# Filepath: app/routes/organisations/organisations.py
# Filepath: app/routes/tenant/organisations.py
# Filepath: app/routes/organisations.py
from flask import Blueprint, request, redirect, url_for, session, render_template, flash, jsonify
from app.models import db, Organisations, Groups, HealthScoreHistory, UserXOrganisation, OrganizationMetadata, Tenants
from app.forms.organisation_form import OrganisationForm  # We'll create this form
import uuid
from sqlalchemy.exc import IntegrityError
from app.utilities.app_access_login_required import login_required
import logging
from app.utilities.app_logging_helper import log_with_route
from flask import request, jsonify
from flask_wtf.csrf import CSRFProtect
from app import csrf
from app.forms.chat_form import ChatForm
from datetime import datetime, timezone
from app.forms.organisation_form import OrganisationForm
from app.forms.group_form import GroupForm
from sqlalchemy import text, desc
from uuid import UUID
import re
from . import organisations_bp
from app.utilities.guided_tour_manager import get_tour_for_page




#csrf = CSRFProtect()

@organisations_bp.route('/organisations', methods=['GET'])
@login_required
def organisations_page():
    form = OrganisationForm()
    group_form = GroupForm()  # Add group form
    tenantuuid = session.get('tenant_uuid')

    # Set the org select choices for group form
    group_form.orgselect.choices = [(str(org.orguuid), org.orgname)
                                   for org in Organisations.query.filter_by(tenantuuid=tenantuuid).all()]

    # Fetch organizations and prepare data for template
    organisations = []
    org_query = Organisations.query.filter_by(tenantuuid=tenantuuid).all()

    for org in org_query:
        groups = Groups.query.filter_by(orguuid=org.orguuid).all()
        initials = ''.join([word[0].upper() for word in org.orgname.split()])
        health_score = org.health_score or 0
        health_color = 'success' if health_score >= 80 else 'warning' if health_score >= 60 else 'danger'

        # Calculate total device count for this organization
        device_count = 0
        for group in groups:
            device_count += len(group.devices)

        organisations.append({
            'orguuid': org.orguuid,
            'orgname': org.orgname,
            'group_count': len(groups),
            'device_count': device_count,
            'health_score': health_score,
            'health_color': health_color,
            'initials': initials,
            'created_at': org.created_at,
            'groups': [{
                'groupuuid': str(group.groupuuid),
                'groupname': group.groupname,
            } for group in groups]  # Include groups data for each org
        })

    # Guided tour data for Organisations page with fallback to US spelling
    tour_data = get_tour_for_page('organisations', session.get('user_id')) or get_tour_for_page('organizations', session.get('user_id'))

    return render_template('organisations/index.html',
                         form=form,
                         group_form=group_form,
                         organisations=organisations,
                         tour_data=tour_data)

@organisations_bp.route('/organisation/<uuid:organisation_uuid>/health_history', methods=['GET'])
@login_required
def get_organisation_health_history(organisation_uuid):
    """
    Fetch the health history for an organisation to display in a chart.
    """
    try:
        # Fetch the organisation details
        organisation = Organisations.query.get(organisation_uuid)
        if not organisation:
            return jsonify({'error': 'Organisation not found'}), 404

        # Retrieve health history records for the organisation
        history = HealthScoreHistory.query.filter_by(
            entity_type='organisation',
            entity_uuid=organisation_uuid
        ).order_by(HealthScoreHistory.timestamp).all()

        # Format the health history data for the chart
        data = [{'x': h.timestamp.isoformat(), 'y': h.health_score} for h in history]

        # Append the current health score
        data.append({
            'x': datetime.utcnow().isoformat(),
            'y': organisation.health_score
        })

        return jsonify(data), 200

    except Exception as e:
        log_with_route(logging.ERROR, f"Error fetching organisation health history: {str(e)}", exc_info=True)
        return jsonify({'error': 'An unexpected error occurred'}), 500


@organisations_bp.route('/organisations/list', methods=['GET'])
@login_required
def list_organisations():
    tenantuuid = session.get('tenant_uuid')
    if not tenantuuid:
        log_with_route(logging.WARNING, 'Tenant UUID is missing in session.')
        return jsonify({"error": "Tenant UUID is required"}), 400

    organisations = Organisations.query.filter_by(tenantuuid=tenantuuid).all()
    result = []
    for org in organisations:
        groups = Groups.query.filter_by(orguuid=org.orguuid).all()
        result.append({
            'orguuid': str(org.orguuid),
            'orgname': org.orgname,
            'health_score': org.health_score,
            'created_at': org.created_at,
            'groups': [{'groupuuid': str(group.groupuuid), 'groupname': group.groupname} for group in groups]
        })

    log_with_route(logging.INFO, f'Fetched organisations for tenant UUID {tenantuuid}')
    return jsonify({"organisations": result}), 200

@organisations_bp.route('/organisations/<uuid:org_uuid>', methods=['GET'])
@login_required
def view_organisation(org_uuid):
    organisation = Organisations.query.get_or_404(org_uuid)
    chat_form = ChatForm()
    return render_template('organisations/index-single-organisation.html', organisation=organisation)




@organisations_bp.route('/organisations/groups', methods=['GET'])
@login_required
def get_groups():
    tenantuuid = session.get('tenant_uuid')
    if not tenantuuid:
        log_with_route(logging.WARNING, 'Tenant UUID is missing in the get groups request.')
        return jsonify({'error': 'Tenant UUID is required'}), 400

    try:
        groups = Groups.query.filter_by(tenantuuid=tenantuuid).all()

        organisations = {}
        for group in groups:
            orguuid = str(group.orguuid)
            if orguuid not in organisations:
                organisations[orguuid] = {
                    'orgname': group.organisation.orgname,
                    'groups': []
                }
            organisations[orguuid]['groups'].append({
                'groupuuid': group.groupuuid,
                'groupname': group.groupname
            })

        log_with_route(logging.INFO, f'Groups fetched successfully for tenant UUID {tenantuuid}.')
        return jsonify({'organisations': organisations}), 200
    except Exception as e:
        log_with_route(logging.ERROR, f'Error fetching groups for tenant UUID {tenantuuid}: {e}', exc_info=True)
        return jsonify({'error': str(e)}), 500


@organisations_bp.route('/organisations/<uuid:org_uuid>/analyses', methods=['GET'])
@login_required
def get_organization_analyses(org_uuid):
    """Get organization analyses for AJAX loading"""
    try:
        # Validate UUID format
        try:
            UUID(str(org_uuid))
        except (ValueError, AttributeError, TypeError):
            log_with_route(logging.ERROR, f"Invalid organization UUID provided: {org_uuid}")
            return jsonify({'error': 'Invalid organization UUID provided'}), 400

        # Fetch the tenant object
        tenant = Tenants.query.filter_by(tenantuuid=session['tenant_uuid']).first()
        if not tenant:
            return jsonify({'error': 'Tenant not found'}), 404

        # Verify organization exists before proceeding
        org = Organisations.query.filter_by(orguuid=org_uuid).first()
        if not org:
            log_with_route(logging.ERROR, f"Organization with UUID {org_uuid} not found")
            return jsonify({'error': 'Organization not found'}), 404

        # Get latest organization analyses
        latest_analyses = db.session.execute(text("""
            SELECT DISTINCT ON (metalogos_type)
                orguuid,
                metalogos_type,
                ai_analysis,
                score,
                analyzed_at,
                created_at
            FROM orgmetadata
            WHERE orguuid = :org_uuid
            AND processing_status = 'processed'
            ORDER BY metalogos_type, created_at DESC
        """), {'org_uuid': str(org_uuid)}).fetchall()

        # Get pending analyses count
        pending_analyses = db.session.execute(text("""
            SELECT metalogos_type, COUNT(*) as pending_count
            FROM orgmetadata
            WHERE orguuid = :org_uuid
            AND processing_status = 'pending'
            GROUP BY metalogos_type
        """), {'org_uuid': str(org_uuid)}).fetchall()

        pending_map = {row.metalogos_type: row.pending_count for row in pending_analyses}

        def clean_analysis_text(text):
            """Clean HTML tags and format text for display"""
            if not text:
                return "No analysis available"
            # Remove HTML tags but keep line breaks
            clean_text = re.sub(r'<[^>]+>', '', text)
            return clean_text.strip()

        analyses_data = []
        for row in latest_analyses:
            # Get previous score for comparison
            prev_analysis = db.session.execute(text("""
                SELECT score
                FROM orgmetadata
                WHERE orguuid = :org_uuid
                AND metalogos_type = :metalogos_type
                AND processing_status = 'processed'
                AND created_at < :current_created_at
                ORDER BY created_at DESC
                LIMIT 1
            """), {
                'org_uuid': str(org_uuid),
                'metalogos_type': row.metalogos_type,
                'current_created_at': row.created_at
            }).fetchone()

            prev_score = prev_analysis.score if prev_analysis else None

            analyses_data.append({
                'type': row.metalogos_type,
                'name': 'Organization Health Analysis',  # Friendly name
                'analysis': row.ai_analysis,  # Keep original HTML formatting
                'score': int(row.score) if row.score is not None else 0,
                'previous_score': int(prev_score) if prev_score is not None else None,
                'analyzed_at': datetime.fromtimestamp(row.analyzed_at) if row.analyzed_at else None,
                'pending_count': pending_map.get(row.metalogos_type, 0),
                'icon': 'fa-building'  # Organization icon
            })

        # Sort by score descending
        analyses_data.sort(key=lambda x: x['score'], reverse=True)

        return render_template('organisations/organalyses.html', analyses=analyses_data)

    except Exception as e:
        log_with_route(logging.ERROR, f"Error fetching organization analyses: {str(e)}", exc_info=True)
        return jsonify({'error': 'An unexpected error occurred'}), 500

@organisations_bp.route('/organisations/delete_group', methods=['POST'])
@login_required
def delete_group():
    data = request.get_json()
    groupuuid = data.get('groupuuid')

    if not groupuuid:
        log_with_route(logging.WARNING, 'Group UUID is missing in the delete group request.')
        return jsonify({"error": "Group UUID is required"}), 400

    try:
        group = Groups.query.filter_by(groupuuid=groupuuid).first()
        if not group:
            log_with_route(logging.WARNING, f'Group with UUID {groupuuid} not found.')
            return jsonify({"error": "Group not found"}), 404

        db.session.delete(group)
        db.session.commit()
        log_with_route(logging.INFO, f'Group with UUID {groupuuid} deleted successfully.')
        return jsonify({"success": "Group deleted successfully"}), 200
    except Exception as e:
        log_with_route(logging.ERROR, f'Error deleting group with UUID {groupuuid}: {e}', exc_info=True)
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

@organisations_bp.route('/organisations/update', methods=['POST'])
@login_required
def update_organisation():
    data = request.get_json()
    orguuid = data.get('orguuid')
    updated_fields = data.get('updated_fields', {})

    if not orguuid:
        log_with_route(logging.WARNING, 'Organisation UUID is missing in the update request.')
        return jsonify({"error": "Organisation UUID is required"}), 400

    try:
        organisation = Organisations.query.filter_by(orguuid=orguuid).first()
        if not organisation:
            log_with_route(logging.WARNING, f'Organisation with UUID {orguuid} not found.')
            return jsonify({"error": "Organisation not found"}), 404

        for key, value in updated_fields.items():
            if hasattr(organisation, key):
                setattr(organisation, key, value)

        db.session.commit()
        log_with_route(logging.INFO, f'Organisation with UUID {orguuid} updated successfully.')
        return jsonify({"success": "Organisation updated successfully"}), 200
    except Exception as e:
        log_with_route(logging.ERROR, f'Error updating organisation with UUID {orguuid}: {e}', exc_info=True)
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

