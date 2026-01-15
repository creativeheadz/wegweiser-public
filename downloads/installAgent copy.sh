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
    python3 -m venv /opt/Wegweiser/Agent/python-weg
    echo "Activating virtual environment..."
#    source /opt/Wegweiser/venv/bin/activate
#    echo "Virtual environment activated."
}

# Define the folder and file
ROOTFOLDER="/opt/Wegweiser"
LOGFOLDER="${ROOTFOLDER}/Logs"
CONFIGFOLDER="${ROOTFOLDER}/Config"
AGENTFOLDER="${ROOTFOLDER}/Agent"
FILESFOLDER="${ROOTFOLDER}/Files"
SCRIPTSFOLDER="${ROOTFOLDER}/Scripts"
FILE="${SCRIPTSFOLDER}/agent.py"
RUNFILE="${AGENTFOLDER}/runAgent.sh"
REQFILE="${AGENTFOLDER}/requirements.txt"
FULLMESSAGE="# Wegweiser Agent (Every Minute)"
CRONJOBFULL="*/1 * * * * sudo sh ${RUNFILE}"

URL1="https://app.wegweiser.tech/download/agent.py"
URL2="https://app.wegweiser.tech/download/runAgent.sh"
URL3="https://app.wegweiser.tech/download/requirements.txt"


# Create the folder if it doesn't exist
if [ ! -d "$ROOTFOLDER" ]; then
    echo "Creating folder ${ROOTFOLDER}"
    mkdir -p "$ROOTFOLDER"
fi

# lock the folder to root only
sudo chmod 700 "$ROOTFOLDER"

# Create Folders if they don't exist
if [ ! -d "$LOGFOLDER" ]; then
    echo "Creating folder ${LOGFOLDER}"
    mkdir -p "$LOGFOLDER"
fi
if [ ! -d "$CONFIGFOLDER" ]; then
    echo "Creating folder ${CONFIGFOLDER}"
    mkdir -p "$CONFIGFOLDER"
fi
if [ ! -d "$AGENTFOLDER" ]; then
    echo "Creating folder ${AGENTFOLDER}"
    mkdir -p "$AGENTFOLDER"
fi
if [ ! -d "$FILESFOLDER" ]; then
    echo "Creating folder ${FILESFOLDER}"
    mkdir -p "$FILESFOLDER"
fi
if [ ! -d "$SCRIPTSFOLDER" ]; then
    echo "Creating folder ${SCRIPTSFOLDER}"
    mkdir -p "$SCRIPTSFOLDER"
fi


# Download agent.py
echo "Downloading ${URL1} to ${FILE}"
curl -o "$FILE" "$URL1"

# Download runAgent.py
echo "Downloading ${URL2} to ${RUNFILE}"
curl -o "$RUNFILE" "$URL2"

# Set runAgent.py executable 
sudo chmod +x $RUNFILE

# Download requirements.txt
echo "Downloading ${URL3} to ${REQFILE}"
curl -o "$REQFILE" "$URL3"

# Install python venv
install_venv

# Create python venv
create_venv

# Install the modules in requirements.txt
echo "Executing: /opt/Wegweiser/venv/bin/pip3 install -r $REQFILE"
/opt/Wegweiser/venv/bin/pip3 install -r $REQFILE

# Run the agent for the first time and register
echo "Attempting to register..."
echo "Commmand: sudo $RUNFILE -g $GROUPUUID"
sudo sudo sh $RUNFILE -g $GROUPUUID
echo "Successfully registered."

# Create a crontab job if it doesn't already exist
echo "Attempting to creating CRONJOBs..."

# Remove existing comment line and add the new one
sudo crontab -l | grep -v -F "$FULLMESSAGE" | crontab -	
(crontab -l; echo "$FULLMESSAGE") | crontab -

# Remove existing exec line and add the new one
sudo crontab -l | grep -v -F "$RUNFILE" | crontab -	
(crontab -l; echo "$CRONJOBFULL") | crontab -

echo "Successfully created CRONJOBs."

# Done
echo "Setup complete."
