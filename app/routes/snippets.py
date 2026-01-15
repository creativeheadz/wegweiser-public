# Filepath: app/routes/snippets.py
from flask import Blueprint, request, jsonify, current_app, session
from logzero import logger, logfile
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy import and_, update, true, false
import json
import os
import time
from random import randrange
import shutil
import uuid
from app.models import db, Snippets, SnippetsSchedule, SnippetsHistory, DeviceStatus
import requests
from flask_wtf.csrf import CSRFProtect
from app import csrf
from datetime import datetime

payload_bp = Blueprint('snippets_bp', __name__)
serverAddr = 'https://app.wegweiser.tech'

################## pendingsnippets ##################
@payload_bp.route('/snippets/pendingsnippets/<deviceuuid>', methods=['GET'])
def returnPendingSnippets(deviceuuid):
    from logzero import logger, logfile

    # Get the root directory of the Flask project
    project_root = os.path.dirname(current_app.root_path)
    logsDir = os.path.join(project_root, 'logs')
    logFile = os.path.join(logsDir, 'snippets.pendingsnippets.log')

    checkDir(logsDir)

    if not deviceuuid:
        return jsonify({'status': 'error', 'data': 'DeviceUUID is required'}), 500

    # Update device last_update timestamp
    updateLastUpdateSql = (
        update(DeviceStatus)
        .where(DeviceStatus.deviceuuid == deviceuuid)
        .values(
            last_update=int(time.time()),
        )
    )
    try:
        db.session.execute(updateLastUpdateSql)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        return jsonify({"status": "error", "data": 'Failed to check in(1)'}), 500

    current_time = int(time.time())
    try:
        # First, reset any stale executions
        reset_stale_sql = (
            update(SnippetsSchedule)
            .where(and_(
                SnippetsSchedule.deviceuuid == deviceuuid,
                SnippetsSchedule.inprogress == true(),
                SnippetsSchedule.lastexecution != None,
                current_time - SnippetsSchedule.lastexecution > Snippets.max_exec_secs
            ))
            .values(
                inprogress=false(),
                lastexecstatus='TIMEOUT',
                nextexecution=current_time
            )
        )
        db.session.execute(reset_stale_sql)
        db.session.commit()

        # Then atomically claim pending schedules by setting inprogress=true and returning the claimed IDs
        claim_stmt = (
            update(SnippetsSchedule)
            .where(and_(
                SnippetsSchedule.deviceuuid == deviceuuid,
                SnippetsSchedule.nextexecution <= current_time,
                SnippetsSchedule.enabled.is_(true()),
                SnippetsSchedule.inprogress.isnot(true())
            ))
            .values(
                inprogress=true(),
                lastexecution=current_time
            )
            .returning(SnippetsSchedule.scheduleuuid)
        )
        result = db.session.execute(claim_stmt)
        db.session.commit()
        schedules = result.fetchall()
    except Exception as e:
        db.session.rollback()
        return jsonify({"status": "error", "data": f'Failed to query snippets: {str(e)}'}), 500

    scheduleDict = {}
    scheduleList = [str(row[0]) for row in schedules]
    scheduleDict['scheduleList'] = scheduleList

    return jsonify({'status': 'success', 'data': scheduleDict}), 200

@payload_bp.route('/snippets/deleteschedule/<scheduleuuid>', methods=['GET'])
@csrf.exempt  # Only use this if you intentionally want to bypass CSRF for this route
def deleteSchedule(scheduleuuid):
    from logzero import logger, logfile

    # Get the root directory of the Flask project
    project_root = os.path.dirname(current_app.root_path)
    logsDir = os.path.join(project_root, 'logs')
    logFile = os.path.join(logsDir, 'snippets.schedulesnippet.log')
    checkDir(logsDir)

    # logfile(logFile)
    # logger.info(f'/snippets/deleteschedule/<scheduleuuid> begins...')
    # logger.debug(f'scheduleuuid: {scheduleuuid}')

    if not scheduleuuid:
        return jsonify({'status': 'error', 'data': 'scheduleuuid is required'}), 500

    existing_row = SnippetsSchedule.query.filter(
        SnippetsSchedule.scheduleuuid == scheduleuuid).first()

    if existing_row:
        # logger.debug(f'Found existing row for scheduleuuid: {scheduleuuid}')
        db.session.delete(existing_row)
        db.session.commit()
        return (jsonify({'status': 'success', 'data': 'schedule deleted'}), 200)
    else:
        return (jsonify({'status': 'success', 'data': 'schedule did not exist'}), 201)

@payload_bp.route('/snippets/getsnippetfromscheduleuuid/<scheduleuuid>', methods=['GET'])
@csrf.exempt  # Only use this if you intentionally want to bypass CSRF for this route
def returnSnippet(scheduleuuid):
    from logzero import logger, logfile

    # Get the root directory of the Flask project
    project_root = os.path.dirname(current_app.root_path)
    logsDir = os.path.join(project_root, 'logs')
    logFile = os.path.join(logsDir, 'snippets.getsnippetfromscheduleuuid.log')

    checkDir(logsDir)

    # logfile(logFile)
    # logger.info(f'/snippets/getsnippetfromscheduleuuid/{scheduleuuid} begins...')
    # logger.debug(f'scheduleuuid: {scheduleuuid}')
    if not scheduleuuid:
        return jsonify({'status': 'error', 'data': 'scheduleuuid is required'}), 500
    try:
        snippetDetails = db.session.query(
            SnippetsSchedule.snippetuuid,
            Snippets.tenantuuid,
            Snippets.snippetname,
            SnippetsSchedule.parameters).join(
            Snippets, SnippetsSchedule.snippetuuid == Snippets.snippetuuid
        ).filter(
            and_(
                SnippetsSchedule.scheduleuuid == scheduleuuid,
                SnippetsSchedule.nextexecution <= int(time.time())
            )
        ).all()
        # logger.debug(f'snippetDetails: {snippetDetails}')

        snippetUuid = str(snippetDetails[0][0])
        tenantUuid = str(snippetDetails[0][1])
        parameters = snippetDetails[0][3]  # Get parameters from schedule

        snippetFilePath = os.path.join(project_root, 'snippets', tenantUuid, snippetUuid + '.json')
        # logger.debug(f'snippetUuid: {snippetUuid}')
        # logger.debug(f'tenantUuid: {tenantUuid}')
        # logger.debug(f'snippetFilePath: {snippetFilePath}')
        with open(snippetFilePath, 'r') as f:
            data = json.load(f)

        # Add parameters to response if they exist
        if parameters:
            data['parameters'] = parameters

        return jsonify({'status': 'success', 'data': data}), 200
    except Exception as e:
        # logger.error(f'Failed to get schedules. Reason: {e}')
        return jsonify({'status': 'error', 'data': str(e)}), 500

@payload_bp.route('/snippets/sendscheduleresult/<scheduleuuid>', methods=['POST'])
@csrf.exempt  # Only use this if you intentionally want to bypass CSRF for this route
def updateScheduleResults(scheduleuuid):
    from logzero import logger, logfile

    # Get the root directory of the Flask project
    project_root = os.path.dirname(current_app.root_path)
    logsDir = os.path.join(project_root, 'logs')
    logFile = os.path.join(logsDir, 'snippets.sendscheduleresult.log')

    checkDir(logsDir)

    # logfile(logFile)
    # logger.info(f'/snippets/sendscheduleresult/<{scheduleuuid}> begins...')
    # logger.debug(f'scheduleuuid: {scheduleuuid}')
    if not scheduleuuid:
        return jsonify({'status': 'error', 'data': 'scheduleuuid is required'}), 500
    data = request.get_json()
    execStatus = data['execstatus']
    try:
        updateSnippetSchedule(scheduleuuid, execStatus)
    except Exception as e:
        # logger.error(f'Failed to get update snippet schedules. Reason: {e}')
        return (jsonify({'status': 'error', 'data': 'Failed to get update snippet schedules'}), 500)
    try:
        updateSnippetHistory(scheduleuuid, execStatus)
    except Exception as e:
        # logger.error(f'Failed to insert snippet history. Reason: {e}')
        return (jsonify({'status': 'error', 'data': 'Failed to insert snippet history'}), 500)
    return jsonify({'status': 'success', 'data': scheduleuuid}), 200

@payload_bp.route('/snippets/schedulesnippet/', methods=['POST'])
@csrf.exempt  # Only use this if you intentionally want to bypass CSRF for this route
def scheduleSnippet():
    from logzero import logger, logfile
    from datetime import datetime, timedelta

    # Get the root directory of the Flask project
    project_root = os.path.dirname(current_app.root_path)
    logsDir = os.path.join(project_root, 'logs')
    logFile = os.path.join(logsDir, 'snippets.schedulesnippet.log')
    checkDir(logsDir)

    # logfile(logFile)
    # logger.info(f'/snippets/schedulesnippet/ begins...')
    data = request.get_json()
    deviceUuid = data['deviceuuid']
    snippetUuid = data['snippetuuid']
    recString = data['recstring']
    startTime = data['starttime']

    try:
        upsertSnippetSchedule(deviceUuid, snippetUuid, recString, startTime)
    except Exception as e:
        # logger.error(f'Failed to upsert snippet schedule. Reason: {e}')
        return (jsonify({'status': 'error', 'data': 'Failed to update snippet schedule'}), 500)
    return (jsonify({'status': 'success', 'data': 'schedule inserted'}), 200)

################## ADDITIONAL FUNCTIONS ##################

def checkDir(dirToCheck):
    if os.path.isdir(dirToCheck):
        # logger.info(f'{dirToCheck} already exists.')
        pass
    else:
        # logger.info(f'{dirToCheck} does not exist. Creating...')
        try:
            os.makedirs(dirToCheck)
            # logger.info(f'{dirToCheck} created.')
        except Exception as e:
            # logger.error(f'Failed to create {dirToCheck}. Reason: {e}')
            pass

def getNextExecution(scheduleUuid):
    scheduleDetails = SnippetsSchedule.query.filter_by(scheduleuuid=scheduleUuid).first()
    nextExecOld = scheduleDetails.nextexecution
    recurrence = scheduleDetails.recurrence
    if recurrence == 0:
        removeSchedule = True
        nextExecNew = 0
        return (removeSchedule, nextExecNew)
    else:
        removeSchedule = False
        interval = scheduleDetails.interval
        nextExecNew = nextExecOld
        # logger.debug(f'nextExecOld: {nextExecOld} | recurrence: {recurrence} | interval: {interval} | nextExecNew: {nextExecNew}')
        while nextExecNew < int(time.time()):
            nextExecNew += (recurrence * interval)
        # logger.debug(f'nextExecNew: {nextExecNew}')
        # logger.debug(f'removeSchedule: {removeSchedule}')
        return (removeSchedule, nextExecNew)

def updateSnippetSchedule(scheduleUuid, execStatus):
    # logger.info(f'Attempting to update SnippetSchedule for {scheduleUuid}')
    removeSchedule, nextExecution = getNextExecution(scheduleUuid)
    if removeSchedule == True:
        rowToDelete = (
            SnippetsSchedule.query.filter_by(scheduleuuid=scheduleUuid).first()
        )
        if not rowToDelete:
            # logger.error('No rows found')
            pass
        else:
            try:
                db.session.delete(rowToDelete)
                db.session.commit()
            except Exception as e:
                # logger.error(f'Error updating SnippetSchedule: Reason: {e}')
                # logger.error(f'Rolling back transaction...')
                db.session.rollback()
                # logger.error(f'Transaction rolled back.')
    else:
        updateSnippetScheduleSql = (
            update(SnippetsSchedule)
            .where(SnippetsSchedule.scheduleuuid == scheduleUuid)
            .values(
                nextexecution=nextExecution,
                lastexecution=int(time.time()),
                lastexecstatus=execStatus,
                inprogress=false()
            )
        )
        try:
            db.session.execute(updateSnippetScheduleSql)
            db.session.commit()
            # logger.info('Updating SnippetSchedule processed')
        except Exception as e:
            # logger.error(f'Error updating SnippetSchedule: Reason: {e}')
            # logger.error(f'Rolling back transaction...')
            db.session.rollback()
            # logger.error(f'Transaction rolled back.')

def updateSnippetHistory(scheduleUuid, execStatus):
    # logger.info(f'Attempting to update SnippetHistory for {scheduleUuid}')
    scheduleDetails = SnippetsSchedule.query.filter_by(scheduleuuid=scheduleUuid).first()
    snippetUuid = scheduleDetails.snippetuuid
    deviceUuid = scheduleDetails.deviceuuid

    insertSnippetHistorySql = (
        insert(SnippetsHistory)
        .values(
            historyuuid=uuid.uuid4(),
            scheduleuuid=scheduleUuid,
            snippetuuid=snippetUuid,
            deviceuuid=deviceUuid,
            exectime=int(time.time()),
            execstatus=execStatus
        )
    )
    try:
        db.session.execute(insertSnippetHistorySql)
        db.session.commit()
        # logger.info('Inserting SnippetsHistory processed')
    except Exception as e:
        # logger.error(f'Error inserting SnippetsHistory: Reason: {e}')
        # logger.error(f'Rolling back transaction...')
        db.session.rollback()
        # logger.error(f'Transaction rolled back.')

def deleteSnippetSchedule(snippetScheduleUuid):
    existing_row = SnippetsSchedule.query.filter(
        SnippetsSchedule.snippetscheduleuuid == snippetScheduleUuid).first()

    if existing_row:
        # logger.debug(f'Found existing row for snippetScheduleUuid: {snippetScheduleUuid}')
        db.session.delete(existing_row)
        db.session.commit()
        return (True)
    else:
        return (False)

def upsertSnippetSchedule(deviceUuid, snippetUuid, recString, startTime):
    existing_row = SnippetsSchedule.query.filter(
        and_(SnippetsSchedule.snippetuuid == snippetUuid, SnippetsSchedule.deviceuuid == deviceUuid)
    ).first()

    if existing_row:
        # logger.debug(f'Found existing row for snippetUuid: {snippetUuid} | deviceuuid: {deviceUuid}')
        db.session.delete(existing_row)
        db.session.commit()

    recurrence, interval = recStringToSeconds(recString)
    startTimeEpoch = getEpochTime(startTime)

    newSchedule = SnippetsSchedule(
        scheduleuuid=str(uuid.uuid4()),
        snippetuuid=snippetUuid,
        deviceuuid=deviceUuid,
        recurrence=recurrence,
        interval=interval,
        nextexecution=startTimeEpoch,
        enabled=true()
    )
    db.session.add(newSchedule)
    db.session.commit()

def recStringToSeconds(recString):
    if recString.isdigit():
        if int(recString) == 0:
            recurrence = 0
            interval = 0
    else:
        units = {
            's': 1,
            'm': 60,
            'h': 3600,
            'd': 86400
        }
        try:
            interval = int(''.join(filter(str.isdigit, recString)))
            unit = ''.join(filter(str.isalpha, recString))
        except ValueError:
            raise ValueError(f"Invalid time format: {recString}")
        if unit not in units:
            raise ValueError(f"Unknown time unit: {unit}")
        recurrence = units[unit]
    print(f'recurrence: {recurrence} | interval: {interval}')
    return (recurrence, interval)

def getEpochTime(startTime):
    from datetime import datetime, timedelta
    if startTime == '0':
        startTimeEpoch = int(time.time())
    else:
        now = datetime.now()
        inputTime = datetime.strptime(startTime, "%H:%M").time()
        inputToday = datetime.combine(now.date(), inputTime)
        if inputToday < now:
            inputToday += timedelta(days=1)
        startTimeEpoch = int(inputToday.timestamp())
    return (startTimeEpoch)
