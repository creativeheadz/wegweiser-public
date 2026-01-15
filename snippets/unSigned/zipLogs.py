# Filepath: snippets/unSigned/zipLogs.py
import zipfile
import platform
import datetime
import os
from logzero import logger


def getLogFolder():
	if platform.system() == 'Windows':
		logFolder = 'c:\\program files (x86)\\Wegweiser\\Logs\\'
	else:
		logFolder = '/opt/Wegweiser/Logs/'
	return(logFolder)

def getLogFiles(logFolder):
	logsToZipList= []
	for file in os.listdir(logFolder):
		if file.endswith('.log'):
			logsToZipList.append(os.path.join(logFolder, file))
	return(logsToZipList)

def zipLog(logFolder, logsToZipList):
	currentTime = datetime.datetime.now().strftime('%Y.%m.%d-%H.%M.%S')
	outputZip = os.path.join(logFolder, f'{currentTime}.zip')
	with zipfile.ZipFile(outputZip, 'w', zipfile.ZIP_DEFLATED) as zipf:
		for logToZip in logsToZipList:
			zipf.write(logToZip, arcname=logToZip.split('/')[-1])

def delZippedFiles(logsToZipList):
	for file in logsToZipList:
		logger.info(f'Attempting to clear {file}')
		try:
			with open(file, 'w') as f:
				f.write('Log zipped and cleared')
			logger.info(f'Successfully cleared {file}')
		except Exception as e:
			logger.info(f'Failed to clear {file}. Reason: {e}')
	

logFolder 		= getLogFolder()
logsToZipList	= getLogFiles(logFolder)
try:
	zipLog(logFolder, logsToZipList)
	zipSuccess = True
	logger.info(f'Successully zipped {logsToZipList}')
except Exception as e:
	logger.error(f'Failed to zip logs. Reason: {e}')
	zipSuccess = False

if zipSuccess == True:
	delZippedFiles(logsToZipList)