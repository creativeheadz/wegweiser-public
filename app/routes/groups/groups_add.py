# Filepath: app/routes/groups/groups_add.py
# groups_add.py
from flask import Blueprint, request, session, render_template, flash, jsonify, redirect, url_for
from app.models import db, Groups, Organisations
from app.forms.group_form import GroupForm
from app.utilities.app_access_login_required import login_required
import logging
from app.utilities.app_logging_helper import log_with_route
import uuid
from sqlalchemy.exc import IntegrityError
from . import groups_bp


@groups_bp.route('/groups/add', methods=['POST'])
@login_required
def add_group():
    form = GroupForm()
    form.orgselect.choices = [(str(org.orguuid), org.orgname) 
                             for org in Organisations.query.filter_by(tenantuuid=session.get('tenant_uuid')).all()]

    if form.validate_on_submit():
        groupname = form.groupname.data
        orguuid = form.orgselect.data
        tenantuuid = session.get('tenant_uuid')

        if not all([groupname, orguuid, tenantuuid]):
            flash("Group name, Organisation, and Tenant are required.", "danger")
            return jsonify({'error': 'Missing required fields'}), 400

        try:
            new_group = Groups(
                groupuuid=uuid.uuid4(),
                groupname=groupname,
                orguuid=orguuid,
                tenantuuid=tenantuuid
            )
            db.session.add(new_group)
            db.session.commit()
            
            flash("Group created successfully!", "success")
            return jsonify({
                'success': True,
                'message': 'Group created successfully'
            }), 200

        except IntegrityError:
            db.session.rollback()
            flash("Group name must be unique within the organisation.", "danger")
            return jsonify({'error': 'Group name must be unique within the organisation'}), 400
            
        except Exception as e:
            db.session.rollback()
            log_with_route(logging.ERROR, f'Error creating group: {str(e)}')
            flash(f"An error occurred: {str(e)}", "danger")
            return jsonify({'error': str(e)}), 500

    for field, errors in form.errors.items():
        for error in errors:
            flash(f"{getattr(form, field).label.text}: {error}", "danger")
    return jsonify({'error': 'Form validation failed', 'errors': form.errors}), 400