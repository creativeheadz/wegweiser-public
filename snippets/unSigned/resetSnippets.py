# Filepath: snippets/unSigned/resetSnippets.py
# Filepath: snippets/unSigned/resetEvents.py
import platform
import os
from logzero import logger

################# FUNCTIONS #################

def removeSnippets():
	for file in os.listdir(snippetsDir):
		if file.endswith('.json'):
			fileToDel = os.path.join(snippetsDir, file)
			logger.info(f'Attempting to delete {file}...')
			try:
				os.remove(fileToDel)
				logger.info(f'Successfully deleted {file}')
			except Exception as e:
				logger.error(f'Failed to delete {file}. Reason: {e}')

def getAppDirs():
	if platform.system() == 'Windows':
		appDir 		= 'c:\\program files (x86)\\Wegweiser\\'
	else:
		appDir 		= '/opt/Wegweiser/'
	logDir 		= os.path.join(appDir, 'Logs', '')
	configDir 	= os.path.join(appDir, 'Config', '')
	tempDir 	= os.path.join(appDir, 'Temp', '')
	filesDir	= os.path.join(appDir, 'Files' , '')
	snippetsDir = os.path.join(appDir, 'Snippets', '')
	checkDirs([appDir, logDir, configDir, tempDir, filesDir, snippetsDir])
	return(appDir, logDir, configDir, tempDir, filesDir, snippetsDir)

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
filesDir, \
snippetsDir        = getAppDirs()

removeSnippets()

logger.info('Done.')