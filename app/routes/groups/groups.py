# Filepath: app/routes/groups/groups.py
# Filepath: app/routes/tenant/groups.py
# Filepath: app/routes/groups.py
from flask import Blueprint, request, jsonify, session, render_template, flash, redirect, url_for
from app.models import db, Groups, Organisations, Devices, Tenants, Messages, Conversations, HealthScoreHistory, GroupMetadata
from app.forms.group_form import GroupForm
from app.forms.chat_form import ChatForm
import uuid
import time
from uuid import UUID
from sqlalchemy.exc import IntegrityError
from sqlalchemy import text, desc
from app.utilities.app_access_login_required import login_required
import logging
from app.utilities.app_logging_helper import log_with_route
import bleach
from app.utilities.langchain_utils import create_langchain_conversation, get_ai_response, adapt_response_style
from app.routes.ai.ai import get_or_create_conversation
from datetime import datetime, timezone
from . import groups_bp  # Import the blueprint
from app.utilities.guided_tour_manager import get_tour_for_page



@groups_bp.route('/group/<uuid:group_uuid>/health_history', methods=['GET'])
@login_required
def get_group_health_history(group_uuid):
    """
    Fetch the health history for a group to display in a chart.
    """
    try:
        # Fetch the group details
        group = Groups.query.get(group_uuid)
        if not group:
            return jsonify({'error': 'Group not found'}), 404

        # Retrieve health history records for the group
        history = HealthScoreHistory.query.filter_by(
            entity_type='group',
            entity_uuid=group_uuid
        ).order_by(HealthScoreHistory.timestamp).all()

        # Format the health history data for the chart
        data = [{'x': h.timestamp.isoformat(), 'y': h.health_score} for h in history]

        # Append the current health score
        data.append({
            'x': datetime.utcnow().isoformat(),
            'y': group.health_score
        })

        return jsonify(data), 200

    except Exception as e:
        log_with_route(logging.ERROR, f"Error fetching group health history: {str(e)}", exc_info=True)
        return jsonify({'error': 'An unexpected error occurred'}), 500



@groups_bp.route('/groups/getorgs', methods=['GET'])
@login_required
def get_organisations():
    tenantuuid = session.get('tenant_uuid')
    if not tenantuuid:
        return jsonify({"error": "Tenant UUID is required"}), 400

    organisations = Organisations.query.filter_by(tenantuuid=tenantuuid).all()
    result = []
    for org in organisations:
        result.append({
            'orguuid': org.orguuid,
            'orgname': org.orgname
        })

    return jsonify({"organisations": result}), 200

@groups_bp.route('/groups', methods=['GET', 'POST'])
@login_required
def groups_page():
    form = GroupForm()

    # Populate the orgselect field with organizations from the database
    tenantuuid = session.get('tenant_uuid')
    form.orgselect.choices = [(org.orguuid, org.orgname) for org in Organisations.query.filter_by(tenantuuid=tenantuuid).all()]

    # Create a dictionary to quickly look up organization names by UUID
    org_names = {str(org.orguuid): org.orgname for org in Organisations.query.filter_by(tenantuuid=tenantuuid).all()}

    # Process groups for template and group by organization
    groups_by_org = {}
    groups = []  # Keep flat list for backward compatibility

    for group in Groups.query.filter_by(tenantuuid=tenantuuid).all():
        initials = ''.join([word[0].upper() for word in group.groupname.split()])
        health_score = group.health_score or 0
        health_color = 'success' if health_score >= 80 else 'warning' if health_score >= 60 else 'danger'

        # Get the organization name for this group
        org_uuid_str = str(group.orguuid)
        org_name = org_names.get(org_uuid_str, "Unknown Organization")

        group_data = {
            'groupuuid': group.groupuuid,
            'groupname': group.groupname,
            'orguuid': group.orguuid,
            'orgname': org_name,
            'device_count': len(group.devices),
            'health_score': health_score,
            'health_color': health_color,
            'initials': initials
        }

        groups.append(group_data)

        # Group groups by organization
        if org_name not in groups_by_org:
            groups_by_org[org_name] = {
                'orgname': org_name,
                'orguuid': str(group.orguuid),
                'groups': []
            }
        groups_by_org[org_name]['groups'].append(group_data)

    # Sort organizations by name
    # Guided tour data for Groups page
    tour_data = get_tour_for_page('groups', session.get('user_id'))

    sorted_orgs = sorted(groups_by_org.items(), key=lambda x: x[1]['orgname'])

    # Render the template with the form and the group data
    return render_template('groups/index.html', form=form, groups=groups, groups_by_org=sorted_orgs, tour_data=tour_data)


@groups_bp.route('/groups/<uuid:group_uuid>')
@login_required
def view_group(group_uuid):
    group = Groups.query.get_or_404(group_uuid)
    org = Organisations.query.filter_by(orguuid=group.orguuid).first()
    device = None
    chat_form = ChatForm()

    return render_template('groups/index-single-group.html', group=group, org=org, device=device, form=chat_form, entity=group, entity_type='group')

def clean_analysis_text(text):
    """Clean and sanitize analysis text for display"""
    if not text:
        return ""

    # Remove any script tags or dangerous content
    cleaned = bleach.clean(text, tags=['p', 'br', 'ul', 'li', 'strong', 'em', 'h4', 'h5'], strip=True)
    return cleaned

@groups_bp.route('/groups/<uuid:group_uuid>/analyses', methods=['GET'])
@login_required
def get_group_analyses(group_uuid):
    """Get group analyses for AJAX loading"""
    try:
        # Validate UUID format
        try:
            UUID(str(group_uuid))
        except (ValueError, AttributeError, TypeError):
            log_with_route(logging.ERROR, f"Invalid group UUID provided: {group_uuid}")
            return jsonify({'error': 'Invalid group UUID provided'}), 400

        # Fetch the tenant object
        tenant = Tenants.query.filter_by(tenantuuid=session['tenant_uuid']).first()
        if not tenant:
            return jsonify({'error': 'Tenant not found'}), 404

        # Verify group exists before proceeding
        group = Groups.query.filter_by(groupuuid=group_uuid).first()
        if not group:
            log_with_route(logging.ERROR, f"Group with UUID {group_uuid} not found")
            return jsonify({'error': 'Group not found'}), 404

        # Get latest group analyses
        latest_analyses = db.session.execute(text("""
            SELECT DISTINCT ON (metalogos_type)
                groupuuid,
                metalogos_type,
                ai_analysis,
                score,
                analyzed_at,
                created_at,
                device_count,
                source_devices
            FROM groupmetadata
            WHERE groupuuid = :group_uuid
            AND processing_status = 'processed'
            ORDER BY metalogos_type, created_at DESC
        """), {'group_uuid': str(group_uuid)}).fetchall()

        # Get pending counts
        pending_counts = db.session.execute(text("""
            SELECT metalogos_type, COUNT(*) as pending_count
            FROM groupmetadata
            WHERE groupuuid = :group_uuid
            AND processing_status = 'pending'
            GROUP BY metalogos_type
        """), {'group_uuid': str(group_uuid)}).fetchall()

        # Create a mapping of pending counts
        pending_map = {row.metalogos_type: row.pending_count for row in pending_counts}

        # Process the results
        analyses_data = []
        for row in latest_analyses:
            # Get the previous score for this type
            prev_score = db.session.execute(text("""
                SELECT score
                FROM groupmetadata
                WHERE groupuuid = :group_uuid
                AND metalogos_type = :type
                AND processing_status = 'processed'
                AND created_at < :created_at
                ORDER BY created_at DESC
                LIMIT 1
            """), {
                'group_uuid': str(group_uuid),
                'type': row.metalogos_type,
                'created_at': row.created_at
            }).scalar()

            analyses_data.append({
                'type': row.metalogos_type,
                'name': 'Group Health Analysis',  # Friendly name
                'analysis': clean_analysis_text(row.ai_analysis),
                'score': int(row.score) if row.score is not None else 0,
                'previous_score': int(prev_score) if prev_score is not None else None,
                'analyzed_at': datetime.fromtimestamp(row.analyzed_at) if row.analyzed_at else None,
                'pending_count': pending_map.get(row.metalogos_type, 0),
                'device_count': row.device_count or 0,
                'icon': 'fa-users'  # Group icon
            })

        # Sort by score descending
        analyses_data.sort(key=lambda x: x['score'], reverse=True)

        return render_template('groups/groupanalyses.html', analyses=analyses_data)

    except Exception as e:
        log_with_route(logging.ERROR, f"Error fetching group analyses: {str(e)}", exc_info=True)
        return jsonify({'error': 'Failed to fetch analyses'}), 500

@groups_bp.route('/groups/update', methods=['POST'])
@login_required
def update_group():
    data = request.get_json()
    groupuuid = data.get('groupuuid')
    updated_fields = data.get('updated_fields', {})

    if not groupuuid:
        log_with_route(logging.WARNING, 'Group UUID is missing in the update request.')
        return jsonify({"error": "Group UUID is required"}), 400

    try:
        group = Groups.query.filter_by(groupuuid=groupuuid).first()
        if not group:
            log_with_route(logging.WARNING, f'Group with UUID {groupuuid} not found.')
            return jsonify({"error": "Group not found"}), 404

        for key, value in updated_fields.items():
            if hasattr(group, key):
                setattr(group, key, value)

        db.session.commit()
        log_with_route(logging.INFO, f'Group with UUID {groupuuid} updated successfully.')
        return jsonify({"success": "Group updated successfully"}), 200
    except Exception as e:
        log_with_route(logging.ERROR, f'Error updating group with UUID {groupuuid}: {e}', exc_info=True)
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

@groups_bp.route('/ai/group/<uuid:group_uuid>/chat', methods=['POST'])
@login_required
def group_chat(group_uuid):
    user_id = session.get('user_id')
    user_firstname = session.get('userfirstname', 'User')
    log_with_route(logging.INFO, f'Initiating chat for group UUID {group_uuid} by user ID {user_id}.')

    group = Groups.query.get(group_uuid)
    if not group:
        return jsonify({"error": "Group not found"}), 404

    user_message = request.json.get('message')

    # Get or create a conversation related to the group
    conversation = Conversations.query.filter_by(
        entityuuid=group_uuid,
        entity_type='group'
    ).order_by(Conversations.last_updated.desc()).first()

    if not conversation:
        conversation = Conversations.create_non_device_conversation(
            tenantuuid=group.tenantuuid,
            entityuuid=group_uuid,
            entity_type='group'
        )
        db.session.add(conversation)
        db.session.commit()


    # Fetch the group's context and tenant details
    group_context = get_group_context(group)
    tenant = Tenants.query.get(group.tenantuuid)
    tenant_profile = get_tenant_profile(tenant)
    user_context = f"User's name: {user_firstname}"

    # Create the conversation chain for the AI response
    conversation_chain = create_langchain_conversation(
        str(group_uuid),
        'group',
        tenant_profile,
        group_context,
        user_context
    )
    ai_response = get_ai_response(conversation_chain, user_message, f"group_{group_uuid}")

    ai_response_content = ai_response.content if hasattr(ai_response, 'content') else str(ai_response)
    ai_response_content = adapt_response_style(ai_response_content, tenant.preferred_communication_style)

    # Store the conversation with real timestamps
    # sequence_id will auto-increment to ensure proper ordering
    user_message_record = Messages(
        messageuuid=uuid.uuid4(),
        conversationuuid=conversation.conversationuuid,
        useruuid=user_id,
        tenantuuid=group.tenantuuid,
        entityuuid=group_uuid,
        entity_type='group',
        title='User Message',
        content=user_message,
        is_read=False,
        created_at=int(time.time()),
        message_type='chat'
    )

    ai_message_record = Messages(
        messageuuid=uuid.uuid4(),
        conversationuuid=conversation.conversationuuid,
        useruuid=None,
        tenantuuid=group.tenantuuid,
        entityuuid=group_uuid,
        entity_type='group',
        title='AI Response',
        content=ai_response_content,
        is_read=False,
        created_at=int(time.time()),
        message_type='chat'
    )

    db.session.add(user_message_record)
    db.session.add(ai_message_record)
    conversation.last_updated = int(time.time())
    db.session.commit()

    log_with_route(logging.INFO, f'Chat history and conversation updated successfully for group UUID {group_uuid}.')

    return jsonify({"response": ai_response_content})

def get_group_context(group):
    devices = Devices.query.filter_by(groupuuid=group.groupuuid).all()
    device_info = [f"Device: {d.devicename}, Health Score: {d.health_score}" for d in devices]
    return f"""
    Group Name: {group.groupname}
    Group Health Score: {group.health_score}
    Number of Devices: {len(devices)}
    Devices:
    {' '.join(device_info)}
    """

def get_tenant_profile(tenant):
    return {
        'tenantname': tenant.tenantname,
        'tenantuuid': str(tenant.tenantuuid),
        'industry': tenant.industry,
        'company_size': tenant.company_size,
        'preferred_communication_style': tenant.preferred_communication_style
    }