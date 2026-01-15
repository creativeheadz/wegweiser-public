#!/bin/bash

# Wegweiser Agent Installer for macOS
# Based on refactored Agent v4.0 structure

if [ "$#" -ne 1 ]; then
    echo "Usage: $0 <groupuuid>"
    exit 1
fi

GROUPUUID=$1
SERVER_ADDR="app.wegweiser.tech"

# Check if script is run with sudo
if [ "$EUID" -ne 0 ]; then 
    echo "Please run as root (use sudo)"
    exit 1
fi

# Define folders
ROOTFOLDER="/opt/Wegweiser"
LOGFOLDER="${ROOTFOLDER}/Logs"
CONFIGFOLDER="${ROOTFOLDER}/Config"
AGENTFOLDER="${ROOTFOLDER}/Agent"
FILESFOLDER="${ROOTFOLDER}/Files"
SNIPPETSFOLDER="${ROOTFOLDER}/Snippets"

# LaunchDaemon files
SCHEDULED_PLIST="/Library/LaunchDaemons/tech.wegweiser.agent.plist"
PERSISTENT_PLIST="/Library/LaunchDaemons/tech.wegweiser.persistent-agent.plist"

# Download URLs
BASE_URL="https://app.wegweiser.tech/installerFiles/MacOS"
AGENT_URL="${BASE_URL}/Agent"

cleanup_existing_installation() {
    echo "Cleaning up any existing installation..."
    launchctl unload "$SCHEDULED_PLIST" 2>/dev/null || true
    launchctl unload "$PERSISTENT_PLIST" 2>/dev/null || true
    rm -rf "$ROOTFOLDER"
    rm -f "$SCHEDULED_PLIST"
    rm -f "$PERSISTENT_PLIST"
}

install_osquery() {
    echo "Installing osquery..."

    # Check if osquery is already installed
    if command -v osqueryi >/dev/null 2>&1; then
        INSTALLED_VERSION=$(osqueryi --version 2>&1 | head -n1 | awk '{print $2}')
        echo "osquery is already installed (version: $INSTALLED_VERSION)"
        return 0
    fi

    # Download osquery package from Wegweiser server
    OSQUERY_PKG="osquery-5.19.0.pkg"
    OSQUERY_URL="https://app.wegweiser.tech/download/Vendors/osquery.io/${OSQUERY_PKG}"
    TEMP_PKG="/tmp/${OSQUERY_PKG}"

    echo "Downloading osquery from ${OSQUERY_URL}..."
    curl -L -o "${TEMP_PKG}" "${OSQUERY_URL}"

    if [ $? -ne 0 ]; then
        echo "Failed to download osquery package."
        return 1
    fi

    # Install osquery
    echo "Installing osquery package..."
    installer -pkg "${TEMP_PKG}" -target /

    if [ $? -ne 0 ]; then
        echo "Failed to install osquery package."
        rm -f "${TEMP_PKG}"
        return 1
    fi

    # Clean up
    rm -f "${TEMP_PKG}"

    # Verify installation
    if command -v osqueryi >/dev/null 2>&1; then
        echo "osquery installed successfully: $(osqueryi --version 2>&1 | head -n1)"
    else
        echo "Warning: osquery installation may have failed."
        return 1
    fi
}

create_directory_structure() {
    echo "Creating directory structure..."
    
    for DIR in "$ROOTFOLDER" "$LOGFOLDER" "$CONFIGFOLDER" "$AGENTFOLDER" "$FILESFOLDER" "$SNIPPETSFOLDER"; do
        mkdir -p "$DIR"
        chown root:wheel "$DIR"
        chmod 755 "$DIR"
    done
    
    # Lock root folder to root only
    chmod 700 "$ROOTFOLDER"
}

download_agent_files() {
    echo "Downloading agent files..."
    
    # Download core files
    curl -o "${AGENTFOLDER}/run_agent.py" "${AGENT_URL}/run_agent.py" || exit 1
    curl -o "${AGENTFOLDER}/register_device.py" "${AGENT_URL}/register_device.py" || exit 1
    curl -o "${AGENTFOLDER}/nats_agent.py" "${AGENT_URL}/nats_agent.py" || exit 1
    curl -o "${AGENTFOLDER}/requirements.txt" "${AGENT_URL}/requirements.txt" || exit 1
    curl -o "${AGENTFOLDER}/__init__.py" "${AGENT_URL}/__init__.py" || exit 1
    
    # Download core module
    mkdir -p "${AGENTFOLDER}/core"
    curl -o "${AGENTFOLDER}/core/__init__.py" "${AGENT_URL}/core/__init__.py" || exit 1
    curl -o "${AGENTFOLDER}/core/agent.py" "${AGENT_URL}/core/agent.py" || exit 1
    curl -o "${AGENTFOLDER}/core/api_client.py" "${AGENT_URL}/core/api_client.py" || exit 1
    curl -o "${AGENTFOLDER}/core/config.py" "${AGENT_URL}/core/config.py" || exit 1
    curl -o "${AGENTFOLDER}/core/crypto.py" "${AGENT_URL}/core/crypto.py" || exit 1
    curl -o "${AGENTFOLDER}/core/nats_service.py" "${AGENT_URL}/core/nats_service.py" || exit 1
    
    # Download execution module
    mkdir -p "${AGENTFOLDER}/execution"
    curl -o "${AGENTFOLDER}/execution/__init__.py" "${AGENT_URL}/execution/__init__.py" || exit 1
    curl -o "${AGENTFOLDER}/execution/executor.py" "${AGENT_URL}/execution/executor.py" || exit 1
    curl -o "${AGENTFOLDER}/execution/validator.py" "${AGENT_URL}/execution/validator.py" || exit 1
    
    # Download monitoring module
    mkdir -p "${AGENTFOLDER}/monitoring"
    curl -o "${AGENTFOLDER}/monitoring/__init__.py" "${AGENT_URL}/monitoring/__init__.py" || exit 1
    curl -o "${AGENTFOLDER}/monitoring/health.py" "${AGENT_URL}/monitoring/health.py" || exit 1
    
    # Make Python files executable
    chmod +x "${AGENTFOLDER}/run_agent.py"
    chmod +x "${AGENTFOLDER}/register_device.py"
    chmod +x "${AGENTFOLDER}/nats_agent.py"
    
    echo "Agent files downloaded successfully."
}

create_virtual_environment() {
    echo "Creating virtual environment..."
    
    /usr/bin/python3 -m venv "${AGENTFOLDER}/python-weg"
    
    if [ $? -ne 0 ]; then
        echo "Failed to create virtual environment. Exiting."
        exit 1
    fi
    
    echo "Virtual environment created."
}

install_python_dependencies() {
    echo "Installing Python dependencies..."
    
    # Upgrade pip first
    "${AGENTFOLDER}/python-weg/bin/pip3" install --upgrade pip setuptools
    
    # Install requirements
    "${AGENTFOLDER}/python-weg/bin/pip3" install --no-cache-dir -r "${AGENTFOLDER}/requirements.txt"
    
    if [ $? -ne 0 ]; then
        echo "Failed to install Python dependencies. Exiting."
        exit 1
    fi
    
    echo "Python dependencies installed successfully."
}

register_device() {
    echo "Registering device with Wegweiser server..."

    cd "${ROOTFOLDER}"
    "${AGENTFOLDER}/python-weg/bin/python3" "${AGENTFOLDER}/register_device.py" \
        -g "${GROUPUUID}" \
        -s "${SERVER_ADDR}"

    if [ $? -ne 0 ]; then
        echo "Failed to register device. Please check the logs and try again."
        exit 1
    fi

    echo "Device registered successfully."
}

create_version_file() {
    echo "Creating agent version file..."

    # Create version string with timestamp (similar to Windows installer)
    VERSION_TIMESTAMP=$(date +%Y%m%d%H%M%S)
    VERSION_STRING="4.0.${VERSION_TIMESTAMP}"

    # Write version to file
    echo "${VERSION_STRING}" > "${CONFIGFOLDER}/agentVersion.txt"
    chown root:wheel "${CONFIGFOLDER}/agentVersion.txt"
    chmod 644 "${CONFIGFOLDER}/agentVersion.txt"

    echo "Agent version file created: ${VERSION_STRING}"
}

create_scheduled_agent_launchdaemon() {
    echo "Creating scheduled agent LaunchDaemon..."
    
    cat > "$SCHEDULED_PLIST" << EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>tech.wegweiser.agent</string>
    <key>ProgramArguments</key>
    <array>
        <string>${AGENTFOLDER}/python-weg/bin/python3</string>
        <string>${AGENTFOLDER}/run_agent.py</string>
    </array>
    <key>StartInterval</key>
    <integer>60</integer>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <false/>
    <key>StandardErrorPath</key>
    <string>${LOGFOLDER}/wegweiser_scheduled.err</string>
    <key>StandardOutPath</key>
    <string>${LOGFOLDER}/wegweiser_scheduled.log</string>
    <key>WorkingDirectory</key>
    <string>${ROOTFOLDER}</string>
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

    chown root:wheel "$SCHEDULED_PLIST"
    chmod 644 "$SCHEDULED_PLIST"
    
    echo "Scheduled agent LaunchDaemon created."
}

create_persistent_agent_launchdaemon() {
    echo "Creating persistent agent LaunchDaemon..."
    
    cat > "$PERSISTENT_PLIST" << EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>tech.wegweiser.persistent-agent</string>
    <key>ProgramArguments</key>
    <array>
        <string>${AGENTFOLDER}/python-weg/bin/python3</string>
        <string>${AGENTFOLDER}/nats_agent.py</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>StandardErrorPath</key>
    <string>${LOGFOLDER}/wegweiser_persistent.err</string>
    <key>StandardOutPath</key>
    <string>${LOGFOLDER}/wegweiser_persistent.log</string>
    <key>WorkingDirectory</key>
    <string>${ROOTFOLDER}</string>
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

    chown root:wheel "$PERSISTENT_PLIST"
    chmod 644 "$PERSISTENT_PLIST"
    
    echo "Persistent agent LaunchDaemon created."
}

start_services() {
    echo "Loading and starting LaunchDaemons..."
    
    launchctl load "$SCHEDULED_PLIST"
    launchctl load "$PERSISTENT_PLIST"
    
    echo "Services started."
    echo ""
    echo "You can check logs at:"
    echo "  ${LOGFOLDER}/wegweiser_scheduled.log"
    echo "  ${LOGFOLDER}/wegweiser_persistent.log"
    echo ""
    echo "To stop services:"
    echo "  sudo launchctl unload $SCHEDULED_PLIST"
    echo "  sudo launchctl unload $PERSISTENT_PLIST"
}

# Main installation flow
echo "=========================================="
echo "Wegweiser Agent Installer for macOS"
echo "=========================================="
echo ""

cleanup_existing_installation
install_osquery
create_directory_structure
download_agent_files
create_virtual_environment
install_python_dependencies
register_device
create_version_file
create_scheduled_agent_launchdaemon
create_persistent_agent_launchdaemon
start_services

echo ""
echo "=========================================="
echo "Installation complete!"
echo "=========================================="

