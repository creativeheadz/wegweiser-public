# Filepath: app/routes/organisations/organisations_delete.py
# Filepath: app/routes/tenant/organisations_delete.py
# routes/tenant/organisations_delete.py
from flask import Blueprint, request, redirect, url_for, session, render_template, flash, jsonify
from app.models import db, Organisations, UserXOrganisation
from app.utilities.app_access_login_required import login_required
import logging
from app.utilities.app_logging_helper import log_with_route
from . import organisations_bp  # Import the blueprint

@organisations_bp.route('/organisations/delete', methods=['POST'])
@login_required
def delete_organisation():
    data = request.get_json()
    orguuid = data.get('orguuid')
    if not orguuid:
        return jsonify({"error": "Organisation UUID is required"}), 400

    try:
        # First delete any user associations
        organisation = Organisations.query.get(orguuid)
        if not organisation:
            return jsonify({"error": "Organisation not found"}), 404

        # Delete user associations first
        UserXOrganisation.query.filter_by(orguuid=orguuid).delete()
        
        # Now delete the organization
        db.session.delete(organisation)
        db.session.commit()
        
        flash('Organisation deleted successfully', 'success')
        return jsonify({"success": True}), 200
        
    except Exception as e:
        db.session.rollback()
        log_with_route(logging.ERROR, f'Error deleting organisation: {str(e)}')
        flash(f'Error deleting organisation: {str(e)}', 'error')
        return jsonify({"error": str(e)}), 500