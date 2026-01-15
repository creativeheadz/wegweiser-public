# Filepath: app/routes/tenant/csv_import.py
import csv
import io
import uuid
import time
import logging
import os
from flask import Blueprint, render_template, request, session, flash, redirect, url_for, jsonify, current_app
from werkzeug.utils import secure_filename

from app.forms.csv_import_form import CsvImportForm
from app.utilities.app_access_login_required import login_required
from app.utilities.app_access_role_required import role_required
from app.utilities.app_logging_helper import log_with_route
from app.models import db, Organisations, Groups

# Create the blueprint
csv_import_bp = Blueprint('csv_import_bp', __name__)

@csv_import_bp.route('/tenant/import', methods=['GET', 'POST'])
@login_required
@role_required(['admin', 'master'])
def csv_import():
    """Handle CSV upload and preview"""
    form = CsvImportForm()
    
    if request.method == 'GET':
        return render_template('tenant/csv_import.html', form=form, step=1)
    
    if form.validate_on_submit():
        # Read the CSV file
        csv_file = request.files['csv_file']
        stream = io.StringIO(csv_file.stream.read().decode("UTF8"), newline=None)
        
        try:
            csv_data = list(csv.reader(stream))
            headers = csv_data[0]
            rows = csv_data[1:]  # Skip header row
            
            # Check if the CSV file has the required columns
            required_columns = ['orgname', 'groupname']
            missing_columns = [col for col in required_columns if col.lower() not in [h.lower() for h in headers]]
            
            if missing_columns:
                flash(f"CSV file is missing required columns: {', '.join(missing_columns)}", 'error')
                return render_template('tenant/csv_import.html', form=form, step=1)
            
            # Map headers to indices
            column_indices = {headers[i].lower(): i for i in range(len(headers))}
            
            # Extract data
            preview_data = []
            for row in rows:
                if len(row) >= 2:  # Check if row has at least the required fields
                    org_name = row[column_indices['orgname']]
                    group_name = row[column_indices['groupname']]
                    
                    # Skip empty rows
                    if not org_name.strip() or not group_name.strip():
                        continue
                    
                    preview_data.append({
                        'orgname': org_name,
                        'groupname': group_name
                    })
            
            # Store the data in session for later processing
            session['csv_import_data'] = preview_data
            
            # If no valid data was found
            if not preview_data:
                flash('No valid data found in the CSV file', 'error')
                return render_template('tenant/csv_import.html', form=form, step=1)
            
            return render_template('tenant/csv_import.html', step=2, preview_data=preview_data)
        
        except Exception as e:
            log_with_route(logging.ERROR, f"Error processing CSV file: {str(e)}", exc_info=True)
            flash(f'Error processing CSV file: {str(e)}', 'error')
            return render_template('tenant/csv_import.html', form=form, step=1)
    
    # If form validation failed
    return render_template('tenant/csv_import.html', form=form, step=1)


@csv_import_bp.route('/tenant/csv_import/confirm', methods=['POST'])
@login_required
@role_required(['admin', 'master'])
def confirm_import():
    """Handle confirmation and execute the import"""
    
    # Get the data from session
    import_data = session.get('csv_import_data')
    
    if not import_data:
        flash('No import data found', 'error')
        return redirect(url_for('csv_import_bp.csv_import'))
    
    tenant_uuid = session.get('tenant_uuid')
    if not tenant_uuid:
        flash('Tenant UUID is required', 'error')
        return redirect(url_for('csv_import_bp.csv_import'))
    
    # Track statistics for the import
    stats = {
        'orgs_created': 0,
        'groups_created': 0,
        'orgs_skipped': 0,
        'errors': 0
    }
    
    # Group data by organization name
    org_groups = {}
    for item in import_data:
        org_name = item['orgname']
        group_name = item['groupname']
        
        if org_name not in org_groups:
            org_groups[org_name] = []
        
        org_groups[org_name].append(group_name)
    
    try:
        # Process each organization and its groups
        for org_name, group_names in org_groups.items():
            # Check if organization already exists
            existing_org = Organisations.query.filter_by(
                orgname=org_name, 
                tenantuuid=tenant_uuid
            ).first()
            
            if existing_org:
                stats['orgs_skipped'] += 1
                org_uuid = existing_org.orguuid
            else:
                # Create new organization
                new_org = Organisations(
                    orguuid=str(uuid.uuid4()),
                    orgname=org_name,
                    tenantuuid=tenant_uuid
                )
                db.session.add(new_org)
                db.session.flush()  # Flush to get the new org's UUID
                org_uuid = new_org.orguuid
                stats['orgs_created'] += 1
            
            # Create groups for this organization
            for group_name in group_names:
                # Check if group already exists in this organization
                existing_group = Groups.query.filter_by(
                    groupname=group_name,
                    orguuid=org_uuid
                ).first()
                
                if not existing_group:
                    try:
                        new_group = Groups(
                            groupuuid=str(uuid.uuid4()),
                            groupname=group_name,
                            orguuid=org_uuid,
                            tenantuuid=tenant_uuid,
                            created_at=int(time.time()),
                            health_score=None
                        )
                        db.session.add(new_group)
                        stats['groups_created'] += 1
                    except Exception as e:
                        log_with_route(logging.ERROR, f"Error creating group '{group_name}': {str(e)}", exc_info=True)
                        # Continue with the next group without failing the entire import
                        continue
        
        db.session.commit()
        log_with_route(logging.INFO, f"CSV import completed: {stats}")
        
        # Clear the session data
        if 'csv_import_data' in session:
            del session['csv_import_data']
        
        flash(f"Import completed: {stats['orgs_created']} organizations and {stats['groups_created']} groups created. {stats['orgs_skipped']} organizations skipped.", 'success')
        
    except Exception as e:
        db.session.rollback()
        stats['errors'] += 1
        log_with_route(logging.ERROR, f"Error during CSV import: {str(e)}", exc_info=True)
        flash(f'Error during import: {str(e)}', 'error')
    
    return render_template('tenant/csv_import.html', step=3, stats=stats)


@csv_import_bp.route('/tenant/csv_import/template')
@login_required
def download_template():
    """Provide a CSV template for users to download"""
    template_path = os.path.join(current_app.root_path, 'static', 'templates', 'org_group_template.csv')
    
    # Read the template file
    try:
        with open(template_path, 'r') as file:
            template_content = file.read()
    except Exception as e:
        log_with_route(logging.ERROR, f"Error reading template file: {str(e)}", exc_info=True)
        # Fallback to hardcoded template if file can't be read
        template_content = "orgname,groupname\nIT Solutions Corp,IT Support\nIT Solutions Corp,Development Team\nIT Solutions Corp,Management\nAcme Inc,Marketing"
    
    response = jsonify({
        'csv_content': template_content
    })
    
    return response
