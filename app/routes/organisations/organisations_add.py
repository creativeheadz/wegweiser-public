# Filepath: app/routes/organisations/organisations_add.py
import uuid
import logging
from datetime import datetime, timezone

from flask import Blueprint, request, session, render_template, flash, jsonify, redirect, url_for
from sqlalchemy.exc import IntegrityError
from flask_wtf.csrf import CSRFProtect

from app import csrf
from app.models import db, Organisations, Groups, HealthScoreHistory, UserXOrganisation
from app.forms.organisation_form import OrganisationForm
from app.forms.group_form import GroupForm
from app.forms.chat_form import ChatForm
from app.utilities.app_access_login_required import login_required
from app.utilities.app_logging_helper import log_with_route
from . import organisations_bp  # Import the blueprint


@organisations_bp.route('/organisations/add', methods=['POST'])
@login_required
def add_organisation():
    data = request.get_json()
    if not data:
        return jsonify({'error': 'No data provided'}), 400
        
    orgname = data.get('orgname')
    groupname = data.get('groupname')
    tenantuuid = session.get('tenant_uuid')

    if not all([orgname, groupname, tenantuuid]):
        return jsonify({'error': 'Missing required fields'}), 400

    try:
        # Check for existing organization
        existing_org = Organisations.query.filter_by(
            orgname=orgname, 
            tenantuuid=tenantuuid
        ).first()
        
        if existing_org:
            flash(f'An organisation with the specified name already exists', 'error')
            return jsonify({'error': 'Organisation name already exists'}), 400

        # Create new organization
        new_organisation = Organisations(
            orguuid=uuid.uuid4(),
            orgname=orgname,
            tenantuuid=tenantuuid
        )
        db.session.add(new_organisation)
        db.session.flush()

        # Create initial group
        new_group = Groups(
            groupuuid=uuid.uuid4(),
            groupname=groupname,
            orguuid=new_organisation.orguuid,
            tenantuuid=tenantuuid
        )
        db.session.add(new_group)
        db.session.commit()

        flash('Organisation created successfully', 'success')

        return jsonify({
            'success': True,
            'message': 'Organisation created successfully'
        }), 200

    except Exception as e:
        db.session.rollback()
        flash(f'Error creating organisation: {str(e)}', 'error')
        log_with_route(logging.ERROR, f'Error creating organisation: {str(e)}')
        return jsonify({'error': str(e)}), 500