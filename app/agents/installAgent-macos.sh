#!/bin/bash

if [ "$#" -ne 1 ]; then
    echo "Usage: $0 <groupuuid>"
    exit 1
fi

GROUPUUID=$1

# Check if script is run with sudo
if [ "$EUID" -ne 0 ]; then 
    echo "Please run as root (use sudo)"
    exit 1
fi

# Define folders and files
ROOTFOLDER="/opt/Wegweiser"
LOGFOLDER="${ROOTFOLDER}/Logs"
CONFIGFOLDER="${ROOTFOLDER}/Config"
AGENTFOLDER="${ROOTFOLDER}/Agent"
FILESFOLDER="${ROOTFOLDER}/Files"
SCRIPTSFOLDER="${ROOTFOLDER}/Scripts"
SNIPPETSFOLDER="${ROOTFOLDER}/Snippets"
FILE="${SCRIPTSFOLDER}/agent.py"
RUNFILE="${AGENTFOLDER}/runAgent.sh"
REQFILE="${AGENTFOLDER}/requirements.txt"
PERSISTENT_AGENT_FILE="${AGENTFOLDER}/nats_persistent_agent.py"
PERSISTENT_AGENT_RUNFILE="${AGENTFOLDER}/runPersistentAgent.sh"
PLIST_FILE="/Library/LaunchDaemons/tech.wegweiser.agent.plist"
PERSISTENT_PLIST_FILE="/Library/LaunchDaemons/tech.wegweiser.persistent-agent.plist"

# URLs for downloading agent files
URL1="https://app.wegweiser.tech/download/agent.py"
URL2="https://app.wegweiser.tech/download/runAgent.sh"
URL3="https://app.wegweiser.tech/download/requirements.txt"
URL4="https://app.wegweiser.tech/download/nats_persistent_agent.py"

# Clean up any existing installation
echo "Cleaning up any existing installation..."
launchctl unload "$PLIST_FILE" 2>/dev/null || true
launchctl unload "$PERSISTENT_PLIST_FILE" 2>/dev/null || true
rm -rf "$ROOTFOLDER"
rm -f "$PLIST_FILE"
rm -f "$PERSISTENT_PLIST_FILE"

# Create required directories
echo "Creating directory structure..."
for DIR in "$ROOTFOLDER" "$LOGFOLDER" "$CONFIGFOLDER" "$AGENTFOLDER" "$FILESFOLDER" "$SCRIPTSFOLDER" "$SNIPPETSFOLDER"; do
    mkdir -p "$DIR"
    chown root:wheel "$DIR"
    chmod 755 "$DIR"
done

# Download agent files
echo "Downloading agent files..."
curl -o "$FILE" "$URL1"
if [ $? -ne 0 ]; then
    echo "Failed to download agent.py. Exiting."
    exit 1
fi

curl -o "$RUNFILE" "$URL2"
if [ $? -ne 0 ]; then
    echo "Failed to download runAgent.sh. Exiting."
    exit 1
fi

curl -o "$REQFILE" "$URL3"
if [ $? -ne 0 ]; then
    echo "Failed to download requirements.txt. Exiting."
    exit 1
fi

curl -o "$PERSISTENT_AGENT_FILE" "$URL4"
if [ $? -ne 0 ]; then
    echo "Failed to download persistent agent. Exiting."
    exit 1
fi

# Create virtual environment
echo "Creating virtual environment..."
/usr/bin/python3 -m venv "${AGENTFOLDER}/python-weg"
if [ $? -ne 0 ]; then
    echo "Failed to create virtual environment. Exiting."
    exit 1
fi

# Install Python requirements
echo "Installing Python requirements..."
"${AGENTFOLDER}/python-weg/bin/pip3" install --no-cache-dir -r "$REQFILE"
if [ $? -ne 0 ]; then
    echo "Failed to install base requirements. Exiting."
    exit 1
fi

# Install additional dependencies for NATS persistent agent (INCLUDING aiohttp!)
echo "Installing additional dependencies for NATS persistent agent..."
"${AGENTFOLDER}/python-weg/bin/pip3" install --no-cache-dir nats-py websockets logzero python-dotenv psutil aiohttp
if [ $? -ne 0 ]; then
    echo "Failed to install additional dependencies. Exiting."
    exit 1
fi

# Install cryptography (needed for registration)
echo "Installing cryptography for secure registration..."
"${AGENTFOLDER}/python-weg/bin/pip3" install --no-cache-dir cryptography
if [ $? -ne 0 ]; then
    echo "Failed to install cryptography. Exiting."
    exit 1
fi

# Create runAgent script
cat > "${RUNFILE}" << 'EOF'
#!/bin/bash

echo "$(date '+%Y-%m-%d %H:%M:%S') - Agent execution started" >> /opt/Wegweiser/Logs/wegweiser_daemon.log

AGENT_DIR="/opt/Wegweiser"
PYTHON="${AGENT_DIR}/Agent/python-weg/bin/python3"
AGENT="${AGENT_DIR}/Scripts/agent.py"

cd "${AGENT_DIR}"
"${PYTHON}" "${AGENT}" "$@"

echo "$(date '+%Y-%m-%d %H:%M:%S') - Agent execution completed" >> /opt/Wegweiser/Logs/wegweiser_daemon.log
EOF

chmod +x "${RUNFILE}"

# Create persistent agent run script
echo "Creating persistent agent run script..."
cat > "${PERSISTENT_AGENT_RUNFILE}" << 'EOF'
#!/bin/bash

ROOTDIR="/opt/Wegweiser"
PYTHONAPP="$ROOTDIR/Agent/python-weg/bin/python3"
PERSISTENT_AGENT="$ROOTDIR/Agent/nats_persistent_agent.py"

echo "$(date '+%Y-%m-%d %H:%M:%S') - Starting persistent agent..." >> /opt/Wegweiser/Logs/wegweiser_persistent_daemon.log
echo "Python: $PYTHONAPP" >> /opt/Wegweiser/Logs/wegweiser_persistent_daemon.log
echo "Agent: $PERSISTENT_AGENT" >> /opt/Wegweiser/Logs/wegweiser_persistent_daemon.log

# Check if aiohttp is available
if ! "$PYTHONAPP" -c "import aiohttp" 2>/dev/null; then
    echo "Required library not found: No module named 'aiohttp'" >> /opt/Wegweiser/Logs/wegweiser_persistent_daemon.log
    echo "Please ensure all dependencies are installed via requirements.txt" >> /opt/Wegweiser/Logs/wegweiser_persistent_daemon.log
    exit 1
fi

cd "$ROOTDIR"
exec "$PYTHONAPP" "$PERSISTENT_AGENT" start
EOF

chmod +x "${PERSISTENT_AGENT_RUNFILE}"

# Make persistent agent executable
chmod +x "$PERSISTENT_AGENT_FILE"

# Initial agent registration (NOW AFTER all dependencies are installed)
echo "Registering agent..."
"${RUNFILE}" -g "${GROUPUUID}"
if [ $? -ne 0 ]; then
    echo "Failed to register agent. Please check the logs and try again."
    exit 1
fi

echo "Successfully registered agent."

# Create LaunchDaemon plist
cat > "$PLIST_FILE" << EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>tech.wegweiser.agent</string>
    <key>ProgramArguments</key>
    <array>
        <string>/bin/bash</string>
        <string>-c</string>
        <string>/opt/Wegweiser/Agent/runAgent.sh</string>
    </array>
    <key>StartInterval</key>
    <integer>60</integer>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <false/>
    <key>StandardErrorPath</key>
    <string>/opt/Wegweiser/Logs/wegweiser_daemon.err</string>
    <key>StandardOutPath</key>
    <string>/opt/Wegweiser/Logs/wegweiser_daemon.log</string>
    <key>WorkingDirectory</key>
    <string>/opt/Wegweiser</string>
    <key>UserName</key>
    <string>root</string>
    <key>GroupName</key>
    <string>wheel</string>
    <key>EnvironmentVariables</key>
    <dict>
        <key>PATH</key>
        <string>/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin</string>
    </dict>
</dict>
</plist>
EOF

# Set permissions for plist
chown root:wheel "$PLIST_FILE"
chmod 644 "$PLIST_FILE"

# Create persistent agent LaunchDaemon plist
echo "Creating persistent agent LaunchDaemon..."
cat > "$PERSISTENT_PLIST_FILE" << EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>tech.wegweiser.persistent-agent</string>
    <key>ProgramArguments</key>
    <array>
        <string>/bin/bash</string>
        <string>-c</string>
        <string>/opt/Wegweiser/Agent/runPersistentAgent.sh</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>StandardErrorPath</key>
    <string>/opt/Wegweiser/Logs/wegweiser_persistent_daemon.err</string>
    <key>StandardOutPath</key>
    <string>/opt/Wegweiser/Logs/wegweiser_persistent_daemon.log</string>
    <key>WorkingDirectory</key>
    <string>/opt/Wegweiser</string>
    <key>UserName</key>
    <string>root</string>
    <key>GroupName</key>
    <string>wheel</string>
    <key>EnvironmentVariables</key>
    <dict>
        <key>PATH</key>
        <string>/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin</string>
    </dict>
</dict>
</plist>
EOF

# Set permissions for persistent agent plist
chown root:wheel "$PERSISTENT_PLIST_FILE"
chmod 644 "$PERSISTENT_PLIST_FILE"

# Load the LaunchDaemons
launchctl load "$PLIST_FILE"
launchctl load "$PERSISTENT_PLIST_FILE"

echo "Installation complete. Wegweiser agent and persistent agent are now running as system services."
echo "You can check the cron agent status in ${LOGFOLDER}/wegweiser_daemon.log"
echo "You can check the persistent agent status in ${LOGFOLDER}/wegweiser_persistent_daemon.log"