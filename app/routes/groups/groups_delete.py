# Filepath: app/routes/groups/groups_delete.py
# groups_delete.py
from flask import Blueprint, request, session, render_template, flash, jsonify, redirect, url_for
from app.models import db, Groups
from app.utilities.app_access_login_required import login_required
import logging
from app.utilities.app_logging_helper import log_with_route
from . import groups_bp

@groups_bp.route('/groups/delete', methods=['POST'])
@login_required
def delete_group():
    data = request.get_json()
    groupuuid = data.get('groupuuid')

    if not groupuuid:
        flash("Group UUID is required", "danger")
        return jsonify({"error": "Group UUID is required"}), 400

    try:
        group = Groups.query.filter_by(groupuuid=groupuuid).first()
        if not group:
            flash("Group not found", "danger")
            return jsonify({"error": "Group not found"}), 404

        # Check if this group belongs to the current tenant
        if str(group.tenantuuid) != str(session.get('tenant_uuid')):
            flash("You are not authorized to delete this group", "danger")
            return jsonify({"error": "Unauthorized"}), 403

        db.session.delete(group)
        db.session.commit()
        
        flash("Group deleted successfully!", "success")
        return jsonify({
            'success': True,
            'message': 'Group deleted successfully'
        }), 200
        
    except Exception as e:
        db.session.rollback()
        log_with_route(logging.ERROR, f'Error deleting group with UUID {groupuuid}: {e}', exc_info=True)
        flash(f"An error occurred while deleting the group: {str(e)}", "danger")
        return jsonify({"error": str(e)}), 500