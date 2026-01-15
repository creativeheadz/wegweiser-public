#!/bin/bash

if [ "$#" -ne 1 ]; then
    echo "Usage: $0 <groupuuid>"
    exit 1
fi

GROUPUUID=$1

install_venv() {
    echo "Installing python3-venv..."
    sudo apt-get update
    sudo apt-get install -y python3-venv
}

create_venv() {
    echo "Creating virtual environment..."
    python3 -m venv /opt/Wegweiser/venv
    echo "Activating virtual environment..."
#    source /opt/Wegweiser/venv/bin/activate
#    echo "Virtual environment activated."
}

# Define the folder and file
ROOTFOLDER="/opt/Wegweiser"
LOGFOLDER="${ROOTFOLDER}/Logs"
CONFIGFOLDER="${ROOTFOLDER}/Config"
COLLFOLDER="${ROOTFOLDER}/Collector"
FILESFOLDER="${ROOTFOLDER}/Files"
FILE="${COLLFOLDER}/collector.py"
RUNFILE="${COLLFOLDER}/runCollector.sh"
REQFILE="${COLLFOLDER}/requirements.txt"
FULLMESSAGE="# Wegweiser FULLAUDIT (Daily)"
AUDITMESSAGE="# Wegweiser AUDIT (Every 15 minutes)"

HOUR=$((9 + RANDOM % 9))
MINUTE=$((RANDOM % 60))

URL1="https://app.wegweiser.tech/download/collector.py"
URL2="https://app.wegweiser.tech/download/runCollector.sh"
URL3="https://app.wegweiser.tech/download/requirements.txt"

CRONJOBFULL="$MINUTE $HOUR * * * sudo sh ${RUNFILE} -m FULLAUDIT"
CRONJOBAUDIT="*/15 * * * * sudo sh ${RUNFILE} -m AUDIT"

# Create the folder if it doesn't exist
if [ ! -d "$ROOTFOLDER" ]; then
    echo "Creating folder ${ROOTFOLDER}"
    mkdir -p "$ROOTFOLDER"
fi
if [ ! -d "$LOGFOLDER" ]; then
    echo "Creating folder ${LOGFOLDER}"
    mkdir -p "$LOGFOLDER"
fi
if [ ! -d "$CONFIGFOLDER" ]; then
    echo "Creating folder ${CONFIGFOLDER}"
    mkdir -p "$CONFIGFOLDER"
fi
if [ ! -d "$COLLFOLDER" ]; then
    echo "Creating folder ${COLLFOLDER}"
    mkdir -p "$COLLFOLDER"
fi
if [ ! -d "$FILESFOLDER" ]; then
    echo "Creating folder ${FILESFOLDER}"
    mkdir -p "$FILESFOLDER"
fi

# Download the file
echo "Downloading ${URL1} to ${FILE}"
curl -o "$FILE" "$URL1"

echo "Downloading ${URL2} to ${RUNFILE}"
curl -o "$RUNFILE" "$URL2"
sudo chmod +x $RUNFILE

echo "Downloading ${URL3} to ${REQFILE}"
curl -o "$REQFILE" "$URL3"


install_venv
create_venv
echo "Executing: /opt/Wegweiser/venv/bin/pip3 install -r $REQFILE"
/opt/Wegweiser/venv/bin/pip3 install -r $REQFILE


# Create a crontab job if it doesn't already exist
echo "Attempting to creating CRONJOBs..."
(sudo crontab -l | grep -v -F "$FILE") | crontab -
(sudo crontab -l | grep -v -F "$FILE") | crontab -

(sudo crontab -l | grep -v -F "$FULLMESSAGE" 			; echo "$FULLMESSAGE") | crontab -
(sudo crontab -l | grep -v -F "$RUNFILE -m FULLAUDIT" 	; echo "$CRONJOBFULL") | crontab -
(sudo crontab -l | grep -v -F "$AUDITMESSAGE" 			; echo "$AUDITMESSAGE")  | crontab -
(sudo crontab -l | grep -v -F "$RUNFILE -m AUDIT" 		; echo "$CRONJOBAUDIT") | crontab -



echo "Successfully created CRONJOBs."

echo "Attempting to run first AUDIT..."
echo "Commmand: sudo $RUNFILE -m AUDIT -g $GROUPUUID"
sudo sudo sh $RUNFILE -m AUDIT -g $GROUPUUID
echo "Successfully ran first AUDIT."

echo "Setup complete."
