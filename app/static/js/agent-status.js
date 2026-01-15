/**
 * Agent Status Indicator
 *
 * Fetches and displays real-time agent connectivity status in the header.
 * Shows online, offline, and stale agent counts with visual indicators.
 */

class AgentStatusIndicator {
    constructor() {
        this.updateInterval = 30000; // Update every 30 seconds
        this.statusDot = document.getElementById('agentStatusDot');
        this.statusText = document.getElementById('agentStatusText');
        this.statusDetails = document.getElementById('agentStatusDetails');
        this.indicator = document.querySelector('.agent-status-indicator');
        this.lastStatus = null;

        // Initialize
        this.init();
    }

    init() {
        // Fetch initial status
        this.updateStatus();

        // Set up periodic updates
        setInterval(() => this.updateStatus(), this.updateInterval);

        // Add click handler for tooltip
        if (this.indicator) {
            this.indicator.addEventListener('click', (e) => {
                e.stopPropagation();
                this.showStatusTooltip();
            });
        }
    }

    async updateStatus() {
        try {
            const response = await fetch('/api/nats/agent-status', {
                method: 'GET',
                headers: {
                    'Accept': 'application/json',
                    'Content-Type': 'application/json'
                }
            });

            if (!response.ok) {
                // Handle 401 (not authenticated) silently
                if (response.status === 401) {
                    this.setStatus('unavailable', 0, 0, 0);
                    return;
                }
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const data = await response.json();

            if (data.success) {
                this.setStatus(
                    this.determineOverallStatus(data),
                    data.online,
                    data.offline,
                    data.stale
                );
            }
        } catch (error) {
            console.warn('Failed to fetch agent status:', error);
            this.setStatus('unavailable', 0, 0, 0);
        }
    }

    determineOverallStatus(data) {
        const { online, offline, stale, total } = data;

        // No agents
        if (total === 0) return 'unavailable';

        // All online
        if (offline === 0 && stale === 0) return 'online';

        // All offline
        if (online === 0 && stale === 0) return 'offline';

        // Some offline or stale
        if (stale > 0) return 'stale';

        // Mixed status (some online, some offline)
        return 'mixed';
    }

    setStatus(status, online, offline, stale) {
        // Update dot class
        this.statusDot.className = `agent-status-dot ${status}`;

        // Format text
        const total = online + offline + stale;

        let statusLabel = 'Unknown';
        let detailsText = '';
        let statusIcon = '';

        if (total === 0) {
            statusLabel = 'No Agents';
            detailsText = 'No agents configured';
            statusIcon = '<i class="fa-solid fa-circle-question"></i>';
        } else if (status === 'online') {
            statusLabel = `${online} Online`;
            detailsText = `All ${total} agents connected`;
            statusIcon = '<i class="fa-solid fa-circle-check"></i>';
        } else if (status === 'offline') {
            statusLabel = `${offline} Offline`;
            detailsText = `All agents disconnected`;
            statusIcon = '<i class="fa-solid fa-circle-xmark"></i>';
        } else if (status === 'stale') {
            statusLabel = `${online} Online`;
            detailsText = `${stale} Stale, ${offline} Offline`;
            statusIcon = '<i class="fa-solid fa-triangle-exclamation"></i>';
        } else if (status === 'mixed') {
            statusLabel = `${online} Online`;
            detailsText = `${offline} Offline out of ${total}`;
            statusIcon = '<i class="fa-solid fa-circle-half-stroke"></i>';
        } else {
            statusLabel = 'Unavailable';
            detailsText = 'Unable to fetch status';
            statusIcon = '<i class="fa-solid fa-ban"></i>';
        }

        this.statusText.innerHTML = `${statusIcon} ${statusLabel}`;
        this.statusDetails.textContent = detailsText;

        // Update tooltip
        this.updateTooltip(online, offline, stale, total);

        // Store for potential future use
        this.lastStatus = { status, online, offline, stale, total };
    }

    updateTooltip(online, offline, stale, total) {
        if (!this.indicator) return;

        let tooltipText = 'Agent Status: ';

        if (total === 0) {
            tooltipText += 'No agents configured';
        } else {
            const parts = [];
            if (online > 0) parts.push(`${online} Online`);
            if (stale > 0) parts.push(`${stale} Stale`);
            if (offline > 0) parts.push(`${offline} Offline`);
            tooltipText += parts.join(', ');
        }

        this.indicator.setAttribute('title', tooltipText);

        // Update Bootstrap tooltip if it exists
        const bsTooltip = bootstrap.Tooltip.getInstance(this.indicator);
        if (bsTooltip) {
            bsTooltip.setContent({ '.tooltip-inner': tooltipText });
        }
    }

    showStatusTooltip() {
        if (!this.lastStatus) return;

        const { online, offline, stale, total } = this.lastStatus;

        // Create a simple notification instead
        const notification = document.createElement('div');
        notification.className = 'toast align-items-center border-0';
        notification.setAttribute('role', 'alert');
        notification.setAttribute('aria-live', 'assertive');
        notification.setAttribute('aria-atomic', 'true');
        notification.innerHTML = `
            <div class="d-flex">
                <div class="toast-body">
                    <strong>Agent Status Summary</strong><br>
                    ${total === 0 ? 'No agents configured' : `
                        Online: ${online}<br>
                        Stale: ${stale}<br>
                        Offline: ${offline}<br>
                        Total: ${total}
                    `}
                </div>
                <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast" aria-label="Close"></button>
            </div>
        `;

        // Add to notification container or body
        const container = document.getElementById('notification-container') || document.body;
        container.appendChild(notification);

        // Show toast
        const toast = new bootstrap.Toast(notification);
        toast.show();

        // Remove after showing
        notification.addEventListener('hidden.bs.toast', () => {
            notification.remove();
        });
    }
}

// Initialize on DOM ready
document.addEventListener('DOMContentLoaded', () => {
    new AgentStatusIndicator();
});
