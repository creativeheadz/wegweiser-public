# Filepath: tools/spaceMonitor.py
import shutil
import os
import jwnMessage

def checkDiskSpace(threshold=5):
	total, used, free = shutil.disk_usage('/')
	freePer            = (free / total) * 100

	body = 'app.wegweiser.tech\n'


	body += f"Total space: {total // (2**20)} MB\n"
	body += f"Used space: {used // (2**20)} MB\n"
	body += f"Free space: {free // (2**20)} MB ({freePer:.2f}% free)\n"

	if freePer < threshold:
		body+= f"Warning: Free space is below {threshold}%!"
	else:
		body += (f"Free space is sufficient.")
	print(body)
	return(body)

body	= checkDiskSpace()
#jwnMessage.sendNtfyMessage(passPhrase='9Palo)pad', ntfyChannel='Monitoring-do4mwtWcUyv374CL', ntfyMessage=body)
