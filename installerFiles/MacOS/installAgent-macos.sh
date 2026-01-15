#!/bin/bash

# Wegweiser Agent Installer for macOS (repair by default)
# Based on refactored Agent v4.0 structure

# Defaults
GROUPUUID=""
SERVER_ADDR="app.wegweiser.tech"
REINSTALL=0

print_usage() {
        cat << USAGE
Usage: sudo $0 [--group <groupuuid>] [--server <serverAddr>] [--reinstall]

Behavior:
    - By default, performs a REPAIR install: preserves existing device identity if /opt/Wegweiser/Config/agent.config exists.
    - Use --reinstall to force a NEW identity (cleans previous install and re-registers).

Examples:
    sudo $0 --group 00000000-0000-0000-0000-000000000000
    sudo $0 --group 0000... --server app.wegweiser.tech
    sudo $0 --reinstall --group 0000...
USAGE
}

# Parse arguments
while [[ $# -gt 0 ]]; do
    case "$1" in
        --group|-g)
            GROUPUUID="$2"; shift 2 ;;
        --server|-s)
            SERVER_ADDR="$2"; shift 2 ;;
        --reinstall)
            REINSTALL=1; shift ;;
        -h|--help)
            print_usage; exit 0 ;;
        *)
            echo "Unknown argument: $1"; print_usage; exit 1 ;;
    esac
done

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
    echo "Stopping existing services (if any)..."
    launchctl unload "$SCHEDULED_PLIST" 2>/dev/null || true
    launchctl unload "$PERSISTENT_PLIST" 2>/dev/null || true

    if [ "$REINSTALL" -eq 1 ]; then
        echo "Reinstall mode: removing full previous installation..."
        rm -rf "$ROOTFOLDER"
    else
        echo "Repair mode: preserving Config and Logs; refreshing agent files..."
        rm -rf "$AGENTFOLDER" "$FILESFOLDER" "$SNIPPETSFOLDER"
        mkdir -p "$AGENTFOLDER" "$FILESFOLDER" "$SNIPPETSFOLDER"
        chown -R root:wheel "$AGENTFOLDER" "$FILESFOLDER" "$SNIPPETSFOLDER"
        chmod 755 "$AGENTFOLDER" "$FILESFOLDER" "$SNIPPETSFOLDER"
    fi

    # Always refresh plists
    rm -f "$SCHEDULED_PLIST" "$PERSISTENT_PLIST"
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
    
    if [ -z "$GROUPUUID" ]; then
        echo "Error: --group <groupuuid> is required for registration" ; exit 1
    fi

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
        <string>--once</string>
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
        <key>PYTHONUNBUFFERED</key>
        <string>1</string>
        <key>WEGWEISER_ONESHOT_JITTER</key>
        <string>5</string>
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
    
    # Ensure fresh load
    launchctl unload "$SCHEDULED_PLIST" 2>/dev/null || true
    launchctl unload "$PERSISTENT_PLIST" 2>/dev/null || true
    launchctl load "$PERSISTENT_PLIST"
    launchctl load "$SCHEDULED_PLIST"
    
    # Trigger an immediate oneshot run
    launchctl start tech.wegweiser.agent 2>/dev/null || true
    
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

CONFIG_FILE="${CONFIGFOLDER}/agent.config"

# Detect repair vs reinstall
if [ -f "$CONFIG_FILE" ] && [ "$REINSTALL" -eq 0 ]; then
    echo "Detected existing device config. Proceeding with REPAIR install (preserve deviceuuid)."
    echo "Note: provided --group is ignored in repair mode."
else
    if [ "$REINSTALL" -eq 1 ]; then
        echo "Reinstall requested: will register a NEW device identity."
    else
        echo "No existing config found: fresh install will register a NEW device."
    fi
fi

cleanup_existing_installation
install_osquery
create_directory_structure
download_agent_files
create_virtual_environment
install_python_dependencies

# Register only if reinstall or no config exists (fresh install)
if [ "$REINSTALL" -eq 1 ] || [ ! -f "$CONFIG_FILE" ]; then
    register_device
else
    echo "Skipping registration (repair mode)."
fi

create_scheduled_agent_launchdaemon
create_persistent_agent_launchdaemon
start_services

echo ""
echo "=========================================="
echo "Installation complete!"
echo "=========================================="

