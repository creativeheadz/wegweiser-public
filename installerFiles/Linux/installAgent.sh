#!/bin/bash

# Wegweiser Agent Installer for Linux
# Based on refactored Agent v4.0 structure

# Check if running as root or with sudo
USER_ID=$(id -u)
if [ "$USER_ID" -ne 0 ]; then
    echo "This script must be run as root or with sudo"
    exit 1
fi

# Check for supported distributions
if ! which apt-get >/dev/null 2>&1 && ! [ -x "/usr/bin/apt-get" ]; then
    echo "This script requires apt-get (Debian/Ubuntu-based distributions)"
    exit 1
fi

SERVER_ADDR="app.wegweiser.tech"
GROUPUUID=""
REINSTALL=false

print_usage() {
    cat << USAGE
Usage:
  $0 [--server=app.wegweiser.tech] [--reinstall] [--group=<groupuuid>|<groupuuid>]

Default behavior: REPAIR install. If an existing config with deviceuuid is found,
the current device identity is preserved unless --reinstall is provided.
USAGE
}

for arg in "$@"; do
    case $arg in
        --server=*)
            SERVER_ADDR="${arg#*=}"
            shift
            ;;
        --reinstall)
            REINSTALL=true
            shift
            ;;
        --group=*)
            GROUPUUID="${arg#*=}"
            shift
            ;;
        -h|--help)
            print_usage
            exit 0
            ;;
        *)
            if [ -z "$GROUPUUID" ]; then
                GROUPUUID="$arg"
            else
                echo "Unknown argument: $arg"
                print_usage
                exit 1
            fi
            ;;
    esac
done

# Define folders
ROOTFOLDER="/opt/Wegweiser"
LOGFOLDER="${ROOTFOLDER}/Logs"
CONFIGFOLDER="${ROOTFOLDER}/Config"
AGENTFOLDER="${ROOTFOLDER}/Agent"
FILESFOLDER="${ROOTFOLDER}/Files"
SNIPPETSFOLDER="${ROOTFOLDER}/Snippets"

# Service files
SERVICE_FILE="/etc/systemd/system/wegweiser-agent.service"
PERSISTENT_SERVICE_FILE="/etc/systemd/system/wegweiser-persistent-agent.service"

# Download URLs
BASE_URL="https://app.wegweiser.tech/installerFiles/Linux"
AGENT_URL="${BASE_URL}/Agent"

# Detect existing installation/config
CONFIG_PATH="${CONFIGFOLDER}/agent.config"
HAS_EXISTING_DEVICEUUID="no"
if [ -f "$CONFIG_PATH" ]; then
    if command -v python3 >/dev/null 2>&1; then
        DEVUUID=$(python3 - << 'PY' "$CONFIG_PATH"
import json,sys
try:
    d=json.load(open(sys.argv[1]))
    print(d.get('deviceuuid',''))
except Exception:
    print('')
PY
        )
        if [ -n "$DEVUUID" ]; then
            HAS_EXISTING_DEVICEUUID="yes"
        fi
    else
        if grep -q '"deviceuuid"' "$CONFIG_PATH" 2>/dev/null; then
            HAS_EXISTING_DEVICEUUID="yes"
        fi
    fi
fi

INSTALL_MODE="new"
if [ "$REINSTALL" = true ]; then
    INSTALL_MODE="reinstall"
else
    if [ "$HAS_EXISTING_DEVICEUUID" = "yes" ]; then
        INSTALL_MODE="repair"
    fi
fi

if [ "$INSTALL_MODE" != "repair" ]; then
    if [ -z "$GROUPUUID" ]; then
        echo "Error: groupuuid is required for new installs or --reinstall."
        print_usage
        exit 1
    fi
fi

install_system_dependencies() {
    echo "Installing system dependencies..."
    
    # Disable interactive prompts for needrestart (kernel upgrade notifications)
    export DEBIAN_FRONTEND=noninteractive
    export NEEDRESTART_MODE=a
    export NEEDRESTART_SUSPEND=1
    
    # Configure dpkg to keep old config files by default (no prompts)
    export DEBIAN_PRIORITY=critical
    export DEBCONF_NONINTERACTIVE_SEEN=true
    
    # Configure needrestart to automatic mode if it exists
    if [ -f /etc/needrestart/needrestart.conf ]; then
        sed -i 's/#$nrconf{restart} = .*/\$nrconf{restart} = '\''a'\'';/' /etc/needrestart/needrestart.conf 2>/dev/null || true
    fi
    
    apt-get update -qq
    apt-get install -y -o Dpkg::Options::="--force-confdef" -o Dpkg::Options::="--force-confold" python3-venv python3-pip curl

    # Check if systemd is available
    if [ -x "/bin/systemctl" ] || [ -x "/usr/bin/systemctl" ] || which systemctl >/dev/null 2>&1; then
        SYSTEMD_AVAILABLE=true
        echo "Systemd detected and available."
    else
        echo "Warning: systemctl not found. This system may not support systemd services."
        SYSTEMD_AVAILABLE=false
    fi
}

install_osquery() {
    echo "Installing osquery..."

    # Check if osquery is already installed
    if command -v osqueryi >/dev/null 2>&1; then
        INSTALLED_VERSION=$(osqueryi --version 2>&1 | head -n1 | awk '{print $2}')
        echo "osquery is already installed (version: $INSTALLED_VERSION)"
        return 0
    fi

    # Detect package manager and architecture
    ARCH=$(uname -m)

    if [ "$ARCH" = "x86_64" ]; then
        OSQUERY_DEB="osquery_5.19.0-1.linux_amd64.deb"
    elif [ "$ARCH" = "aarch64" ] || [ "$ARCH" = "arm64" ]; then
        OSQUERY_DEB="osquery_5.19.0-1.linux_arm64.deb"
    else
        echo "Unsupported architecture: $ARCH"
        echo "osquery installation skipped. Please install manually."
        return 1
    fi

    # Download osquery package from Wegweiser server
    OSQUERY_URL="https://app.wegweiser.tech/download/Vendors/osquery.io/${OSQUERY_DEB}"
    TEMP_DEB="/tmp/${OSQUERY_DEB}"

    echo "Downloading osquery from ${OSQUERY_URL}..."
    curl -L -o "${TEMP_DEB}" "${OSQUERY_URL}"

    if [ $? -ne 0 ]; then
        echo "Failed to download osquery package."
        return 1
    fi

    # Install osquery
    echo "Installing osquery package..."
    dpkg -i "${TEMP_DEB}"

    if [ $? -ne 0 ]; then
        echo "dpkg installation failed, attempting to fix dependencies..."
        apt-get install -f -y
    fi

    # Clean up
    rm -f "${TEMP_DEB}"

    # Verify installation
    if command -v osqueryi >/dev/null 2>&1; then
        echo "osquery installed successfully: $(osqueryi --version 2>&1 | head -n1)"
    else
        echo "Warning: osquery installation may have failed."
        return 1
    fi
}

install_osquery() {
    echo "Installing osquery..."

    # Check if osquery is already installed
    if which osqueryi >/dev/null 2>&1; then
        echo "osquery is already installed."
        osqueryi --version
        return 0
    fi

    # Detect OS and install osquery
    if [ -f /etc/os-release ]; then
        . /etc/os-release
        OS=$ID
        VERSION_ID=$VERSION_ID
    else
        echo "Cannot detect OS. Skipping osquery installation."
        return 1
    fi

    echo "Detected OS: $OS $VERSION_ID"

    case "$OS" in
        ubuntu|debian)
            echo "Installing osquery for Debian/Ubuntu..."
            export OSQUERY_KEY=1484120AC4E9F8A1A577AEEE97A80C63C9D8B80B
            apt-key adv --keyserver hkp://keyserver.ubuntu.com:80 --recv-keys $OSQUERY_KEY 2>/dev/null || true
            add-apt-repository -y 'deb [arch=amd64] https://pkg.osquery.io/deb deb main'
            apt-get update -qq
            apt-get install -y osquery
            ;;
        centos|rhel|fedora)
            echo "Installing osquery for CentOS/RHEL/Fedora..."
            curl -L https://pkg.osquery.io/rpm/GPG | tee /etc/pki/rpm-gpg/RPM-GPG-KEY-osquery
            yum-config-manager --add-repo https://pkg.osquery.io/rpm/osquery-s3-rpm.repo
            yum install -y osquery
            ;;
        *)
            echo "Unsupported OS for automatic osquery installation: $OS"
            echo "Please install osquery manually from https://osquery.io/downloads"
            return 1
            ;;
    esac

    # Verify installation
    if which osqueryi >/dev/null 2>&1; then
        echo "osquery installed successfully."
        osqueryi --version
        return 0
    else
        echo "osquery installation failed."
        return 1
    fi
}

cleanup_old_configurations() {
    echo "Cleaning up old configurations and vidar.wegweiser.tech references..."
    
    # Remove old cron jobs that might reference vidar.wegweiser.tech, persistent_agent.py, or old Scripts paths
    echo "Removing old cron entries..."
    TEMP_CRON=$(mktemp)
    crontab -l 2>/dev/null > "$TEMP_CRON" || touch "$TEMP_CRON"
    if grep -q "vidar.wegweiser.tech\|persistent_agent.py\|/opt/Wegweiser/Scripts/agent.py\|runAgent.sh" "$TEMP_CRON" 2>/dev/null; then
        echo "Found old cron entries, cleaning up..."
        grep -v "vidar.wegweiser.tech" "$TEMP_CRON" | \
            grep -v "persistent_agent.py" | \
            grep -v "/opt/Wegweiser/Scripts/agent.py" | \
            grep -v "runAgent.sh" | \
            crontab - 2>/dev/null || true
        echo "Old cron entries removed. Systemd timers will handle scheduling."
    fi
    rm -f "$TEMP_CRON"
    
    # Stop and disable old systemd services
    echo "Stopping old systemd services..."
    for OLD_SERVICE in wegweiser-old.service wegweiser-ws.service wegweiser-vidar.service wegweiser-websocket.service; do
        if systemctl list-unit-files 2>/dev/null | grep -q "$OLD_SERVICE"; then
            echo "Stopping and disabling $OLD_SERVICE..."
            systemctl stop "$OLD_SERVICE" 2>/dev/null || true
            systemctl disable "$OLD_SERVICE" 2>/dev/null || true
            rm -f "/etc/systemd/system/$OLD_SERVICE" 2>/dev/null || true
        fi
    done
    
    # Find and remove ALL persistent_agent.py files (old agent version)
    echo "Searching for old persistent_agent.py files..."
    find /opt/Wegweiser -name "persistent_agent.py" -type f 2>/dev/null | while read -r OLD_FILE; do
        if grep -q "vidar.wegweiser.tech" "$OLD_FILE" 2>/dev/null; then
            echo "Found old agent script with vidar reference: $OLD_FILE"
            BACKUP_NAME="${OLD_FILE}.vidar-backup.$(date +%s)"
            mv "$OLD_FILE" "$BACKUP_NAME" 2>/dev/null || rm -f "$OLD_FILE"
            echo "  -> Moved to $BACKUP_NAME"
        fi
    done
    
    # Remove old Python scripts in various locations
    echo "Removing old agent scripts..."
    for OLD_SCRIPT in \
        "${ROOTFOLDER}/persistent_agent.py" \
        "${ROOTFOLDER}/agent.py.old" \
        "${ROOTFOLDER}/ws_agent.py" \
        "${ROOTFOLDER}/vidar_agent.py" \
        "${AGENTFOLDER}/persistent_agent.py"; do
        if [ -f "$OLD_SCRIPT" ]; then
            if grep -q "vidar.wegweiser.tech" "$OLD_SCRIPT" 2>/dev/null; then
                echo "Removing old script: $OLD_SCRIPT"
                rm -f "$OLD_SCRIPT" 2>/dev/null || true
            fi
        fi
    done
    
    # Clean up old config files that might have vidar references
    if [ -f "${CONFIGFOLDER}/agent.config" ]; then
        echo "Checking agent.config for old server references..."
        if grep -q "vidar.wegweiser.tech" "${CONFIGFOLDER}/agent.config" 2>/dev/null; then
            echo "Found vidar.wegweiser.tech reference in config, updating to app.wegweiser.tech..."
            cp "${CONFIGFOLDER}/agent.config" "${CONFIGFOLDER}/agent.config.vidar-backup.$(date +%s)"
            # Replace vidar references with app
            sed -i 's/vidar\.wegweiser\.tech/app.wegweiser.tech/g' "${CONFIGFOLDER}/agent.config" 2>/dev/null || true
            sed -i 's/wss:\/\/vidar/wss:\/\/app/g' "${CONFIGFOLDER}/agent.config" 2>/dev/null || true
            sed -i 's/https:\/\/vidar/https:\/\/app/g' "${CONFIGFOLDER}/agent.config" 2>/dev/null || true
            echo "Config file updated successfully."
        fi
    fi
    
    # Check for any Python files containing vidar references in the Agent folder
    if [ -d "${AGENTFOLDER}" ]; then
        echo "Scanning Agent folder for vidar references..."
        find "${AGENTFOLDER}" -name "*.py" -type f 2>/dev/null | while read -r PY_FILE; do
            if grep -q "vidar.wegweiser.tech" "$PY_FILE" 2>/dev/null; then
                echo "WARNING: Found vidar reference in $PY_FILE - this file will be replaced by new agent files"
            fi
        done
    fi
    
    # Reload systemd after service cleanup
    if [ "$SYSTEMD_AVAILABLE" = true ]; then
        systemctl daemon-reload 2>/dev/null || true
    fi
    
    echo "Old configuration cleanup complete."
    echo "All vidar.wegweiser.tech references have been removed/updated."
}

create_directory_structure() {
    echo "Creating directory structure..."
    
    # Create all required directories
    for DIR in "$ROOTFOLDER" "$LOGFOLDER" "$CONFIGFOLDER" "$AGENTFOLDER" "$FILESFOLDER" "$SNIPPETSFOLDER"; do
        mkdir -p "$DIR"
        chmod 755 "$DIR"
    done
    
    # Lock root folder to root only
    chmod 700 "$ROOTFOLDER"
}

download_agent_files() {
    echo "Downloading agent files..."
    
    # Create temporary directory for downloads
    TEMP_DIR=$(mktemp -d)
    
    # Download the entire Agent directory structure
    echo "Downloading Agent structure from ${AGENT_URL}..."
    
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
    curl -o "${AGENTFOLDER}/core/mcp_handler.py" "${AGENT_URL}/core/mcp_handler.py" || exit 1
    curl -o "${AGENTFOLDER}/core/nats_service.py" "${AGENT_URL}/core/nats_service.py" || exit 1
    curl -o "${AGENTFOLDER}/core/tool_manager.py" "${AGENT_URL}/core/tool_manager.py" || exit 1
    
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
    
    # Remove existing virtual environment if it exists
    if [ -d "${AGENTFOLDER}/python-weg" ]; then
        echo "Removing existing virtual environment..."
        rm -rf "${AGENTFOLDER}/python-weg"
    fi
    
    python3 -m venv "${AGENTFOLDER}/python-weg"
    
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
    "${AGENTFOLDER}/python-weg/bin/pip3" install -r "${AGENTFOLDER}/requirements.txt"
    
    if [ $? -ne 0 ]; then
        echo "Failed to install Python dependencies. Exiting."
        exit 1
    fi
    
    echo "Python dependencies installed successfully."
}

validate_device() {
    # Check if device UUID exists on server
    if [ ! -f "$CONFIG_PATH" ]; then
        return 1
    fi
    
    DEVUUID=$(python3 - << 'PY' "$CONFIG_PATH"
import json,sys
try:
    d=json.load(open(sys.argv[1]))
    print(d.get('deviceuuid',''))
except Exception:
    print('')
PY
    )
    
    if [ -z "$DEVUUID" ]; then
        return 1
    fi
    
    # Test if device exists on server
    HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" "${SERVER_ADDR}/api/device/${DEVUUID}/tenant")
    
    if [ "$HTTP_CODE" = "200" ]; then
        echo "Device UUID ${DEVUUID} validated successfully."
        return 0
    else
        echo "Device UUID ${DEVUUID} not found on server (HTTP ${HTTP_CODE}). Will re-register..."
        return 1
    fi
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

create_scheduled_agent_service() {
    echo "Creating scheduled agent service..."
    
    # Create systemd timer for scheduled runs (every minute)
    cat > "/etc/systemd/system/wegweiser-agent.timer" << EOF
[Unit]
Description=Wegweiser Agent Timer (runs every minute)
Requires=wegweiser-agent.service

[Timer]
OnBootSec=1min
OnUnitActiveSec=1min
Unit=wegweiser-agent.service

[Install]
WantedBy=timers.target
EOF

    # Create systemd service for scheduled agent
    cat > "${SERVICE_FILE}" << EOF
[Unit]
Description=Wegweiser Scheduled Agent
After=network.target

[Service]
Type=oneshot
User=root
Group=root
WorkingDirectory=${ROOTFOLDER}
Environment=WEGWEISER_ONESHOT_JITTER=5
TimeoutStartSec=900
ExecStart=${AGENTFOLDER}/python-weg/bin/python3 ${AGENTFOLDER}/run_agent.py --once
StandardOutput=journal
StandardError=journal
SyslogIdentifier=wegweiser-agent

[Install]
WantedBy=multi-user.target
EOF

    echo "Scheduled agent service created."
}

create_persistent_agent_service() {
    echo "Creating persistent agent service..."
    
    cat > "${PERSISTENT_SERVICE_FILE}" << EOF
[Unit]
Description=Wegweiser NATS Persistent Agent
After=network.target
Wants=network.target

[Service]
Type=simple
User=root
Group=root
WorkingDirectory=${ROOTFOLDER}
ExecStart=${AGENTFOLDER}/python-weg/bin/python3 ${AGENTFOLDER}/nats_agent.py
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal
SyslogIdentifier=wegweiser-persistent-agent

[Install]
WantedBy=multi-user.target
EOF

    echo "Persistent agent service created."
}

start_services() {
    echo "Starting and enabling services..."
    
    # Reload systemd
    systemctl daemon-reload
    
    # Enable and start timer for scheduled agent
    systemctl enable wegweiser-agent.timer
    systemctl start wegweiser-agent.timer
    
    # Enable and start persistent agent
    systemctl enable wegweiser-persistent-agent.service
    systemctl restart wegweiser-persistent-agent.service || systemctl start wegweiser-persistent-agent.service
    
    # Trigger an immediate one-shot run so the node is active right away
    systemctl start wegweiser-agent.service
    
    echo "Services started and enabled."
    echo ""
    echo "Service status:"
    timeout 5 systemctl status wegweiser-agent.timer --no-pager -l || echo "Timer status check timed out (this is OK)"
    echo ""
    timeout 5 systemctl status wegweiser-persistent-agent.service --no-pager -l || echo "Service status check timed out (this is OK)"
    echo ""
    echo "You can check logs with:"
    echo "  sudo journalctl -u wegweiser-agent.service -f"
    echo "  sudo journalctl -u wegweiser-persistent-agent.service -f"
}

# Main installation flow
echo "=========================================="
echo "Wegweiser Agent Installer for Linux"
echo "=========================================="
echo ""

install_system_dependencies
install_osquery
cleanup_old_configurations
create_directory_structure
download_agent_files
create_virtual_environment
install_python_dependencies

case "$INSTALL_MODE" in
    repair)
        echo "Detected existing device config. Validating with server..."
        if validate_device; then
            echo "Device validation successful. Proceeding with REPAIR install (preserve deviceuuid)."
        else
            echo "Device validation failed. Backing up old config and re-registering..."
            if [ -f "$CONFIG_PATH" ]; then
                cp -f "$CONFIG_PATH" "${CONFIG_PATH}.invalid.$(date +%s)" || true
            fi
            register_device
        fi
        ;;
    new)
        echo "No existing device config detected. Proceeding with NEW registration."
        register_device
        ;;
    reinstall)
        echo "--reinstall specified. Proceeding with NEW registration (new device identity)."
        if [ -f "$CONFIG_PATH" ]; then
                cp -f "$CONFIG_PATH" "${CONFIG_PATH}.bak.$(date +%s)" || true
        fi
        register_device
        ;;
esac

if [ "$SYSTEMD_AVAILABLE" = true ]; then
    create_scheduled_agent_service
    create_persistent_agent_service
    start_services
else
    echo "Systemd not available. Services will not be created."
    echo "You can run the agent manually:"
    echo "  ${AGENTFOLDER}/python-weg/bin/python3 ${AGENTFOLDER}/run_agent.py"
    echo "  ${AGENTFOLDER}/python-weg/bin/python3 ${AGENTFOLDER}/nats_agent.py"
fi

echo ""
echo "=========================================="
echo "Installation complete!"
echo "=========================================="

