# Filepath: snippets/unSigned/resetEvents.py
import platform
import os
from logzero import logger

################# FUNCTIONS #################

def removeEvents():
	logger.info('Resetting event logs...')
	filesToDel = [f'{configDir}latestEvt-Application.txt',
				f'{configDir}latestEvt-Security.txt',
				f'{configDir}latestEvt-System.txt',
				f'{filesDir}events-Application.json',
				f'{filesDir}events-Security.json',
				f'{filesDir}events-System.json',
				f'{filesDir}eventsFiltered-Application.json',
				f'{filesDir}eventsFiltered-Security.json',
				f'{filesDir}eventsFiltered-System.json'
				]
	for fileToDel in filesToDel:
		logger.info(f'Attempting to delete {fileToDel}...')
		if os.path.exists(fileToDel):
			try:
				os.remove(fileToDel)
				logger.info(f'Successfully deleted {fileToDel}...')
			except Exception as e:
				logger.error(f'Failed to delete {fileToDel}')
		else:
			logger.info(f'{fileToDel} does not exist. Skipped.')

def getAppDirs():
	if platform.system() == 'Windows':
		appDir 		= 'c:\\program files (x86)\\Wegweiser\\'
	else:
		appDir 		= '/opt/Wegweiser/'
	logDir 		= os.path.join(appDir, 'Logs', '')
	configDir 	= os.path.join(appDir, 'Config', '')
	tempDir 	= os.path.join(appDir, 'Temp', '')
	filesDir	= os.path.join(appDir, 'Files' , '')
	checkDirs([appDir, logDir, configDir, tempDir, filesDir])
	return(appDir, logDir, configDir, tempDir, filesDir)

def checkDirs(dirsToCheck):
	for dirToCheck in dirsToCheck:
		dirToCheck = os.path.join(dirToCheck, '')
		if not os.path.isdir(dirToCheck):
			logger.info(f'{dirToCheck} does not exist. Creating...')
			try:
				os.makedirs(dirToCheck)
				logger.info(f'{dirToCheck} created.')
			except Exception as e:
				logger.error(f'Failed to create {dirToCheck}. Reason: {e}')
				sys.exit()

################# MAIN #################

appDir, \
logDir, \
configDir, \
tempDir, \
filesDir        = getAppDirs()

if platform.system() == 'Windows':
    removeEvents()
else:
    logger.info(f'RESETEVENTS is not valid for this OS ({platform.system()}).')

logger.info('Done.')