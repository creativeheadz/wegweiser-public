# Filepath: tools/testServerSigning.py
import requests
import json
import base64
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding

def getServerPubPem():
	host 			= 'app.wegweiser.tech'
	endpoint 		= '/diags/getserverpublickey'
	url 			= f'https://{host}{endpoint}'
	response 		= requests.get(url)
	serverPubPem	= base64.b64decode(json.loads(response.text)['serverpublickey'])
	print(f'serverPubPem: {serverPubPem}')
	serverPubKey 	= serialization.load_pem_public_key(serverPubPem)
	return(serverPubKey)

def getSignedMessageFromServer():
	endpoint 	= '/diags/testserversigning'
	host 		= 'app.wegweiser.tech'
	url 		= f'https://{host}{endpoint}'
	response 	= requests.get(url)
	return(response.text)

def verifyBase64Signature(responseJson, publicKey):
    payloaddict = json.loads(responseJson)
    payloadb64 = payloaddict['data']['payload']['payloadb64'].encode()
    payloadsigb64 = payloaddict['data']['payload']['payloadsigb64'].encode()

    # Decode the payload and signature
    payload = base64.b64decode(payloadb64)
    payloadsig = base64.b64decode(payloadsigb64)
    
    # Print the decoded payload and signature for debugging
    print(f"Decoded Payload: {payload}")
    print(f"Decoded Signature: {payloadsig}")

    try:
        publicKey.verify(
            payloadsig,
            payload,
            padding.PKCS1v15(),
            hashes.SHA256()
        )
        print('Valid signature')
    except Exception as e:
        print(f'Invalid signature. Reason: {e}')

# Call the functions as before
responseJson = getSignedMessageFromServer()
serverPubPem = getServerPubPem()
verifyBase64Signature(responseJson, serverPubPem)
