# Filepath: snippets/unSigned/jwnTest.py
import datetime
import os
import platform

def getTempDir():
    if platform.system() == 'Windows':
        tempDir = 'c:\\temp\\'
    elif platform.system() == 'Linux':
        tempDir = '/tmp/'
    else:
        quit('unknown OS')
    os.makedirs(tempDir, exist_ok=True)
    return(tempDir)


tempDir     = getTempDir()
outFile     = os.path.join(tempDir, 'test.log')

with open(outFile, 'w') as f:
    f.write(f'Test success: {datetime.datetime.now().strftime("%d-%b-%Y %H:%M:%S")}')
