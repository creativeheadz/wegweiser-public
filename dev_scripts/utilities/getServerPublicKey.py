# Filepath: tools/getServerPublicKey.py
from logzero import logger
import requests
import json
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

def getServerPubPem():
	endpoint 		= '/diags/getserverpublickey'
	url 			= f'https://{host}{endpoint}'
	logger.info(f'Attempting to connect to: {url}')
	response 		= requests.get(url)
	logger.debug(f'response: {response.text}')
	serverpublickey	= json.loads(response.text)['serverpublickey']
	logger.debug(f'serverpublickey: {serverpublickey}')
	return(serverpublickey)

def validatePem(pemToValidate):
	jpub = serialization.load_pem_public_key(pemToValidate.encode('utf-8'))
	if isinstance(jpub, rsa.RSAPublicKey):
		logger.info('Valid key')
	else:
		logger.error('Invalid key')

host 			= 'app.wegweiser.tech'
port 			= 443

serverPubPem = getServerPubPem()
validatePem(serverPubPem)

