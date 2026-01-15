#!/bin/bash
# Filepath: scripts/deploy_nats_integration.sh
"""
NATS Integration Deployment Script

Deploys the NATS integration alongside existing Node-RED infrastructure
for gradual migration and testing.
"""

set -e

# Configuration
NATS_SERVER_URL="nats.wegweiser.tech"
NATS_PORT="4222"
FLASK_APP_DIR="/opt/wegweiser"
VENV_PATH="/venv"
SYSTEMD_SERVICE="wegweiser"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

log_debug() {
    echo -e "${BLUE}[DEBUG]${NC} $1"
}

# Check if running as root
check_root() {
    if [[ $EUID -eq 0 ]]; then
        log_error "This script should not be run as root"
        exit 1
    fi
}

# Check prerequisites
check_prerequisites() {
    log_info "Checking prerequisites..."
    
    # Check if NATS server is accessible
    if ! nc -z "$NATS_SERVER_URL" "$NATS_PORT" 2>/dev/null; then
        log_error "NATS server at $NATS_SERVER_URL:$NATS_PORT is not accessible"
        log_info "Please ensure NATS server is running and accessible"
        exit 1
    fi
    
    log_info "NATS server is accessible at $NATS_SERVER_URL:$NATS_PORT"
    
    # Check if Flask app directory exists
    if [[ ! -d "$FLASK_APP_DIR" ]]; then
        log_error "Flask app directory not found: $FLASK_APP_DIR"
        exit 1
    fi
    
    # Check if virtual environment exists
    if [[ ! -d "$FLASK_APP_DIR$VENV_PATH" ]]; then
        log_error "Virtual environment not found: $FLASK_APP_DIR$VENV_PATH"
        exit 1
    fi
    
    log_info "Prerequisites check passed"
}

# Install Python dependencies
install_dependencies() {
    log_info "Installing Python dependencies..."
    
    cd "$FLASK_APP_DIR"
    source "$VENV_PATH/bin/activate"
    
    # Install NATS client
    pip install nats-py
    
    # Install additional dependencies if needed
    pip install aiohttp python-dotenv
    
    log_info "Dependencies installed successfully"
}

# Create NATS configuration
create_nats_config() {
    log_info "Creating NATS configuration..."
    
    # Create NATS config directory
    mkdir -p "$FLASK_APP_DIR/config/nats"
    
    # Create NATS client configuration
    cat > "$FLASK_APP_DIR/config/nats/client.conf" << EOF
# NATS Client Configuration for Wegweiser
server_url = "nats://$NATS_SERVER_URL:$NATS_PORT"
reconnect_time_wait = 2
max_reconnect_attempts = 10
ping_interval = 30
EOF
    
    log_info "NATS configuration created"
}

# Update Flask application configuration
update_flask_config() {
    log_info "Updating Flask configuration..."
    
    # Add NATS configuration to environment
    if ! grep -q "NATS_SERVER_URL" "$FLASK_APP_DIR/.env" 2>/dev/null; then
        echo "NATS_SERVER_URL=nats://$NATS_SERVER_URL:$NATS_PORT" >> "$FLASK_APP_DIR/.env"
    fi
    
    if ! grep -q "NATS_ENABLED" "$FLASK_APP_DIR/.env" 2>/dev/null; then
        echo "NATS_ENABLED=true" >> "$FLASK_APP_DIR/.env"
    fi
    
    log_info "Flask configuration updated"
}

# Test NATS integration
test_nats_integration() {
    log_info "Testing NATS integration..."
    
    cd "$FLASK_APP_DIR"
    source "$VENV_PATH/bin/activate"
    
    # Run basic connectivity test
    python3 -c "
import asyncio
import nats

async def test_connection():
    try:
        nc = await nats.connect('nats://$NATS_SERVER_URL:$NATS_PORT')
        print('✓ NATS connection successful')
        await nc.close()
        return True
    except Exception as e:
        print(f'✗ NATS connection failed: {e}')
        return False

result = asyncio.run(test_connection())
exit(0 if result else 1)
"
    
    if [[ $? -eq 0 ]]; then
        log_info "NATS integration test passed"
    else
        log_error "NATS integration test failed"
        exit 1
    fi
}

# Create NATS agent installer
create_nats_agent_installer() {
    log_info "Creating NATS agent installer..."
    
    # Copy NATS agent to installer directory
    cp "$FLASK_APP_DIR/nats_persistent_agent.py" "$FLASK_APP_DIR/installerFiles/Windows/Agent007/Agent007/scripts/"
    
    # Create requirements file for NATS agent
    cat > "$FLASK_APP_DIR/installerFiles/Windows/Agent007/Agent007/scripts/nats_requirements.txt" << EOF
nats-py>=2.6.0
aiohttp>=3.8.0
python-dotenv>=1.0.0
psutil>=5.9.0
EOF
    
    log_info "NATS agent installer created"
}

# Restart Flask application
restart_flask_app() {
    log_info "Restarting Flask application..."
    
    # Restart systemd service
    sudo systemctl restart "$SYSTEMD_SERVICE"
    
    # Wait for service to start
    sleep 5
    
    # Check if service is running
    if systemctl is-active --quiet "$SYSTEMD_SERVICE"; then
        log_info "Flask application restarted successfully"
    else
        log_error "Failed to restart Flask application"
        sudo systemctl status "$SYSTEMD_SERVICE"
        exit 1
    fi
}

# Verify deployment
verify_deployment() {
    log_info "Verifying deployment..."
    
    # Test NATS health endpoint
    if curl -s -f "http://localhost:5000/api/nats/health" > /dev/null; then
        log_info "✓ NATS health endpoint is accessible"
    else
        log_warn "✗ NATS health endpoint is not accessible"
    fi
    
    # Test NATS metrics endpoint
    if curl -s -f "http://localhost:5000/api/nats/metrics" > /dev/null; then
        log_info "✓ NATS metrics endpoint is accessible"
    else
        log_warn "✗ NATS metrics endpoint is not accessible"
    fi
    
    log_info "Deployment verification completed"
}

# Main deployment function
main() {
    log_info "Starting NATS integration deployment..."
    
    check_root
    check_prerequisites
    install_dependencies
    create_nats_config
    update_flask_config
    test_nats_integration
    create_nats_agent_installer
    restart_flask_app
    verify_deployment
    
    log_info "NATS integration deployment completed successfully!"
    log_info ""
    log_info "Next steps:"
    log_info "1. Test NATS endpoints: curl http://localhost:5000/api/nats/health"
    log_info "2. Start NATS message service: curl -X POST http://localhost:5000/api/nats/service/start"
    log_info "3. Deploy NATS agent to test devices"
    log_info "4. Monitor NATS metrics: curl http://localhost:5000/api/nats/metrics"
    log_info ""
    log_info "The NATS integration is now running parallel to Node-RED."
    log_info "Existing agents will continue to work normally."
}

# Run main function
main "$@"
