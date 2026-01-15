# Filepath: agent/genKeys.py
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization
import sys
import os

def genPrivateKey():
	privateKey = rsa.generate_private_key(
		public_exponent=65537,
		key_size=4096
	)
	return(privateKey)

def genPublicKey(privateKey):
	publicKey = privateKey.public_key()
	return(publicKey)

def savePrivateKey(privateKey, privateKeyFile):
	with open(privateKeyFile, 'wb') as privateFile:
		privateFile.write(
			privateKey.private_bytes(
				encoding				=serialization.Encoding.PEM,
				format					=serialization.PrivateFormat.PKCS8,
				encryption_algorithm	=serialization.NoEncryption()
			)
		)

def savePublicKey(publicKey, publicKeyfile):
	with open(publicKeyfile, 'wb') as publicFile:
		publicFile.write(
			publicKey.public_bytes(
				encoding=serialization.Encoding.PEM,
				format=serialization.PublicFormat.SubjectPublicKeyInfo
			)
		)

if len(sys.argv) < 2:
	print('USAGE: genKey.py <dir to save keys in>')	
	sys.exit()
outDir 			= sys.argv[1]
privateKeyFile 	= os.path.join(outDir, 'serverPrivKey.pem')
publicKeyfile	= os.path.join(outDir, 'serverPubKey.pem')
#privateKeyFile 	= '/home/wegweiseruser/wegweiser/includes/serverPrivKey.pem'
#publicKeyfile 		= '/home/wegweiseruser/wegweiser/includes/serverPubKey.pem'

privateKey		= genPrivateKey()
publicKey		= genPublicKey(privateKey)
savePrivateKey(privateKey, privateKeyFile)
savePublicKey(publicKey, publicKeyfile)
