# Filepath: app/routes/tags.py
from flask import Blueprint, request, jsonify, current_app, session
import time
from random import randrange
import os
from app.models import db, ServerCore, Tags, Devices, TagsXDevices, Tenants
from app.utilities.app_access_login_required import login_required
import uuid
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.exc import IntegrityError
import json
from app.utilities.app_logging_helper import log_with_route
import logging
from dotenv import load_dotenv
from flask_wtf.csrf import CSRFProtect
from app import csrf

load_dotenv()

diags_bp = Blueprint('tags_bp', __name__)
@diags_bp.route('/tags/create', methods=['POST'])
@csrf.exempt
def createTag():
    log_with_route(logging.INFO, 'Received /tags/create')

    data = request.get_json()
    tagvalue = data.get('tagvalue')
    tenantuuid = data.get('tenantuuid')

    if not tenantuuid:
        log_with_route(logging.ERROR, 'No tenantuuid specified. Quitting.')
        return jsonify({'status': 'error', 'data': 'tenantuuid is required'}), 400

    if not tagvalue:
        log_with_route(logging.ERROR, 'No tagvalue specified. Quitting.')
        return jsonify({'status': 'error', 'data': 'tagvalue is required'}), 400

    # Check if the tag already exists
    tag = Tags.query.filter_by(tagvalue=tagvalue, tenantuuid=tenantuuid).first()
    if not tag:
        # Create the new tag
        taguuid = str(uuid.uuid4())
        insertNewTagSql = insert(Tags).values(
            taguuid=taguuid,
            tenantuuid=tenantuuid,
            tagvalue=tagvalue,
            created_at=int(time.time())
        )
        try:
            db.session.execute(insertNewTagSql)
            db.session.commit()
            log_with_route(logging.INFO, 'New tag inserted successfully.')
        except IntegrityError as e:
            db.session.rollback()
            if 'duplicate key value violates unique constraint' in str(e.orig):
                log_with_route(logging.ERROR, f'tagvalue {tagvalue} already exists for tenantuuid {tenantuuid}.')
                return jsonify({'status': 'error', 'data': f'tagvalue {tagvalue} already exists for tenantuuid {tenantuuid}'}), 400
            else:
                log_with_route(logging.ERROR, f'Error inserting new tag: {e}', exc_info=True)
                return jsonify({'status': 'error', 'data': 'Failed to create tag'}), 500
    else:
        taguuid = tag.taguuid

    # Only return the taguuid, do not assign to device here
    return jsonify({'status': 'success', 'taguuid': taguuid}), 200


@diags_bp.route('/tags/unassign/device', methods=['DELETE'])
@csrf.exempt
def unassignTag():
    data = request.json
    deviceuuid = data.get('deviceuuid')
    taguuid = data.get('taguuid')
    tagvalue = data.get('tagvalue')
    tenantuuid = session.get('tenant_uuid')

    if not deviceuuid:
        return jsonify({'status': 'error', 'data': 'deviceuuid is required'}), 400

    # If tagvalue is provided, find the corresponding taguuid
    if tagvalue and not taguuid:
        tag = Tags.query.filter_by(tagvalue=tagvalue, tenantuuid=tenantuuid).first()
        if not tag:
            return jsonify({
                'status': 'error',
                'data': f'Tag "{tagvalue}" not found'
            }), 404
        taguuid = tag.taguuid

    if not taguuid:
        return jsonify({'status': 'error', 'data': 'Either taguuid or tagvalue is required'}), 400

    # Check if the association exists
    tag_device = TagsXDevices.query.filter_by(
        taguuid=taguuid,
        deviceuuid=deviceuuid
    ).first()

    if not tag_device:
        return jsonify({
            'status': 'error',
            'data': f'Tag is not assigned to device {deviceuuid}'
        }), 404

    try:
        db.session.delete(tag_device)
        db.session.commit()
        return jsonify({
            'status': 'success',
            'data': f'Tag unassigned from device {deviceuuid}'
        }), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'status': 'error',
            'data': str(e)
        }), 500

@diags_bp.route('/tags/delete', methods=['DELETE'])
@csrf.exempt
def deleteTag():
    log_with_route(logging.INFO, 'Received /tags/delete')

    data = request.get_json()
    taguuid = data.get('taguuid')

    if not taguuid:
        log_with_route(logging.ERROR, 'No taguuid specified. Quitting.')
        return jsonify({'status': 'error', 'data': 'taguuid is required'}), 400

    tag = Tags.query.filter_by(taguuid=taguuid).first()
    if not tag:
        log_with_route(logging.ERROR, f'taguuid {taguuid} does not exist. Quitting.')
        return jsonify({'status': 'error', 'data': f'{taguuid} does not exist'}), 400
    else:
        try:
            Tags.query.filter_by(taguuid=taguuid).delete()
            db.session.commit()
            log_with_route(logging.INFO, f'taguuid: {taguuid} deleted.')
            return jsonify({"status": "success", "data": f'taguuid: {taguuid} deleted.'}), 200
        except Exception as e:
            log_with_route(logging.ERROR, f'Failed to delete taguuid {taguuid}: {e}', exc_info=True)
            db.session.rollback()
            log_with_route(logging.ERROR, 'Transaction rolled back.')
            return jsonify({"status": "error", "data": f'Failed to delete {taguuid}'}), 500

@diags_bp.route('/tags/assign/device', methods=['POST'])
@csrf.exempt
def assignTag():
    log_with_route(logging.INFO, 'Received /tags/assign/device')

    data = request.get_json()
    taguuid = data.get('taguuid')
    deviceuuid = data.get('deviceuuid')

    if not taguuid:
        log_with_route(logging.ERROR, 'No taguuid specified. Quitting.')
        return jsonify({'status': 'error', 'data': 'taguuid is required'}), 400
    if not deviceuuid:
        log_with_route(logging.ERROR, 'No deviceuuid specified. Quitting.')
        return jsonify({'status': 'error', 'data': 'deviceuuid is required'}), 400

    tag = Tags.query.filter_by(taguuid=taguuid).first()
    if not tag:
        log_with_route(logging.ERROR, f'taguuid {taguuid} does not exist. Quitting.')
        return jsonify({'status': 'error', 'data': f'taguuid {taguuid} does not exist'}), 400
    device = Devices.query.filter_by(deviceuuid=deviceuuid).first()
    if not device:
        log_with_route(logging.ERROR, f'deviceuuid {deviceuuid} does not exist. Quitting.')
        return jsonify({'status': 'error', 'data': f'deviceuuid {deviceuuid} does not exist'}), 400

    upsertAssignTagSql = insert(TagsXDevices).values(
        taguuid=taguuid,
        deviceuuid=deviceuuid,
        created_at=int(time.time())
    ).on_conflict_do_update(
        index_elements=['deviceuuid', 'taguuid'],
        set_=dict(
            created_at=int(time.time())
        )
    )
    try:
        db.session.execute(upsertAssignTagSql)
        db.session.commit()
        log_with_route(logging.INFO, f'taguuid: {taguuid} assigned to deviceuuid {deviceuuid}')
        return jsonify({'status': 'success', 'data': f'taguuid: {taguuid} assigned to deviceuuid {deviceuuid}'}), 200
    except Exception as e:
        log_with_route(logging.ERROR, f'Error assigning tag: {e}', exc_info=True)
        db.session.rollback()
        log_with_route(logging.ERROR, 'Transaction rolled back.')
        return jsonify({'status': 'error', 'data': f'Failed to assign {taguuid} to {deviceuuid}'}), 500

@diags_bp.route('/tags/list/bydevice/<deviceuuid>', methods=['GET'])
@csrf.exempt
def getTagByDevice(deviceuuid):
    log_with_route(logging.INFO, f'Received /tags/list/bydevice/{deviceuuid}')

    if not deviceuuid:
        log_with_route(logging.ERROR, 'No deviceuuid specified. Quitting.')
        return jsonify({'status': 'error', 'data': 'deviceuuid is required'}), 500
    try:
        val = uuid.UUID(deviceuuid)
    except ValueError:
        log_with_route(logging.ERROR, 'Invalid deviceuuid format.')
        return jsonify({'status': 'error', 'data': 'Invalid deviceuuid format'}), 500

    validDeviceUuid = Devices.query.filter_by(deviceuuid=deviceuuid).first()
    if not validDeviceUuid:
        log_with_route(logging.ERROR, 'deviceuuid is not valid.')
        return jsonify({'status': 'error', 'data': 'deviceuuid is not valid'}), 500

    tags = TagsXDevices.query.filter_by(deviceuuid=deviceuuid).all()
    tagList = []
    for tag in tags:
        tagvalue = Tags.query.filter_by(taguuid=tag.taguuid).first()
        tagList.append([tag.taguuid, tagvalue.tagvalue])
    log_with_route(logging.DEBUG, f'Tags for device {deviceuuid}: {tagList}')
    return jsonify({'status': 'success', deviceuuid: tagList}), 200

@diags_bp.route('/tags/list/bytenant/<tenantuuid>', methods=['GET'])
@csrf.exempt
def getTagByTenant(tenantuuid):
    log_with_route(logging.INFO, f'Received /tags/list/bytenant/{tenantuuid}')

    if not tenantuuid:
        log_with_route(logging.ERROR, 'No tenantuuid specified. Quitting.')
        return jsonify({'status': 'error', 'data': 'tenantuuid is required'}), 500
    try:
        val = uuid.UUID(tenantuuid)
    except ValueError:
        log_with_route(logging.ERROR, 'Invalid tenantuuid format.')
        return jsonify({'status': 'error', 'data': 'Invalid tenantuuid format'}), 500

    validTenantUuid = Tenants.query.filter_by(tenantuuid=tenantuuid).first()
    if not validTenantUuid:
        log_with_route(logging.ERROR, 'tenantuuid is not valid.')
        return jsonify({'status': 'error', 'data': 'tenantuuid is not valid'}), 400

    tags = Tags.query.filter_by(tenantuuid=tenantuuid).all()
    tagList = []
    for tag in tags:
        tagList.append([tag.taguuid, tag.tagvalue])
    log_with_route(logging.DEBUG, f'Tags for tenant {tenantuuid}: {tagList}')
    return jsonify({'status': 'success', tenantuuid: tagList}), 200

@diags_bp.route('/tags/getvalue/<taguuid>', methods=['GET'])
def getTagValue(taguuid):
    log_with_route(logging.INFO, f'Received /tags/getvalue/{taguuid}')

    if not taguuid:
        log_with_route(logging.ERROR, 'No taguuid specified. Quitting.')
        return jsonify({'status': 'error', 'data': 'taguuid is required'}), 500
    try:
        val = uuid.UUID(taguuid)
    except ValueError:
        log_with_route(logging.ERROR, 'Invalid taguuid format.')
        return jsonify({'status': 'error', 'data': 'Invalid taguuid format'}), 500

    tagvalue = Tags.query.filter_by(taguuid=taguuid).first()
    if not tagvalue:
        log_with_route(logging.ERROR, 'taguuid is not valid.')
        return jsonify({'status': 'error', 'data': 'taguuid is not valid'}), 400

    return jsonify({'status': 'success', taguuid: tagvalue.tagvalue}), 200

@diags_bp.route('/tags/gettags/<deviceuuid>', methods=['GET'])
@login_required
@csrf.exempt
def get_tags_for_device(deviceuuid):
    tenantuuid = session.get('tenant_uuid')

    if not tenantuuid:
        log_with_route(logging.ERROR, 'Tenant UUID not found in session.')
        return jsonify({'error': 'Tenant UUID not found in session'}), 401

    # Query to get all tags assigned to the specific deviceuuid and tenantuuid
    tags = db.session.query(Tags.taguuid, Tags.tagvalue).join(
        TagsXDevices, 
        Tags.taguuid == TagsXDevices.taguuid
    ).filter(
        Tags.tenantuuid == tenantuuid,
        TagsXDevices.deviceuuid == deviceuuid
    ).all()

    # Convert the tags to a list of dictionaries with taguuid and tagvalue
    tags_list = [{'taguuid': tag[0], 'tagvalue': tag[1]} for tag in tags]

    log_with_route(logging.INFO, f'Tags for device {deviceuuid}: {tags_list}')
    return jsonify(tags_list), 200
