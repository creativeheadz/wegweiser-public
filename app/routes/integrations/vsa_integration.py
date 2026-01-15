# Filepath: app/routes/integrations/vsa_integration.py
# Filepath: app/routes/vsa_integration.py
from flask import Blueprint, render_template, request, session, flash, redirect, url_for
from app.forms.vsa_integration_form import VSAConnectionForm, VSASelectionForm, VSAConfirmationForm
from app.utilities.app_access_login_required import login_required
from app.utilities.guided_tour_manager import get_tour_for_page

from app.utilities.app_logging_helper import log_with_route
from app.models import db, Organisations, Groups
import logging
import requests
import uuid
import json
import time

vsa_integration_bp = Blueprint('vsa_integration_bp', __name__)

@vsa_integration_bp.route('/vsa_integration', methods=['GET', 'POST'])
@login_required
def vsa_integration_wizard():
    connection_form = VSAConnectionForm()
    if connection_form.validate_on_submit():
        # Store the connection info in the session
        session['vsa_endpoint'] = connection_form.endpoint.data.rstrip('/')
        session['vsa_token_id'] = connection_form.token_id.data
        session['vsa_token_secret'] = connection_form.token_secret.data

        # Verify the connection
        if verify_vsa_connection():
            flash('Connection successful!', 'success')
            return redirect(url_for('vsa_integration_bp.fetch_vsa_data'))
        else:
            flash('Connection failed. Please check your credentials.', 'error')

    # Guided tour data for VSA 10 integration (use dummy when none exists)
    tour_data = get_tour_for_page('integrations-vsa10', session.get('user_id')) or {
        'is_active': True,
        'page_identifier': 'integrations-vsa10',
        'tour_name': 'Quick Tour',
        'tour_config': {},
        'steps': [{'id': 'welcome', 'title': 'Welcome', 'text': 'This is a placeholder tour.'}],
        'user_progress': {'completed_steps': [], 'is_completed': False}
    }

    return render_template('integrations/index-vsa10.html', form=connection_form, step=1, tour_data=tour_data)

def verify_vsa_connection():
    try:
        response = requests.get(
            f"{session['vsa_endpoint']}/organizations",
            auth=(session['vsa_token_id'], session['vsa_token_secret']),
            params={'$top': 1}
        )
        response.raise_for_status()
        log_with_route(logging.INFO, f"VSA connection successful. Status code: {response.status_code}")
        log_with_route(logging.DEBUG, f"VSA connection response: {response.text}")
        return True
    except requests.RequestException as e:
        log_with_route(logging.ERROR, f'VSA connection verification failed: {str(e)}')
        return False

@vsa_integration_bp.route('/vsa_integration/fetch_data', methods=['GET'])
@login_required
def fetch_vsa_data():
    orgs = fetch_all_items('organizations')
    sites = fetch_all_items('sites')
    groups = fetch_all_items('groups')

    # Process the data into a hierarchical structure
    org_data = []
    for org in orgs['Data']:
        org_item = {
            'id': org['Id'],
            'name': org['Name'],
            'sites': []
        }
        for site in sites['Data']:
            if site['ParentId'] == org['Id']:
                site_item = {
                    'id': site['Id'],
                    'name': site['Name'],
                    'groups': []
                }
                for group in groups['Data']:
                    if group['ParentSiteId'] == site['Id']:
                        site_item['groups'].append({
                            'id': group['Id'],
                            'name': group['Name']
                        })
                org_item['sites'].append(site_item)
        org_data.append(org_item)

    # Store the processed data in the session
    session['vsa_data'] = org_data

    form = VSASelectionForm()
    # Guided tour data for VSA 10 integration (use dummy when none exists)
    tour_data = get_tour_for_page('integrations-vsa10', session.get('user_id')) or {
        'is_active': True,
        'page_identifier': 'integrations-vsa10',
        'tour_name': 'Quick Tour',
        'tour_config': {},
        'steps': [{'id': 'welcome', 'title': 'Welcome', 'text': 'This is a placeholder tour.'}],
        'user_progress': {'completed_steps': [], 'is_completed': False}
    }

    return render_template('integrations/index-vsa10.html', step=2, org_data=org_data, form=form, tour_data=tour_data)

def fetch_all_items(resource):
    items = {'Data': []}
    skip = 0
    while True:
        response = requests.get(
            f"{session['vsa_endpoint']}/{resource}",
            auth=(session['vsa_token_id'], session['vsa_token_secret']),
            params={'$top': 50, '$skip': skip}
        )
        response.raise_for_status()
        batch = response.json()
        items['Data'].extend(batch['Data'])
        if len(batch['Data']) < 50:
            items['Meta'] = batch['Meta']
            break
        skip += 50
    return items

@vsa_integration_bp.route('/vsa_integration/select_items', methods=['POST'])
@login_required
def select_items():
    selected_orgs = request.form.getlist('selected_orgs')
    selected_groups = request.form.getlist('selected_groups')

    # Filter the data based on selections
    org_data = session.get('vsa_data', [])
    selected_data = []
    for org in org_data:
        if str(org['id']) in selected_orgs:
            selected_org = {
                'id': org['id'],
                'name': org['name'],
                'sites': []
            }
            for site in org['sites']:
                selected_site = {
                    'id': site['id'],
                    'name': site['name'],
                    'groups': [group for group in site['groups'] if str(group['id']) in selected_groups]
                }
                if selected_site['groups']:
                    selected_org['sites'].append(selected_site)
            if selected_org['sites']:
                selected_data.append(selected_org)

    # Store the selections in the session
    session['selected_vsa_data'] = selected_data

    # Create a new form instance for the confirmation step
    form = VSAConfirmationForm()

    # Guided tour data for VSA 10 integration (use dummy when none exists)
    tour_data = get_tour_for_page('integrations-vsa10', session.get('user_id')) or {
        'is_active': True,
        'page_identifier': 'integrations-vsa10',
        'tour_name': 'Quick Tour',
        'tour_config': {},
        'steps': [{'id': 'welcome', 'title': 'Welcome', 'text': 'This is a placeholder tour.'}],
        'user_progress': {'completed_steps': [], 'is_completed': False}
    }

    return render_template('integrations/index-vsa10.html', step=3, selected_data=selected_data, form=form, tour_data=tour_data)

@vsa_integration_bp.route('/vsa_integration/import_items', methods=['POST'])
@login_required
def import_items():
    confirmation_form = VSAConfirmationForm()
    if confirmation_form.validate_on_submit():
        tenant_uuid = session.get('tenant_uuid')
        if not tenant_uuid:
            flash('Tenant UUID is required', 'error')
            return redirect(url_for('vsa_integration_bp.vsa_integration_wizard'))

        try:
            for org in session['selected_vsa_data']:
                new_org = Organisations(
                    orguuid=str(uuid.uuid4()),
                    orgname=org['name'],
                    tenantuuid=tenant_uuid
                )
                db.session.add(new_org)
                db.session.flush()  # Flush to get the new org's UUID

                for site in org['sites']:
                    for group in site['groups']:
                        group_name = f"{site['name']} - {group['name']}"
                        new_group = Groups(
                            groupuuid=str(uuid.uuid4()),
                            groupname=group_name,
                            orguuid=new_org.orguuid,
                            tenantuuid=tenant_uuid,
                            created_at=int(time.time()),
                            health_score=None
                        )
                        db.session.add(new_group)
                        db.session.flush()  # Flush to get the new group's UUID

                        # Assign custom field to VSA group
                        assign_custom_field(group['id'], new_group.groupuuid)

            db.session.commit()
            flash('VSA items imported successfully', 'success')
        except Exception as e:
            db.session.rollback()
            log_with_route(logging.ERROR, f'Error importing VSA items: {str(e)}')
            flash('An error occurred while importing VSA items', 'error')

        # Guided tour data for VSA 10 integration (use dummy when none exists)
        tour_data = get_tour_for_page('integrations-vsa10', session.get('user_id')) or {
            'is_active': True,
            'page_identifier': 'integrations-vsa10',
            'tour_name': 'Quick Tour',
            'tour_config': {},
            'steps': [{'id': 'welcome', 'title': 'Welcome', 'text': 'This is a placeholder tour.'}],
            'user_progress': {'completed_steps': [], 'is_completed': False}
        }

        return render_template('integrations/index-vsa10.html', step=4, tour_data=tour_data)

    flash('Invalid form submission', 'error')
    return redirect(url_for('vsa_integration_bp.vsa_integration_wizard'))

def assign_custom_field(vsa_group_id, wegweiser_group_uuid):
    custom_field_id = get_or_create_custom_field()

    request_body = {
        "ContextType": "Group",
        "ContextItemId": str(vsa_group_id),
        "UseDefaultValue": False,
        "Value": str(wegweiser_group_uuid),
    }

    try:
        response = requests.post(
            f"{session['vsa_endpoint']}/customFields/{custom_field_id}/assign",
            auth=(session['vsa_token_id'], session['vsa_token_secret']),
            json=request_body
        )
        response.raise_for_status()
        log_with_route(logging.INFO, f"Custom field assigned successfully for VSA group {vsa_group_id}")
    except requests.RequestException as e:
        log_with_route(logging.ERROR, f"Failed to assign custom field for VSA group {vsa_group_id}: {str(e)}")
        raise

def get_or_create_custom_field():
    custom_field_name = "WegweiserGroupUUID"

    try:
        # Check if the custom field already exists
        response = requests.get(
            f"{session['vsa_endpoint']}/customFields",
            auth=(session['vsa_token_id'], session['vsa_token_secret']),
            params={'$filter': f"Name eq '{custom_field_name}'"}
        )
        response.raise_for_status()
        existing_fields = response.json()['Data']

        if existing_fields:
            return existing_fields[0]['Id']

        # If the custom field doesn't exist, create it
        create_body = {
            "Name": custom_field_name,
            "Type": "Text",
            "DefaultValue": "",
            "IsRequired": False,
            "ApplicableToOrganizations": True,
            "ApplicableToSites": True,
            "ApplicableToGroups": True,
            "ApplicableToDevices": True
        }

        response = requests.post(
            f"{session['vsa_endpoint']}/customFields",
            auth=(session['vsa_token_id'], session['vsa_token_secret']),
            json=create_body
        )
        response.raise_for_status()
        new_field = response.json()['Data']

        log_with_route(logging.INFO, f"Created new custom field: {custom_field_name}")
        return new_field['Id']
    except requests.RequestException as e:
        log_with_route(logging.ERROR, f"Failed to get or create custom field: {str(e)}")
        raise