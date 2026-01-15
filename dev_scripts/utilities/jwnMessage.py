# Filepath: tools/jwnMessage.py
def decodeMessage(message, passPhrase, salt, debugMode=False):
	from cryptography.fernet import Fernet
	from cryptography.hazmat.primitives import hashes
	from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
	from cryptography.hazmat.backends import default_backend
	import base64
	from logzero import logger
	passPhrase	= passPhrase.encode('utf-8')
	backend 	= default_backend()
	kdf 		= PBKDF2HMAC(
					algorithm=hashes.SHA256(),
					length=32,
					salt=salt,
					iterations=200000,
					backend=backend
					)
	key 		= base64.urlsafe_b64encode(kdf.derive(passPhrase))
	if debugMode == True:
		logger.debug(f'key: {key.decode()}')
	f = Fernet(key)
	try:
		decryptedMessage = f.decrypt(message).decode()
	except Exception as e:
		logger.error(f'Error decrypting - {e}')
		quit()
	return(decryptedMessage)

def sendNtfyMessage(passPhrase=None, ntfyChannel='Default-fQdwW3BkZdNNHKx5', ntfyMessage='ERROR: No Message.'):
	import base64
	from logzero import logger
	import requests
	import os
	if not passPhrase:
		passPhrase 		= os.environ.get('PASSPHRASE')
	ntfySalt 			= b'yyd67!*MfmE&K^Z@c*ey9DqvBq*QxDDGV8sV7JxtPAYEEpwdY%RVz&SZ9q!JX@yx'
	ntfyServerEnc 		= b'gAAAAABm5D8Azfxhc85IEwYJHEZuR92ISdBYQBBba_c-PTiuFFj4IrIFE-_7lbX6-5CkuYt0MPSJCQBSMxbXavHfbNsK2ZksKLubh9hH8U9PW_Dqvqf7_hk='
	ntfyUserEnc 		= b'gAAAAABm5GAK14OFd0BmdDPbQZYTezdIBAIBbl7ucwemtH3DsdV8Vxgf6kSpGAazjXtTZFJ56XjCfbQjF4INVHKblQTv1PUvp63Xo7zUnFLIPCU1BRbtS3c='
	ntfyPasswordEnc 	= b'gAAAAABm5GA_sfdNU90sgh5OrB6npLceUMm86vGURIOq2YyUELnwO4xo4yqvWC0byVEN__it9k5gR8Owh_Nrpg6SVQkE7aar6aimR_78xddXQzYb1FRo-umXj_kHLqjdxCwjQZ4ckSs0'
	ntfyServer			= decodeMessage(ntfyServerEnc, passPhrase, ntfySalt)
	ntfyUser			= decodeMessage(ntfyUserEnc, passPhrase, ntfySalt)
	ntfyPassword		= decodeMessage(ntfyPasswordEnc, passPhrase, ntfySalt)

	b64Auth     		= base64.b64encode(f'{ntfyUser}:{ntfyPassword}'.encode("utf-8")).decode()
	headers 			= {"Authorization": "Basic " + b64Auth}
	url 				= f'{ntfyServer}{ntfyChannel}'
	logger.info(f'Sending message to: {url}')

	try:
		r       = requests.post(url, data=ntfyMessage, headers=headers)
		logger.info(f'Successfully sent message to {url}')
	except Exception as e:
		logger.error(f'Failed to send message to {url}. Reason: {e}')