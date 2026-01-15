# Filepath: app/routes/download.py
from flask import Blueprint, current_app, send_from_directory, abort, jsonify
import os
from app.models import db, Devices, Organisations, Groups
from flask_wtf.csrf import CSRFProtect
from app import csrf
from flask import make_response, send_from_directory
from app.utilities.app_logging_helper import log_with_route
import logging

download_bp = Blueprint('download_bp', __name__)

@download_bp.route('/download/<path:filepath>', methods=['GET'])
@csrf.exempt
def download_file_direct(filepath):
    """Serve files from downloads directory, including subdirectories"""
    project_root = os.path.dirname(current_app.root_path)
    downloadDirectory = os.path.join(project_root, 'downloads')
    checkDir(downloadDirectory)

    # Security check: prevent directory traversal
    safe_path = os.path.normpath(filepath)
    if safe_path.startswith('..') or os.path.isabs(safe_path):
        log_with_route(logging.ERROR, f'Invalid file path: {filepath}')
        abort(404)

    log_with_route(logging.INFO, f'Request to download: {downloadDirectory}/{safe_path}...')
    try:
        # Get the directory and filename
        file_dir = os.path.dirname(safe_path)
        filename = os.path.basename(safe_path)

        if file_dir:
            full_dir = os.path.join(downloadDirectory, file_dir)
        else:
            full_dir = downloadDirectory

        log_with_route(logging.INFO, f'Successfully sent: {safe_path}')
        return send_from_directory(full_dir, filename, as_attachment=True)
    except FileNotFoundError:
        log_with_route(logging.ERROR, f'File not found: {safe_path}')
        abort(404)

@download_bp.route('/download/groupuuid/<groupuuid>', methods=['GET'])
def download_file_via_groupuuid(groupuuid):
    project_root = os.path.dirname(current_app.root_path)
    downloadDirectory = os.path.join(project_root, 'downloads')
    checkDir(downloadDirectory)

    log_with_route(logging.INFO, f'Request to download via groupuuid: {groupuuid}...')

    group = Groups.query.filter_by(groupuuid=groupuuid).first()
    if not group:
        log_with_route(logging.ERROR, f'Invalid groupuuid: {groupuuid}. Quitting.')
        return jsonify({'error': 'Group UUID is invalid'}), 400

    try:
        log_with_route(logging.INFO, f'Successfully sent: {filename}')
        return send_from_directory(downloadDirectory, filename, as_attachment=True)
    except FileNotFoundError:
        log_with_route(logging.ERROR, f'File not found. Aborting.')
        abort(404)

@download_bp.route('/installerFiles/<platform>/<path:filepath>', methods=['GET'])
@csrf.exempt
def download_installer_file(platform, filepath):
    """Serve files from installerFiles directory for agent installation"""
    project_root = os.path.dirname(current_app.root_path)
    installer_directory = os.path.join(project_root, 'installerFiles', platform)

    # Security check: ensure platform is valid
    if platform not in ['Windows', 'Linux', 'MacOS']:
        log_with_route(logging.ERROR, f'Invalid platform: {platform}')
        abort(404)

    # Security check: prevent directory traversal
    safe_path = os.path.normpath(filepath)
    if safe_path.startswith('..') or os.path.isabs(safe_path):
        log_with_route(logging.ERROR, f'Invalid file path: {filepath}')
        abort(404)

    log_with_route(logging.INFO, f'Request to download installer file: {platform}/{filepath}')

    try:
        return send_from_directory(installer_directory, safe_path, as_attachment=False)
    except FileNotFoundError:
        log_with_route(logging.ERROR, f'Installer file not found: {platform}/{filepath}')
        abort(404)

####################### HELPER FUNCTIONS #######################

def checkDir(dirToCheck):
    if os.path.isdir(dirToCheck):
        log_with_route(logging.INFO, f'{dirToCheck} already exists.')
    else:
        log_with_route(logging.INFO, f'{dirToCheck} does not exist. Creating...')
        try:
            os.makedirs(dirToCheck)
            log_with_route(logging.INFO, f'{dirToCheck} created.')
        except Exception as e:
            log_with_route(logging.ERROR, f'Failed to create {dirToCheck}. Reason: {e}')