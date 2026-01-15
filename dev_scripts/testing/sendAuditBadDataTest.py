# Filepath: tools/sendAuditBadDataTest.py
import requests
from logzero import logger
import json
import time

def sendJsonPayloadFlask(payload, endpoint):
	url 		= f'https://{host}{endpoint}'
	headers 	= {'Content-Type': 'application/json'}
	response 	= requests.post(url, headers=headers, data=json.dumps(payload))
	return(response)


host			= 'app.wegweiser.tech'
route 			= '/payload/sendaudit'
payloadBad 		= {'data': {'agent': {'agentUuid': 1, 'serverUuid': 'd07e0394-60a8-4a47-bfdd-9a495137f232', 'systemtime': 1718810148.3345523}, 'system': {'agentPlatform': 'Linux-5.15.0-112-generic-x86_64-with-glibc2.35', 'systemName': 'ginger.longmead.local', 'currentUser': 'john', 'cpuUsage': 2.6, 'cpuCount': 8, 'bootTime': 1718805165.0}, 'drives': [{'name': '/', 'total': 114223820800, 'used': 28786221056, 'free': 79588016128, 'usedPer': 25.20159179966776, 'freePer': 69.67724908042999}], 'networkList': [{'lo': {'ifIsUp': True, 'ifSpeed': 0, 'ifMtu': 65536, 'bytesSent': 1183092, 'bytesRecv': 1183092, 'errIn': 0, 'errOut': 0, 'address4': '127.0.0.1', 'netmask4': '255.0.0.0', 'broadcast4': None, 'address6': '::1', 'netmask6': 'ffff:ffff:ffff:ffff:ffff:ffff:ffff:ffff', 'broadcast6': None}, 'eno1': {'ifIsUp': True, 'ifSpeed': 1000, 'ifMtu': 1500, 'bytesSent': 2157132857, 'bytesRecv': 39107226, 'errIn': 0, 'errOut': 0, 'address4': '192.168.0.11', 'netmask4': '255.255.255.0', 'broadcast4': '192.168.0.255', 'address6': 'fe80::e03e:ec2b:12fe:47f8%eno1', 'netmask6': 'ffff:ffff:ffff:ffff::', 'broadcast6': None}, 'wlp3s0': {'ifIsUp': False, 'ifSpeed': 0, 'ifMtu': 1500, 'bytesSent': 0, 'bytesRecv': 0, 'errIn': 0, 'errOut': 0}, 'ztrta7m2fb': {'ifIsUp': True, 'ifSpeed': 10, 'ifMtu': 2800, 'bytesSent': 0, 'bytesRecv': 201447, 'errIn': 0, 'errOut': 0, 'address4': '192.168.192.20', 'netmask4': '255.255.255.0', 'broadcast4': '192.168.192.255', 'address6': 'fe80::e4f9:aaff:fefc:6420%ztrta7m2fb', 'netmask6': 'ffff:ffff:ffff:ffff::', 'broadcast6': None}}], 'Users': [{0: {'username': 'john', 'terminal': 'tty7', 'host': 'localhost', 'loggedIn': 1718805220.0, 'pid': 1699}}], 'battery': {'installed': True, 'pcCharged': 100.0, 'secsLeft': -2, 'powerPlug': True}, 'partitions': [{'/': {'device': '/dev/mapper/vgmint-root', 'fstype': 'ext4'}, '/boot': {'device': '/dev/sda3', 'fstype': 'ext4'}, '/boot/efi': {'device': '/dev/sda2', 'fstype': 'vfat'}}], 'memory': {'total': 16665350144, 'available': 11073105920, 'used': 4938260480, 'free': 5787746304}}}
payloadGood 	= {'data': {'agent': {'agentUuid': 'd07e0394-60a8-4a47-bfdd-9a495137f232', 'serverUuid': 'd07e0394-60a8-4a47-bfdd-9a495137f232', 'systemtime': 1718810148.3345523}, 'system': {'agentPlatform': 'Linux-5.15.0-112-generic-x86_64-with-glibc2.35', 'systemName': 'ginger.longmead.local', 'currentUser': 'john', 'cpuUsage': 2.6, 'cpuCount': 8, 'bootTime': 1718805165.0}, 'drives': [{'name': '/', 'total': 114223820800, 'used': 28786221056, 'free': 79588016128, 'usedPer': 25.20159179966776, 'freePer': 69.67724908042999}], 'networkList': [{'lo': {'ifIsUp': True, 'ifSpeed': 0, 'ifMtu': 65536, 'bytesSent': 1183092, 'bytesRecv': 1183092, 'errIn': 0, 'errOut': 0, 'address4': '127.0.0.1', 'netmask4': '255.0.0.0', 'broadcast4': None, 'address6': '::1', 'netmask6': 'ffff:ffff:ffff:ffff:ffff:ffff:ffff:ffff', 'broadcast6': None}, 'eno1': {'ifIsUp': True, 'ifSpeed': 1000, 'ifMtu': 1500, 'bytesSent': 2157132857, 'bytesRecv': 39107226, 'errIn': 0, 'errOut': 0, 'address4': '192.168.0.11', 'netmask4': '255.255.255.0', 'broadcast4': '192.168.0.255', 'address6': 'fe80::e03e:ec2b:12fe:47f8%eno1', 'netmask6': 'ffff:ffff:ffff:ffff::', 'broadcast6': None}, 'wlp3s0': {'ifIsUp': False, 'ifSpeed': 0, 'ifMtu': 1500, 'bytesSent': 0, 'bytesRecv': 0, 'errIn': 0, 'errOut': 0}, 'ztrta7m2fb': {'ifIsUp': True, 'ifSpeed': 10, 'ifMtu': 2800, 'bytesSent': 0, 'bytesRecv': 201447, 'errIn': 0, 'errOut': 0, 'address4': '192.168.192.20', 'netmask4': '255.255.255.0', 'broadcast4': '192.168.192.255', 'address6': 'fe80::e4f9:aaff:fefc:6420%ztrta7m2fb', 'netmask6': 'ffff:ffff:ffff:ffff::', 'broadcast6': None}}], 'Users': [{0: {'username': 'john', 'terminal': 'tty7', 'host': 'localhost', 'loggedIn': 1718805220.0, 'pid': 1699}}], 'battery': {'installed': True, 'pcCharged': 100.0, 'secsLeft': -2, 'powerPlug': True}, 'partitions': [{'/': {'device': '/dev/mapper/vgmint-root', 'fstype': 'ext4'}, '/boot': {'device': '/dev/sda3', 'fstype': 'ext4'}, '/boot/efi': {'device': '/dev/sda2', 'fstype': 'vfat'}}], 'memory': {'total': 16665350144, 'available': 11073105920, 'used': 4938260480, 'free': 5787746304}}}



response 	= sendJsonPayloadFlask(payloadBad, route)
print(f'We should get a response.status_code = 500 here as the payload is valid JSON, but invalid data type on the agentUuid')
print(f'response.status_code: {response.status_code}')
if response.status_code == 500:
	print('Test SUCCESS')
else:
	print('Test FAIL')

response 	= sendJsonPayloadFlask(payloadGood, route)
print(f'We should get a response.status_code = 200 here as the payload is valid JSON, and has valid data types')
print(f'response.status_code: {response.status_code}')
if response.status_code == 200:
	print('Test SUCCESS')
else:
	print('Test FAIL')	

