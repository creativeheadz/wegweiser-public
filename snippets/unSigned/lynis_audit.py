# Filepath: snippets/unSigned/lynis_audit.py
# Lynis Security Audit Script for Wegweiser
# This script downloads Lynis from official GitHub repo and runs a security audit
# Platform: Linux, macOS
# metalogos_type: lynis-audit

import os
import sys
import json
import platform
import subprocess
import time
from logzero import logger

try:
	import requests
except Exception as e:
	subprocess.check_call([sys.executable, '-m', 'pip', 'install', 'requests'])
	import requests


################# FUNCTIONS #################

def getAppDirs():
	"""Get application directories based on OS"""
	if platform.system() == 'Windows':
		appDir = 'c:\\program files (x86)\\Wegweiser\\'
	else:
		appDir = '/opt/Wegweiser/'
	logDir = os.path.join(appDir, 'Logs', '')
	configDir = os.path.join(appDir, 'Config', '')
	filesDir = os.path.join(appDir, 'files', '')
	scriptsDir = os.path.join(appDir, 'Scripts', '')
	tempDir = os.path.join(appDir, 'Temp', '')
	lynisDir = os.path.join(appDir, 'lynis', '')
	return appDir, logDir, configDir, tempDir, filesDir, scriptsDir, lynisDir

def checkDirs(dirsToCheck):
	"""Create directories if they don't exist"""
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

def getDeviceUuid():
	"""Read device UUID and server address from config"""
	appDir, logDir, configDir, tempDir, filesDir, scriptsDir, lynisDir = getAppDirs()
	with open(os.path.join(configDir, 'agent.config')) as f:
		agentConfigDict = json.load(f)
	deviceUuid = agentConfigDict['deviceuuid']
	if 'serverAddr' in agentConfigDict:
		host = agentConfigDict['serverAddr']
	else:
		host = 'app.wegweiser.tech'
	return deviceUuid, host

def check_os_compatibility():
	"""Check if OS is compatible with Lynis"""
	os_name = platform.system()
	if os_name not in ['Linux', 'Darwin']:  # Darwin = macOS
		logger.error(f"Lynis is not compatible with {os_name}")
		return False
	return True

def install_lynis(lynisDir):
	"""Download and install Lynis from official GitHub repository"""
	# Check if Lynis already exists
	lynis_binary = os.path.join(lynisDir, 'lynis')
	if os.path.exists(lynis_binary):
		logger.info("Lynis already installed, checking for updates...")
		try:
			# Update existing installation
			result = subprocess.run(
				['git', '-C', lynisDir, 'pull'],
				capture_output=True,
				text=True,
				timeout=60
			)
			if result.returncode == 0:
				logger.info("Lynis updated successfully")
				return True
			else:
				logger.warning("Failed to update Lynis, will use existing version")
				return True
		except Exception as e:
			logger.warning(f"Could not update Lynis: {e}, using existing version")
			return True

	# Install fresh copy
	logger.info("Installing Lynis from official GitHub repository...")
	try:
		# Ensure parent directory exists
		appDir = os.path.dirname(lynisDir.rstrip('/'))
		os.makedirs(appDir, mode=0o755, exist_ok=True)

		# Clone from official repository
		result = subprocess.run(
			['git', 'clone', 'https://github.com/CISOfy/lynis.git', lynisDir],
			capture_output=True,
			text=True,
			timeout=120
		)

		if result.returncode == 0:
			logger.info("Lynis installed successfully")
			return True
		else:
			logger.error(f"Failed to install Lynis: {result.stderr}")
			return False

	except subprocess.TimeoutExpired:
		logger.error("Lynis installation timed out")
		return False
	except Exception as e:
		logger.error(f"Error installing Lynis: {e}")
		return False

def run_lynis_audit(lynisDir):
	"""Run Lynis security audit and return results"""
	lynis_binary = './lynis'  # Use relative path since we'll run from lynisDir
	lynis_full_path = os.path.join(lynisDir, 'lynis')

	if not os.path.exists(lynis_full_path):
		logger.error("Lynis binary not found")
		return None

	logger.info("Running Lynis security audit...")

	try:
		# Run Lynis audit from its own directory (required for Lynis to find include files)
		# --quiet: Less verbose output
		# --quick: Skip wait for user input
		# --auditor "Wegweiser": Tag the audit
		result = subprocess.run(
			[lynis_binary, 'audit', 'system', '--quiet', '--quick', '--auditor', 'Wegweiser'],
			capture_output=True,
			text=True,
			cwd=lynisDir,  # Run from Lynis directory
			timeout=300  # 5 minutes max
		)

		if result.returncode not in [0, 1]:  # Lynis returns 1 if warnings found (normal)
			logger.error(f"Lynis audit failed: {result.stderr}")
			return None

		# Parse the log file for results
		log_file = '/var/log/lynis.log'
		report_file = '/var/log/lynis-report.dat'

		audit_results = {
			'status': 'completed',
			'timestamp': int(time.time()),
			'os': platform.system(),
			'os_version': platform.release(),
			'hostname': platform.node(),
			'lynis_version': None,
			'hardening_index': None,
			'tests_performed': 0,
			'warnings': [],
			'suggestions': [],
			'findings': {},
			'raw_output': result.stdout
		}

		# Parse report file if it exists
		if os.path.exists(report_file):
			with open(report_file, 'r') as f:
				for line in f:
					line = line.strip()
					if not line or line.startswith('#'):
						continue

					if '=' in line:
						key, value = line.split('=', 1)
						key = key.strip()
						value = value.strip()

						# Extract key information
						if key == 'lynis_version':
							audit_results['lynis_version'] = value
						elif key == 'hardening_index':
							try:
								audit_results['hardening_index'] = int(value)
							except ValueError:
								pass
						elif key == 'tests_performed':
							try:
								audit_results['tests_performed'] = int(value)
							except ValueError:
								pass
						elif key.startswith('warning['):
							audit_results['warnings'].append(value)
						elif key.startswith('suggestion['):
							audit_results['suggestions'].append(value)
						else:
							# Store other findings
							if key not in audit_results['findings']:
								audit_results['findings'][key] = []
							audit_results['findings'][key].append(value)

		# Parse log file for additional details
		if os.path.exists(log_file):
			try:
				with open(log_file, 'r') as f:
					log_content = f.read()
					audit_results['log_excerpt'] = log_content[-5000:]  # Last 5000 chars
			except Exception as e:
				logger.warning(f"Could not read log file: {e}")

		logger.info(f"Lynis audit completed. Hardening Index: {audit_results.get('hardening_index', 'N/A')}")
		logger.info(f"Tests performed: {audit_results['tests_performed']}")
		logger.info(f"Warnings: {len(audit_results['warnings'])}")
		logger.info(f"Suggestions: {len(audit_results['suggestions'])}")

		return audit_results

	except subprocess.TimeoutExpired:
		logger.error("Lynis audit timed out after 5 minutes")
		return None
	except Exception as e:
		logger.error(f"Error running Lynis audit: {e}")
		return None

def send_to_wegweiser(deviceUuid, host, audit_data):
	"""Send audit results to Wegweiser server via new Lynis ingest endpoint"""
	# New endpoint expects: {'results': {...lynis json...}}
	body = {
		'results': audit_data  # audit_data is already JSON (dict)
	}

	# Use new Lynis-specific ingest endpoint
	url = f'https://{host}/devices/{deviceUuid}/lynis/ingest'
	headers = {'Content-Type': 'application/json'}

	try:
		response = requests.post(url, headers=headers, data=json.dumps(body), timeout=30)
		if response.status_code == 202:  # New endpoint returns 202 Accepted (async processing)
			logger.info("Lynis audit data sent successfully to Wegweiser")
			logger.info(f"Server response: {response.json()}")
			return True
		elif response.status_code == 403:
			logger.warning("Lynis audits are not enabled for this tenant")
			logger.warning("Enable in Settings > Analysis Settings > Security Audits")
			return False
		else:
			logger.error(f"Failed to send data: HTTP {response.status_code} - {response.text}")
			return False
	except Exception as e:
		logger.error(f"Error sending data to Wegweiser: {e}")
		return False

################# MAIN #################

try:
	# Get app directories
	appDir, logDir, configDir, tempDir, filesDir, scriptsDir, lynisDir = getAppDirs()
	checkDirs([appDir, logDir, configDir, tempDir, filesDir, scriptsDir, lynisDir])

	# Check OS compatibility
	if not check_os_compatibility():
		logger.error("This script requires Linux or macOS")
		print("ERROR: Lynis is only compatible with Linux and macOS systems")
		sys.exit(1)

	# Get device configuration
	deviceUuid, host = getDeviceUuid()
	logger.info(f"Device UUID: {deviceUuid}")
	logger.info(f"Wegweiser Host: {host}")

	# Install/Update Lynis
	if not install_lynis(lynisDir):
		logger.error("Failed to install Lynis")
		print("ERROR: Failed to install Lynis from GitHub")
		sys.exit(1)

	# Run security audit
	audit_results = run_lynis_audit(lynisDir)
	if audit_results is None:
		logger.error("Failed to run Lynis audit")
		print("ERROR: Failed to run Lynis audit")
		sys.exit(1)

	# Send audit results directly (as dict, not string)
	# New endpoint handles JSON dict format
	if send_to_wegweiser(deviceUuid, host, audit_results):
		logger.info("Lynis security audit completed successfully")
		print("SUCCESS: Lynis audit completed and sent to Wegweiser")
	else:
		logger.error("Failed to send audit results to Wegweiser")
		print("ERROR: Failed to send audit results to Wegweiser")
		sys.exit(1)

except Exception as e:
	logger.error(f"Fatal error in Lynis audit script: {e}")
	print(f"ERROR: {e}")
	sys.exit(1)
